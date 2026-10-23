#!/usr/bin/env python3
"""
Unit tests for App-ads.txt Sync Tool.
Uses standard Python unittest module (no external dependencies required).
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add project root to sys.path so sync can be imported directly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sync import (
    CASApiClient,
    canonical_record_key,
    parse_arguments,
    parse_existing_file,
    __version__,
)


class TestCanonicalRecordKey(unittest.TestCase):
    """Test canonical record key extraction and normalization for deduplication."""

    def test_empty_and_whitespace_lines(self):
        self.assertIsNone(canonical_record_key(""))
        self.assertIsNone(canonical_record_key("   "))
        self.assertIsNone(canonical_record_key("\t\n"))

    def test_comment_only_lines(self):
        self.assertIsNone(canonical_record_key("# This is a comment"))
        self.assertIsNone(canonical_record_key("   # Indented comment"))

    def test_standard_four_field_record(self):
        line = "google.com, pub-1234567890123456, DIRECT, f08c47fec0942fa0"
        expected = ("google.com", "pub-1234567890123456", "DIRECT")
        self.assertEqual(canonical_record_key(line), expected)

    def test_record_with_comment_at_end(self):
        line = "applovin.com, 12345, RESELLER, abcd1234efgh5678 # CAS mediation"
        expected = ("applovin.com", "12345", "RESELLER")
        self.assertEqual(canonical_record_key(line), expected)

    def test_case_insensitivity_and_whitespace(self):
        line1 = "google.com, pub-123, DIRECT, f08c47fec0942fa0"
        line2 = "  GOOGLE.COM  ,  PUB-123  ,  direct  "
        self.assertEqual(canonical_record_key(line1), canonical_record_key(line2))

    def test_quoted_values(self):
        line = '"google.com", "pub-123", "DIRECT"'
        expected = ("google.com", "pub-123", "DIRECT")
        self.assertEqual(canonical_record_key(line), expected)

    def test_domain_protocol_stripping(self):
        line = "https://google.com/, pub-123, DIRECT"
        expected = ("google.com", "pub-123", "DIRECT")
        self.assertEqual(canonical_record_key(line), expected)

    def test_two_field_record(self):
        line = "example.com, pub-999"
        expected = ("example.com", "pub-999")
        self.assertEqual(canonical_record_key(line), expected)

    def test_variable_declaration(self):
        line = "contact=support@example.com"
        expected = ("contact=support@example.com",)
        self.assertEqual(canonical_record_key(line), expected)


class TestParseExistingFile(unittest.TestCase):
    """Test reading and parsing of existing app-ads.txt files."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_non_existent_file(self):
        fake_file = self.temp_path / "does_not_exist.txt"
        raw_lines, keys, stripped_lines = parse_existing_file(fake_file)
        self.assertEqual(raw_lines, [])
        self.assertEqual(keys, set())
        self.assertEqual(stripped_lines, set())

    def test_standard_file_parsing(self):
        sample_file = self.temp_path / "app-ads.txt"
        content = (
            "# Developer app-ads.txt\n"
            "google.com, pub-123456, DIRECT, f08c47fec0942fa0\n"
            "\n"
            "applovin.com, 54321, RESELLER\n"
        )
        sample_file.write_text(content, encoding="utf-8")

        raw_lines, keys, stripped_lines = parse_existing_file(sample_file)
        self.assertEqual(len(raw_lines), 4)
        self.assertIn(("google.com", "pub-123456", "DIRECT"), keys)
        self.assertIn(("applovin.com", "54321", "RESELLER"), keys)
        self.assertIn("google.com, pub-123456, DIRECT, f08c47fec0942fa0", stripped_lines)

    def test_file_with_utf8_bom(self):
        sample_file = self.temp_path / "app-ads-bom.txt"
        content = "\ufeffgoogle.com, pub-999999, DIRECT\n"
        with open(sample_file, "w", encoding="utf-8-sig") as f:
            f.write(content)

        raw_lines, keys, stripped_lines = parse_existing_file(sample_file)
        self.assertIn(("google.com", "pub-999999", "DIRECT"), keys)


