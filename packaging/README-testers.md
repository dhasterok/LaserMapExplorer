# Laser Map Explorer — tester build

Thanks for helping test LaME. Nothing needs to be installed: no Python, no conda, no
Node. Download the file for your platform, open it, and run the app.

These builds are **not code-signed**, so both operating systems will warn you the first
time. That is expected — the steps below are how you get past it.

---

## macOS (Apple Silicon — M1 and later)

1. Open `LaME-macos-arm64.dmg` and drag **LaME** into **Applications**.
2. **Right-click** (or Control-click) the LaME icon → **Open** → **Open** in the dialog.

   Double-clicking the first time will *not* work — macOS will say the app "cannot be
   opened because the developer cannot be verified". Right-click → Open is what gives
   you the "Open" button. You only need to do this once; after that it launches normally.

If it still refuses, open Terminal and run:

```
xattr -dr com.apple.quarantine /Applications/LaME.app
```

The first launch takes noticeably longer than later ones while macOS verifies the app.

## Windows (64-bit)

1. Unzip `LaME-windows-x64.zip` somewhere you can write to — your Desktop or Documents
   folder is fine. **Do not run it from inside the zip**, and avoid `Program Files`.
2. Run `LaME.exe` from the unzipped folder.
3. Windows SmartScreen will show *"Windows protected your PC"*. Click **More info**, then
   **Run anyway**.

Keep the whole unzipped folder together — `LaME.exe` needs the files beside it.

---

## Where your data is kept

LaME never writes into its own installation folder, so your projects and settings
survive reinstalling or replacing the app:

| | |
|---|---|
| macOS | `~/Library/Application Support/LaME` |
| Windows | `%APPDATA%\LaME` |

Inside you will find `logs/` (diagnostics), `projects/` (saved projects), and `saved/`
(exported data and figures).

## Reporting a problem

Please include:

- What you were doing, and what you expected instead.
- Your operating system and version.
- **The log file** — `logs/lame.log` in the folder above. This is the single most useful
  thing you can attach.
- A screenshot, if anything looked wrong on screen.

Open an issue at <https://github.com/dhasterok/LaserMapExplorer/issues>, or send the
details to whoever gave you this build.

## Known rough edges in a test build

- The app is large (~800 MB installed) because it ships its own Python, Qt and a browser
  engine. That is normal for this kind of build.
- Startup is slow the first time — several seconds while fonts and the browser engine
  initialise.
- The security warnings above are purely because the build is unsigned; they are not a
  sign that anything is wrong with the app.
