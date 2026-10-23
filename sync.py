#!/usr/bin/env python3
"""
App-ads.txt Sync Tool
Synchronizes missing lines from Clever Ads Solutions (CAS.AI) API into your local app-ads.txt.
Cross-platform: Windows, macOS, Linux.
Zero external dependencies required (uses standard Python library).
"""

import argparse
import getpass
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Ensure UTF-8 output encoding for consoles (e.g. Windows cp1251 / cp866)
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Enable ANSI colors on Windows 10/11
if os.name == "nt":
    os.system("")

CONFIG_FILE_NAME = "config.json"
API_BASE_URL = "https://platform-api.cas.ai/api/v2"
AUTH_BASE_URL = "https://platform-api.cas.ai"


class TerminalColors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    CYAN = "\033[36m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    GRAY = "\033[90m"
    WHITE = "\033[97m"


def print_success(msg: str) -> None:
    print(f"{TerminalColors.GREEN}[+] {msg}{TerminalColors.RESET}")


def print_info(msg: str) -> None:
    print(f"{TerminalColors.CYAN}[*] {msg}{TerminalColors.RESET}")


def print_warning(msg: str) -> None:
    print(f"{TerminalColors.YELLOW}[!] {msg}{TerminalColors.RESET}")


def print_error(msg: str) -> None:
    print(f"{TerminalColors.RED}[x] {msg}{TerminalColors.RESET}")


def print_header(title: str) -> None:
    width = 65
    print(f"\n{TerminalColors.BOLD}{TerminalColors.CYAN}{'=' * width}")
    print(f"  {title}")
    print(f"{'=' * width}{TerminalColors.RESET}\n")


def pause_exit(code: int = 0) -> None:
    """Prompt the user before exiting so the console window remains open."""
    if sys.stdin.isatty():
        try:
            input(f"\n{TerminalColors.GRAY}Нажмите Enter для выхода...{TerminalColors.RESET}")
        except (KeyboardInterrupt, EOFError):
            pass
    sys.exit(code)


class CASApiClient:
    """Client for interacting with Clever Ads Solutions Platform API v2."""

    def __init__(
        self,
        api_token: str,
        base_url: str = API_BASE_URL,
        auth_base_url: str = AUTH_BASE_URL,
    ):
        self.api_token = api_token.strip() if api_token else ""
        self.base_url = base_url.rstrip("/")
        self.auth_base_url = auth_base_url.rstrip("/")

    @staticmethod
    def login_and_get_token(email: str, password: str, auth_base_url: str = AUTH_BASE_URL) -> str:
        """
        Authenticate with email and password in memory.
        Attempts to create a permanent API Key via POST /api/v2/api-keys.
        If that fails, returns the session token directly.
        Password is never written to disk.
        """
        url = f"{auth_base_url.rstrip('/')}/auth/login"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": "AppAdsSync/2.0 (Python; Cross-Platform)",
        }
        payload = {"email": email.strip(), "password": password}
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                resp_data = resp.read().decode("utf-8")
                res = json.loads(resp_data)
                token_data = res.get("data") or res
                session_token = token_data.get("token") or ""
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            try:
                err_json = json.loads(body)
                msg = (
                    err_json.get("error", {}).get("message")
                    or err_json.get("message")
                    or body
                )
            except Exception:
                msg = body
            raise PermissionError(f"Login failed: {msg}")
        except Exception as e:
            raise ConnectionError(f"Network error during login: {e}")

        if not session_token:
            raise PermissionError("Server did not return an authentication token.")

        # Try to generate a persistent API Key
        try:
            api_keys_url = f"{API_BASE_URL}/api-keys"
            api_req = urllib.request.Request(
                api_keys_url,
                data=json.dumps({"name": "AppAdsSync"}).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {session_token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "X-Requested-With": "XMLHttpRequest",
                    "User-Agent": "AppAdsSync/2.0",
                },
                method="POST",
            )
            with urllib.request.urlopen(api_req, timeout=15) as api_resp:
                api_res = json.loads(api_resp.read().decode("utf-8"))
                created_key = api_res.get("data", {}).get("token")
                if created_key:
                    return created_key
        except Exception:
            # Fall back to session token if /api-keys endpoint is restricted
            pass

        return session_token

    def _request(
        self,
        endpoint: str,
        method: str = "GET",
        payload: Optional[Dict[str, Any]] = None,
        retries: int = 3,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        data = json.dumps(payload).encode("utf-8") if payload is not None else None

        for attempt in range(1, retries + 1):
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "X-Requested-With": "XMLHttpRequest",
                "User-Agent": "AppAdsSync/2.0 (Python; Cross-Platform)",
            }
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    resp_data = resp.read().decode("utf-8")
                    if not resp_data.strip():
                        return {}
                    return json.loads(resp_data)
            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8", errors="replace")
                try:
                    err_json = json.loads(err_body)
                    err_msg = err_json.get("message") or err_json.get("error", {}).get("message") or err_body
                except Exception:
                    err_msg = err_body

                if e.code == 401:
                    raise PermissionError(
                        f"Authentication failed (HTTP 401): Invalid or expired token.\n"
                        f"Details: {err_msg}\n"
                        f"Please re-run the tool or update config.json with a valid token."
                    )
                elif e.code == 403:
                    raise PermissionError(
                        f"Access forbidden (HTTP 403): Token lacks permission.\nDetails: {err_msg}"
                    )
                elif e.code == 429 and attempt < retries:
                    wait_sec = 2 * attempt
                    print_warning(f"Rate limited (HTTP 429). Retrying in {wait_sec}s...")
                    time.sleep(wait_sec)
                    continue
                else:
                    raise RuntimeError(f"HTTP {e.code} on {method} {url}: {err_msg}")
            except urllib.error.URLError as e:
                if attempt < retries:
                    time.sleep(2)
                    continue
                raise ConnectionError(f"Network error connecting to {url}: {e.reason}")

        raise RuntimeError("Exceeded maximum retries.")

    def list_all_apps(self) -> List[Dict[str, Any]]:
        """Fetch all mobile applications associated with the account, handling pagination."""
        apps: List[Dict[str, Any]] = []
        cursor: Optional[str] = None

        while True:
            payload: Dict[str, Any] = {"per_page": 100}
            if cursor:
                payload["cursor"] = cursor

            res = self._request("/apps", method="POST", payload=payload)
            page_data = res.get("data", [])
            apps.extend(page_data)

            meta = res.get("meta", {})
            has_more = meta.get("has_more", False)
            next_cursor = meta.get("next_cursor")

            if not has_more or not next_cursor:
                break
            cursor = next_cursor

        return apps

    def get_app_ads_txt_parts(self, app_id: str) -> Dict[str, Any]:
        """Fetch app-ads.txt parts (seller line, developer part, missing lines, status) for a specific app."""
        res = self._request(f"/apps/{app_id}/app-ads-txt", method="GET")
        return res.get("data", {})

    def recheck_app_ads_txt(self, app_id: str) -> Dict[str, Any]:
        """Request CAS to re-verify the published app-ads.txt file for an app."""
        res = self._request(f"/apps/{app_id}/app-ads-txt/recheck", method="POST")
        return res.get("data", {})