class TestCommandLineArguments(unittest.TestCase):
    """Test argparse CLI arguments configuration."""

    def test_default_arguments(self):
        sys_argv_backup = sys.argv
        try:
            sys.argv = ["sync.py"]
            args = parse_arguments()
            self.assertEqual(args.config, "config.json")
            self.assertIsNone(args.token)
            self.assertIsNone(args.target)
            self.assertFalse(args.dry_run)
            self.assertFalse(args.recheck)
            self.assertFalse(args.no_pause)
        finally:
            sys.argv = sys_argv_backup

    def test_custom_flags(self):
        sys_argv_backup = sys.argv
        try:
            sys.argv = [
                "sync.py",
                "--token", "test-token-123",
                "--target", "./my-ads.txt",
                "--dry-run",
                "--recheck",
                "--no-pause",
                "--config", "custom.json",
            ]
            args = parse_arguments()
            self.assertEqual(args.token, "test-token-123")
            self.assertEqual(args.target, "./my-ads.txt")
            self.assertTrue(args.dry_run)
            self.assertTrue(args.recheck)
            self.assertTrue(args.no_pause)
            self.assertEqual(args.config, "custom.json")
        finally:
            sys.argv = sys_argv_backup


class TestSyncAppAdsTxtExecution(unittest.TestCase):
    """Test full sync_app_ads_txt workflow with mocked CAS API responses."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.target_file = self.temp_path / "app-ads.txt"

    def tearDown(self):
        self.temp_dir.cleanup()

    from unittest.mock import patch

    @patch("sync.CASApiClient.get_app_ads_txt_parts")
    @patch("sync.CASApiClient.list_all_apps")
    def test_sync_adds_missing_lines(self, mock_list_apps, mock_parts):
        from sync import sync_app_ads_txt

        # Existing file has 1 line
        self.target_file.write_text("google.com, pub-111, DIRECT, tag1\n", encoding="utf-8")

        mock_list_apps.return_value = [
            {"id": "app1", "name": "Game A", "bundle_id": "com.game.a", "platform": "android", "app_ads_status": "ok"},
            {"id": "app2", "name": "Game B", "bundle_id": "com.game.b", "platform": "ios", "app_ads_status": "issue"},
        ]

        def fake_parts(app_id):
            if app_id == "app1":
                return {
                    "status": "ok",
                    "missing_lines": "google.com, pub-111, DIRECT, tag1\n# already present",
                }
            return {
                "status": "issue",
                "missing_lines": (
                    "# New lines from CAS\n"
                    "applovin.com, 222, DIRECT, tag2\n"
                    "unity.com, 333, RESELLER\n"
                ),
            }

        mock_parts.side_effect = fake_parts

        import io
        from contextlib import redirect_stdout

        with redirect_stdout(io.StringIO()):
            res = sync_app_ads_txt(
                api_token="dummy-token",
                target_file_path=str(self.target_file),
                dry_run=False,
                no_pause=True,
            )

        self.assertEqual(res["apps_total"], 2)
        self.assertEqual(res["new_lines_count"], 2)
        self.assertIn("applovin.com, 222, DIRECT, tag2", res["new_lines"])
        self.assertIn("unity.com, 333, RESELLER", res["new_lines"])

        # Check content written to file
        final_content = self.target_file.read_text(encoding="utf-8")
        self.assertIn("google.com, pub-111, DIRECT, tag1", final_content)
        self.assertIn("applovin.com, 222, DIRECT, tag2", final_content)
        self.assertIn("unity.com, 333, RESELLER", final_content)

    @patch("sync.CASApiClient.get_app_ads_txt_parts")
    @patch("sync.CASApiClient.list_all_apps")
    def test_sync_dry_run_does_not_modify_file(self, mock_list_apps, mock_parts):
        import io
        from contextlib import redirect_stdout
        from sync import sync_app_ads_txt

        self.target_file.write_text("google.com, pub-111, DIRECT, tag1\n", encoding="utf-8")

        mock_list_apps.return_value = [
            {"id": "app1", "name": "Game A", "bundle_id": "com.game.a", "platform": "android"},
        ]
        mock_parts.return_value = {
            "status": "issue",
            "missing_lines": "inmobi.com, 555, DIRECT\n",
        }

        with redirect_stdout(io.StringIO()):
            res = sync_app_ads_txt(
                api_token="dummy-token",
                target_file_path=str(self.target_file),
                dry_run=True,
                no_pause=True,
            )

        self.assertTrue(res["dry_run"])
        self.assertEqual(res["new_lines_count"], 1)

        # File should remain unchanged in dry-run
        final_content = self.target_file.read_text(encoding="utf-8")
        self.assertNotIn("inmobi.com", final_content)


class TestCASApiClient(unittest.TestCase):
    """Test CASApiClient initializations and properties."""

    def test_client_init(self):
        client = CASApiClient(api_token="  my-test-token  ")
        self.assertEqual(client.api_token, "my-test-token")
        self.assertEqual(client.base_url, "https://platform-api.cas.ai/api/v2")

    def test_version_present(self):
        self.assertTrue(bool(__version__))
        self.assertRegex(__version__, r"^\d+\.\d+\.\d+")


if __name__ == "__main__":
    unittest.main()
