# 🧰 Tools Pro Kit – Code Archiver + Secret Scanner

An all‑rounder toolkit that gives you:

- **v4compiler** – Archive any project into a single text file (and rebuild it later).  
- **Gitleaks** – Block secrets from ever touching your Git history.

---

## ⚡ Quick Install (Windows)

1. **Clone the repo**
   ```cmd
   git clone https://github.com/your-username/tools-pro-kit.git
   cd tools-pro-kit
   ```

2. **Run the one‑click setup**
   ```cmd
   setup.bat
   ```
   This installs Gitleaks, pre‑commit, and activates the Git hook.

3. **Add the right‑click menu (optional)**
   - Double‑click `Add-V4Compiler-Menu.reg`
   - Confirm the prompts.

> 💡 **Trick:** The `.reg` file assumes `v4compiler.py` lives at `C:\PathH\`.  
> If you store it somewhere else, edit the `.reg` file first.

---

## 📦 Using v4compiler

| Method | Command / Action |
|--------|------------------|
| **GUI via right‑click** | Right‑click any folder → **"Make Tree.txt (v4compiler)"** |
| **Command line** | `python C:\PathH\v4compiler.py "C:\my-project"` |

---

## 🔐 Scanning for Secrets

- **Automatic on commit** – Every `git commit` is scanned. If a secret is found, the commit is **blocked**.
- **Manual scan of any folder**  
  ```powershell
  .\scripts\scan-folder.ps1 "C:\path\to\scan"
  ```
  (Just double‑click the script and paste the path when asked.)

---

## 🧠 Pro Tricks

- **Use `.gitleaks.toml`** – Add custom rules or whitelist known false positives.  
  Place it in the root of any project you want to protect.
- **Portable setup** – Keep this repo on a USB stick. Run `setup.bat` on any new machine.
- **Skip the GUI** – Use v4compiler purely as a CLI tool:  
  ```cmd
  python C:\PathH\v4compiler.py collect --root . --output mydump.txt
  ```

---

## 🧹 Uninstall

- Remove the pre‑commit hook from a repo: `pre-commit uninstall`
- Remove the right‑click menu: double‑click `Remove-V4Compiler-Menu.reg`

---

**Made with 💖 by Pavneet**