def canonical_record_key(line: str) -> Optional[Tuple[str, ...]]:
    """
    Extract canonical identity tuple for an app-ads.txt record to avoid duplicates.
    Example line: 'google.com, pub-1234567890123456, DIRECT, f08c47fec0942fa0 # comment'
    Returns: ('google.com', 'pub-1234567890123456', 'DIRECT')
    """
    line_without_comment = line.split("#")[0].strip()
    if not line_without_comment:
        return None

    parts = [p.strip() for p in line_without_comment.split(",")]
    if len(parts) >= 3:
        # domain, publisher_id, account_type (DIRECT / RESELLER)
        return (parts[0].lower(), parts[1].lower(), parts[2].upper())
    elif len(parts) == 2:
        return (parts[0].lower(), parts[1].lower())
    return (line_without_comment.lower(),)


def parse_existing_file(filepath: Path) -> Tuple[List[str], Set[Tuple[str, ...]], Set[str]]:
    """Read existing app-ads.txt file and extract existing records for deduplication."""
    if not filepath.exists():
        return [], set(), set()

    raw_lines: List[str] = []
    seen_keys: Set[Tuple[str, ...]] = set()
    seen_stripped_lines: Set[str] = set()

    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            raw_lines.append(line)
            stripped = line.strip()
            if stripped:
                seen_stripped_lines.add(stripped)
                key = canonical_record_key(stripped)
                if key:
                    seen_keys.add(key)

    return raw_lines, seen_keys, seen_stripped_lines


