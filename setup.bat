@echo off
title Tools Pro Kit – One‑Click Setup
echo ========================================
echo     Tools Pro Kit – Installer
echo ========================================
echo.

:: ---------- Gitleaks ----------
echo [1/3] Checking Gitleaks...
where gitleaks >nul 2>nul
if %errorlevel% neq 0 (
    echo   -> Installing Gitleaks via winget...
    winget install Gitleaks.Gitleaks --accept-package-agreements --accept-source-agreements
    if %errorlevel% neq 0 (
        echo   [!] Winget failed. Download manually from:
        echo       https://github.com/gitleaks/gitleaks/releases
        pause
        exit /b 1
    )
) else (
    echo   -> Gitleaks is already installed.
)

:: ---------- pre-commit ----------
echo.
echo [2/3] Checking pre-commit...
where pre-commit >nul 2>nul
if %errorlevel% neq 0 (
    echo   -> Installing pre-commit via pip...
    pip install pre-commit
    if %errorlevel% neq 0 (
        echo   [!] Pip install failed. Ensure Python and pip are in PATH.
        pause
        exit /b 1
    )
) else (
    echo   -> pre-commit is already installed.
)

:: ---------- Activate Hook ----------
echo.
echo [3/3] Installing Git pre-commit hook...
pre-commit install

echo.
echo ========================================
echo ✅ Setup complete!
echo ========================================
echo.
echo - Gitleaks will now scan every commit.
echo - To scan any folder manually:
echo     .\scripts\scan-folder.ps1
echo.
echo - Right‑click menu for v4compiler:
echo     Double‑click Add-V4Compiler-Menu.reg
echo.
pause
