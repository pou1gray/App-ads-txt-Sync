# App-ads Sync

Cross-platform tool to automatically synchronize and merge missing `app-ads.txt` records from **Clever Ads Solutions (CAS.AI) Platform API** into your local `app-ads.txt` file.

Works on **Windows, macOS, and Linux** with **zero external pip dependencies** (uses standard Python 3.7+ libraries).

---

## Features

- **Direct CAS API Integration**: Connects to the official [CAS Platform API](https://platform-api.cas.ai/docs/api).
- **Two Easy Authentication Options**:
  - **Login & Password**: Use your standard CAS account credentials (recommended - automatically manages and refreshes session tokens).
  - **Token**: Use your existing token / API key (from DevTools or environment).
- **Per-Application Audit**: Iterates through all applications in your CAS account and queries missing lines (`AppAdsTxtPartsResource`).
- **Smart Non-Destructive Merge**:
  - Automatically identifies missing lines across all your apps.
  - Checks against your existing `app-ads.txt` records (canonicalizing domain, publisher ID, and account type to prevent duplicates).
  - Appends only new, unique lines without touching or breaking your custom existing records.
- **Cross-Platform**: Run on Windows, macOS, or Linux.
- **Safe Modes**: Includes `--dry-run` to preview changes and `--recheck` to trigger CAS remote verification.

---

## Requirements

- Python 3.7+ installed. No `pip install` required!

---

## Getting Started

### 1. Launch

**Windows:**
```bat
run.bat
```
*(or `python sync.py`)*

**macOS / Linux:**
```bash
chmod +x run.sh
./run.sh
```
*(or `python3 sync.py`)*

### 2. First Run Setup

On first launch, the program will prompt you for configuration:

1. **Authentication Method**:
   - **Method 1 (Recommended)**: Log in with your CAS Email & Password. The tool connects to `https://platform-api.cas.ai/auth/login`, obtains the token, and will automatically refresh it if it expires.
   - **Method 2**: Enter your token manually. You can copy it from `https://platform.cas.ai` in browser DevTools:
     `F12` &rarr; **Application** &rarr; **Local Storage** &rarr; `https://platform.cas.ai` &rarr; `onebi_actor_token`.
2. **Target File Path**: Path to your local `app-ads.txt` (for example: `C:\Projects\my-site\app-ads.txt` or `~/my-site/app-ads.txt`).

Settings are saved to `config.json` (git-ignored to protect your credentials). On subsequent runs, simply execute `run.bat` or `./run.sh`!

### 3. Commit and Push
Once the missing lines have been merged into your local repository, commit and push:
```bash
git add app-ads.txt
git commit -m "Update app-ads.txt with CAS mediation lines"
git push
```

---

## CLI Options

```bash
# Preview what would be added without modifying files
python sync.py --dry-run

# Force CAS to re-verify published app-ads.txt before fetching
python sync.py --recheck

# Override credentials or target path via CLI
python sync.py --token YOUR_TOKEN --target ./app-ads.txt

# Custom configuration file
python sync.py --config custom_config.json
```

### Environment Variables
You can also use environment variables (ideal for CI/CD or automated cron jobs):
- `CAS_API_TOKEN`
- `APP_ADS_TXT_PATH`