def load_or_create_config(config_path: Path) -> Dict[str, Any]:
    """
    Load config.json or prompt the user interactively on first run.
    Note: Passwords are NEVER saved in config.json. Only the obtained API token is saved.
    """
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                if config.get("api_token") and config.get("target_file_path"):
                    print_success(f"Конфигурация загружена из {config_path}")
                    return config
        except Exception as e:
            print_warning(f"Не удалось прочитать {config_path}: {e}")

    print_header("Настройка авторизации и параметров")
    print(f"{TerminalColors.WHITE}Выберите способ авторизации в Clever Ads Solutions:{TerminalColors.RESET}\n")
    print(f"  {TerminalColors.BOLD}1{TerminalColors.RESET}) Вход по Email и Паролю")
    print(f"     {TerminalColors.GRAY}Пароль используется однократно для генерации токена и НЕ сохраняется на диск!{TerminalColors.RESET}")
    print(f"  {TerminalColors.BOLD}2{TerminalColors.RESET}) Ввести токен вручную")
    print(f"     {TerminalColors.GRAY}Скопировать 'onebi_actor_token' из DevTools браузера (F12 -> Application -> Local Storage){TerminalColors.RESET}\n")

    choice = ""
    while choice not in ("1", "2"):
        choice = input(f"{TerminalColors.BOLD}Выберите вариант [1/2]: {TerminalColors.RESET}").strip()

    api_token = ""

    if choice == "1":
        email = ""
        while not email:
            email = input(f"{TerminalColors.BOLD}Введите CAS Email: {TerminalColors.RESET}").strip()

        password = ""
        while not password:
            try:
                password = getpass.getpass(f"{TerminalColors.BOLD}Введите CAS Пароль: {TerminalColors.RESET}")
            except Exception:
                password = input(f"{TerminalColors.BOLD}Введите CAS Пароль: {TerminalColors.RESET}")
            if not password:
                print_warning("Пароль не может быть пустым.")

        print_info("Авторизация на сервере CAS...")
        try:
            api_token = CASApiClient.login_and_get_token(email, password)
            del password  # Immediately erase password from memory
            print_success("Авторизация успешна! Получен токен доступа.")
        except Exception as e:
            print_error(f"Ошибка входа: {e}")
            pause_exit(1)
    else:
        print_info(
            "Подсказка: на сайте https://platform.cas.ai откройте DevTools (F12) -> Application\n"
            "           -> Local Storage -> https://platform.cas.ai -> скопируйте значение 'onebi_actor_token'"
        )
        while not api_token.strip():
            api_token = input(f"{TerminalColors.BOLD}Введите токен CAS: {TerminalColors.RESET}").strip()

    target_file_path = ""
    while not target_file_path.strip():
        target_file_path = input(
            f"{TerminalColors.BOLD}Укажите путь к файлу app-ads.txt (напр. C:\\Projects\\site\\app-ads.txt): {TerminalColors.RESET}"
        ).strip().strip('"').strip("'")

    # Only save the token and target path. Never save passwords!
    config: Dict[str, Any] = {
        "api_token": api_token,
        "target_file_path": target_file_path,
    }

    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
        print_success(f"Конфигурация успешно сохранена в {config_path} (пароль не сохранялся!)\n")
    except Exception as e:
        print_warning(f"Не удалось записать {config_path}: {e}\n")

    return config


