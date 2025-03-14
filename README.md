![Untitled-1](https://github.com/user-attachments/assets/4b660853-bc07-4432-b335-c765c89d5972)

# 🌑 D.A.R.K Launcher [Open-Source]

An open-source launcher designed to automate downloading, updating, and injecting DLLs into the game "REPO." Supports both Steam and cracked versions.
Also checkout: https://github.com/D4rkks/r.e.p.o-cheat

---

## ⚠️ IMPORTANT
> Before using this launcher, please **turn off Real-Time Protection** or **whitelist the folder** containing the launcher in your antivirus. Rest assured, this launcher is **COMPLETELY SAFE** and does **not** steal personal information.

---

## 🌟 Features
- **Auto Download/Update**: Fetches the latest release from GitHub (`https://api.github.com/repos/D4rkks/r.e.p.o-cheat/releases/latest`).
- **Auto Inject**: Injects the specified DLL into the game process automatically.
- **Steam & Cracked Support**: Compatible with both Steam (AppID: 3241660) and standalone REPO.exe.
- **Command Line Interface**: Advanced control via CLI (e.g., `inject`, `kill`, `restart`).
- **GUI Configuration**: Easy setup with a graphical interface on first run.
- ~~**Mica Effect**: Modern Windows UI with Mica transparency (Windows 11)~~.
- **Customizable**: Configurable via `config.json` or GUI (auto-inject, wait time, etc.).

---

## ❓ How to Use
1. Download the latest release from the link below.
2. Extract `D.A.R.K Launcher.exe` to a new folder.
3. Run the executable:
   - **First Run**: A GUI will prompt you to set the game path (`REPO.exe`) and DLL path (`r.e.p.o.cheat.dll`).
   - **Subsequent Runs**: Auto-downloads updates and injects if configured.
4. Use commands (e.g., `inject 5`) for manual control if needed.

---

## 📋 Commands
- `inject [time] [--force]`: Inject the DLL after `[time]` seconds; `--force` overrides auto-inject restrictions.
- `kill`: Terminate the REPO process.
- `restart [time]`: Kill and restart the game with an optional delay.
- `auto_inject [true/false] [time]`: Toggle auto-injection and set wait time.
- `inject_wait_time`: Open GUI to set injection delay.
- `status`: Show current configuration and game status.
- `download_dll <url>`: Download a DLL from a specified URL.
- `help`: Display this list.

---

## 🙅 Disclaimer
This is an **automated launcher**. Any injection failures are due to the injector (`smi.exe`) or DLL (`r.e.p.o.cheat.dll`), not the launcher itself. We only take responsibility for launcher-specific errors.

---

## 🛠️ Build Instructions
1. Clone this repository: `git clone https://github.com/sang765/DARK-Launcher-Open.git`
2. Install dependencies: `pip install -r requirements.txt`
3. Run the build script: `python py2exe.py`
   - Requires `pyinstaller`, a certificate (`.pfx`), and `signtool.exe`.
   - Configurable via `.env` (see `py2exe.py`).

---

## ⭐ Support Us
Leave a star on our GitHub: [https://github.com/sang765/DARK-Launcher-Open](https://github.com/sang765/DARK-Launcher-Open)

---

## 📜 License
MIT License - See [LICENSE](LICENSE) for details.

---

**Made by SengsDeyy**