def sync_app_ads_txt(
    api_token: str,
    target_file_path: str,
    dry_run: bool = False,
    recheck_remote: bool = False,
) -> None:
    target_path = Path(target_file_path).expanduser().resolve()
    print_info(f"Целевой файл: {TerminalColors.WHITE}{target_path}{TerminalColors.RESET}")

    # Parse existing file
    existing_lines, seen_keys, seen_stripped_lines = parse_existing_file(target_path)
    initial_existing_count = len([l for l in existing_lines if l.strip()])
    if target_path.exists():
        print_info(
            f"Найден локальный файл: {len(existing_lines)} строк ({len(seen_keys)} уникальных записей, {initial_existing_count} непустых)"
        )
    else:
        print_info("Локальный файл пока отсутствует — он будет создан автоматически.")

    # Initialize API Client
    client = CASApiClient(api_token=api_token)

    # 1. Fetch apps
    print_info("Запрос списка приложений из CAS API...")
    try:
        apps = client.list_all_apps()
    except Exception as e:
        print_error(f"Не удалось получить список приложений: {e}")
        pause_exit(1)

    print_success(f"Найдено приложений в аккаунте CAS: {len(apps)}")

    # 2. Iterate through apps and collect missing lines
    total_missing_lines_collected: List[str] = []
    apps_with_missing_lines = 0
    apps_with_issues = 0
    apps_ok = 0
    apps_detailed_report: List[Dict[str, Any]] = []

    print_header("Проверка приложений и missing_lines")

    for idx, app in enumerate(apps, 1):
        app_id = app.get("id", "unknown")
        app_name = app.get("name") or "Unnamed App"
        bundle_id = app.get("bundle_id") or "No bundle ID"
        platform = (app.get("platform") or "unknown").upper()
        cas_status = app.get("app_ads_status") or "unknown"

        display_name = f"{app_name} ({bundle_id}) [{platform}]"

        try:
            if recheck_remote:
                print(f"  [{idx}/{len(apps)}] Запрос перепроверки CAS для {display_name}...", end="", flush=True)
                parts = client.recheck_app_ads_txt(app_id)
                print(" готово.")
            else:
                parts = client.get_app_ads_txt_parts(app_id)

            status = parts.get("status") or cas_status
            landing_url = parts.get("landing_url")
            missing_text = parts.get("missing_lines") or ""
            raw_missing_lines = [line.strip() for line in missing_text.splitlines() if line.strip()]

            # Analyze missing lines
            new_lines_for_app: List[str] = []
            already_present_for_app: List[str] = []

            for line in raw_missing_lines:
                if line.startswith("#"):
                    continue

                key = canonical_record_key(line)
                if (key and key in seen_keys) or line in seen_stripped_lines:
                    already_present_for_app.append(line)
                else:
                    new_lines_for_app.append(line)
                    seen_stripped_lines.add(line)
                    if key:
                        seen_keys.add(key)

            if status in ("issue", "unchecked") or new_lines_for_app:
                apps_with_issues += 1
            else:
                apps_ok += 1

            app_report = {
                "idx": idx,
                "name": app_name,
                "bundle_id": bundle_id,
                "platform": platform,
                "status": status,
                "landing_url": landing_url,
                "total_missing": len(raw_missing_lines),
                "new_added": len(new_lines_for_app),
                "already_present": len(already_present_for_app),
                "new_lines": new_lines_for_app,
            }
            apps_detailed_report.append(app_report)

            # Print status line
            status_color = (
                TerminalColors.GREEN if status == "ok" and not new_lines_for_app
                else TerminalColors.YELLOW if new_lines_for_app
                else TerminalColors.RED
            )
            status_icon = (
                "[+]" if status == "ok" and not new_lines_for_app
                else "[!]" if new_lines_for_app
                else "[-]"
            )

            print(
                f"  {status_color}{status_icon} [{idx}/{len(apps)}] {display_name}{TerminalColors.RESET}\n"
                f"      Статус в CAS: {TerminalColors.BOLD}{status.upper()}{TerminalColors.RESET} | "
                f"Строк в CAS missing: {len(raw_missing_lines)} | "
                f"Новых для файла: {TerminalColors.GREEN}+{len(new_lines_for_app)}{TerminalColors.RESET}"
            )
            if landing_url:
                print(f"      {TerminalColors.GRAY}Landing URL: {landing_url}{TerminalColors.RESET}")

            if new_lines_for_app:
                apps_with_missing_lines += 1
                total_missing_lines_collected.extend(new_lines_for_app)
                for nl in new_lines_for_app:
                    print(f"        {TerminalColors.GREEN}+ {nl}{TerminalColors.RESET}")

            print()

        except Exception as e:
            print_error(f"  [{idx}/{len(apps)}] Ошибка получения данных для {display_name}: {e}\n")

    # 3. Print Comprehensive Summary
    print_header("Итоговый отчет о синхронизации")

    print(f"  Всего приложений в CAS:        {TerminalColors.BOLD}{len(apps)}{TerminalColors.RESET}")
    print(f"  Приложений в статусе OK:       {TerminalColors.GREEN}{apps_ok}{TerminalColors.RESET}")
    print(f"  Приложений с замечаниями:      {TerminalColors.YELLOW if apps_with_issues else TerminalColors.GREEN}{apps_with_issues}{TerminalColors.RESET}")
    print(f"  Приложений, давших новые строки:{TerminalColors.BOLD}{apps_with_missing_lines}{TerminalColors.RESET}")
    print(f"  -------------------------------------------------------------")
    print(f"  Строк в файле ДО синхронизации: {TerminalColors.BOLD}{initial_existing_count}{TerminalColors.RESET}")
    print(f"  Новых уникальных строк найдено: {TerminalColors.GREEN}{TerminalColors.BOLD}+{len(total_missing_lines_collected)}{TerminalColors.RESET}")
    print(f"  Всего строк в файле ПОСЛЕ:      {TerminalColors.BOLD}{initial_existing_count + len(total_missing_lines_collected)}{TerminalColors.RESET}")

    if not total_missing_lines_collected:
        print(f"\n{TerminalColors.GREEN}✔ Все строки уже присутствуют в вашем app-ads.txt! Файл полностью актуален.{TerminalColors.RESET}")
        return

    # Print preview of lines
    print(f"\n{TerminalColors.BOLD}{TerminalColors.CYAN}Список строк для добавления ({len(total_missing_lines_collected)} шт.):{TerminalColors.RESET}")
    for i, line in enumerate(total_missing_lines_collected, 1):
        print(f"  {TerminalColors.GRAY}{i:02d}.{TerminalColors.RESET} {TerminalColors.GREEN}{line}{TerminalColors.RESET}")

    if dry_run:
        print_warning("\n[DRY RUN] Режим предпросмотра: файл не изменялся на диске.")
        return

    # 4. Write / Append to target file
    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)

        needs_leading_newline = False
        if target_path.exists() and target_path.stat().st_size > 0:
            with open(target_path, "rb") as f:
                f.seek(-1, os.SEEK_END)
                last_char = f.read(1)
                if last_char != b"\n":
                    needs_leading_newline = True

        with open(target_path, "a" if target_path.exists() else "w", encoding="utf-8") as f:
            if needs_leading_newline:
                f.write("\n")
            for line in total_missing_lines_collected:
                f.write(f"{line}\n")

        print_success(f"\nФайл успешно обновлен: {target_path}")
        print(
            f"\n{TerminalColors.BOLD}{TerminalColors.GREEN}"
            f"=== Синхронизация завершена! Закоммитьте и отправьте изменения в Git: ==="
            f"{TerminalColors.RESET}"
        )
        print(f"  {TerminalColors.WHITE}git add app-ads.txt{TerminalColors.RESET}")
        print(f"  {TerminalColors.WHITE}git commit -m \"Update app-ads.txt with CAS mediation lines\"{TerminalColors.RESET}")
        print(f"  {TerminalColors.WHITE}git push{TerminalColors.RESET}\n")

    except Exception as e:
        print_error(f"Не удалось записать в {target_path}: {e}")
        pause_exit(1)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Синхронизация недостающих строк из Clever Ads Solutions API в локальный файл app-ads.txt."
    )
    parser.add_argument(
        "--config",
        "-c",
        default=CONFIG_FILE_NAME,
        help=f"Путь к JSON-файлу конфигурации (по умолчанию: {CONFIG_FILE_NAME})",
    )
    parser.add_argument(
        "--token",
        "-t",
        help="CAS API Токен (переопределяет config.json)",
    )
    parser.add_argument(
        "--target",
        "-p",
        help="Путь к файлу app-ads.txt (переопределяет config.json)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Показать недостающие строки без изменения файла на диске",
    )
    parser.add_argument(
        "--recheck",
        action="store_true",
        help="Запросить у CAS перепроверку опубликованного файла перед получением строк",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    config_path = Path(args.config).resolve()

    # Priority: CLI arguments -> Environment variables -> config.json
    api_token = args.token or os.environ.get("CAS_API_TOKEN")
    target_path = args.target or os.environ.get("APP_ADS_TXT_PATH")

    if not api_token or not target_path:
        config = load_or_create_config(config_path)
        api_token = api_token or config.get("api_token")
        target_path = target_path or config.get("target_file_path")

    if not api_token or not target_path:
        print_error("Отсутствует токен авторизации или путь к файлу app-ads.txt.")
        pause_exit(1)

    sync_app_ads_txt(
        api_token=api_token,
        target_file_path=target_path,
        dry_run=args.dry_run,
        recheck_remote=args.recheck,
    )
    pause_exit(0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{TerminalColors.YELLOW}Операция отменена пользователем.{TerminalColors.RESET}")
        pause_exit(130)
