import os
import time
import json
import tkinter
import requests
import subprocess
import sys
import psutil
import ctypes
import logging
import re
import hashlib
import shutil
import threading
import winreg
import glob
import win32gui
import win32con
import win32api
from concurrent.futures import ThreadPoolExecutor
from tkinter import filedialog, messagebox, Tk, Label, Checkbutton, Entry, simpledialog
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from colorama import init, Fore, Style
from PIL import Image, ImageTk
from pathlib import Path

init()

NO_INJECT_MODE = "--no-inject" in sys.argv
NO_CONSOLE_MODE = "--no-console" in sys.argv

DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_MICA_EFFECT = 1029

NAMESPACE_MAPPING = {
    "Stable": "r.e.p.o_cheat",
    "Beta": "dark_cheat"
}

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def setup_icon():
    icon_name = "icon.ico"
    source_icon = resource_path(icon_name)
    temp_dir = os.getenv('TEMP')
    temp_icon_path = os.path.join(temp_dir, f"DARK_Launcher_{os.getpid()}_{icon_name}")
    
    try:
        if not os.path.exists(source_icon):
            print(f"{Fore.YELLOW}⚠ Source icon not found at {source_icon}. Skipping icon setup.{Style.RESET_ALL}")
            return None
        if not os.path.exists(temp_icon_path):
            shutil.copy2(source_icon, temp_icon_path)
        return temp_icon_path
    except Exception as e:
        print(f"{Fore.RED}❌ Failed to copy icon to temp folder: {e}{Style.RESET_ALL}")
        return None

def set_app_user_model_id():
    try:
        app_id = "DARKLauncher"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception as e:
        print(f"{Fore.YELLOW}⚠ Failed to set AppUserModelID: {e}{Style.RESET_ALL}")

def setup_logging():
    try:
        logging.basicConfig(filename="launcher.log", level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
        logging.info("Logging initialized successfully")
    except Exception as e:
        print(f"{Fore.RED}❌ Failed to setup logging: {e}{Style.RESET_ALL}")
        raise

def is_windows_terminal_installed():
    try:
        result = subprocess.run(['where', 'wt'], capture_output=True, text=True, shell=True)
        if result.returncode == 0 and result.stdout.strip():
            wt_path = result.stdout.strip().splitlines()[0]
            if os.path.exists(wt_path):
                return wt_path

        wt_path = os.path.join(os.getenv("LocalAppData"), "Microsoft", "WindowsApps", "wt.exe")
        if os.path.exists(wt_path):
            return wt_path
        
        wt_path = os.path.join(os.getenv("ProgramFiles"), "WindowsApps", "Microsoft.WindowsTerminal_*", "wt.exe")
        for path in glob.glob(wt_path):
            if os.path.exists(path):
                return path
        
        return None
    except Exception as e:
        print(f"{Fore.YELLOW}⚠ Cannot check Windows Terminal: {e}{Style.RESET_ALL}")
        return None

def is_admin():
    return ctypes.windll.shell32.IsUserAnAdmin() != 0

def is_uac_enabled():
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System")
        enable_lua, _ = winreg.QueryValueEx(key, "EnableLUA")
        winreg.CloseKey(key)
        return enable_lua == 1
    except Exception as e:
        print(f"{Fore.YELLOW}⚠ Unable to determine UAC state: {e}. Assumed UAC is enabled.{Style.RESET_ALL}")
        return True

def run_as_admin():
    if not is_admin():
        try:
            uac_enabled = is_uac_enabled()
            exe_path = sys.executable
            args = " ".join(sys.argv)
            
            wt_path = is_windows_terminal_installed()
            
            if wt_path:
                cmd = f'"{exe_path}" {args}'
                print(f"{Fore.YELLOW}⚠ Requesting admin rights via Windows Terminal...{Style.RESET_ALL}")
                ctypes.windll.shell32.ShellExecuteW(None, "runas", wt_path, f'-p "Command Prompt" /c {cmd}', None, 1)
            else:
                cmd = f'"{exe_path}" {args}'
                print(f"{Fore.YELLOW}⚠ Requesting admin rights via CMD (Windows Terminal not available)...{Style.RESET_ALL}")
                ctypes.windll.shell32.ShellExecuteW(None, "runas", "cmd.exe", f'/c {cmd}', None, 1)
            sys.exit(0)
        except Exception as e:
            print(f"{Fore.RED}❌ Cannot runnin with admin: {e}{Style.RESET_ALL}")
            sys.exit(1)
    else:
        print(f"{Fore.GREEN}✅ Running with admin.{Style.RESET_ALL}")

def get_latest_release(config, channel_override=None):
    channels = {
        "Stable": "https://api.github.com/repos/D4rkks/r.e.p.o-cheat/releases/latest",
        "Beta": "https://api.github.com/repos/peeberpoober/beta-r.e.p.o-cheat/releases/latest"
    }
    url = channels.get(channel_override or config["channel"], channels["Stable"])
    try:
        response = requests.get(url)
        if response.status_code != 200:
            print(f"{Fore.RED}❌ Failed to fetch latest release from {url}: {response.status_code}{Style.RESET_ALL}")
            logging.error(f"Failed to fetch release from {url}: {response.status_code}")
            return None
        return response.json()
    except requests.RequestException as e:
        print(f"{Fore.RED}❌ Network error fetching release from {url}: {e}{Style.RESET_ALL}")
        logging.error(f"Network error fetching release from {url}: {e}")
        return None

def format_size(size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"

def download_file(url, filename, config=None):
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        total_size = int(response.headers.get('content-length', 0))
        downloaded_size = 0
        start_time = time.time()

        bar_length = 30
        print(f"{Fore.CYAN}⬇ Downloading {filename}...{Style.RESET_ALL}")

        if not os.access(os.path.dirname(filename) or '.', os.W_OK):
            raise PermissionError(f"No write permission for directory of {filename}")

        with open(filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    elapsed_time = time.time() - start_time
                    
                    if total_size > 0 and elapsed_time > 0:
                        download_speed = downloaded_size / elapsed_time
                        remaining_size = total_size - downloaded_size
                        eta = remaining_size / download_speed if download_speed > 0 else 0

                        percent = downloaded_size / total_size
                        filled_length = int(bar_length * percent)
                        bar = '=' * filled_length + '-' * (bar_length - filled_length)
                        size_info = f"{format_size(downloaded_size)} / {format_size(total_size)}"
                        eta_info = f"ETA: {eta:.1f}s" if eta > 0 else "ETA: Calculating..."
                        sys.stdout.write(f"\r{Fore.GREEN}[{bar}] {percent * 100:.1f}% | {size_info} | {eta_info}{Style.RESET_ALL}")
                        sys.stdout.flush()

        if total_size > 0:
            elapsed_time = time.time() - start_time
            size_info = f"{format_size(downloaded_size)} / {format_size(total_size)}"
            sys.stdout.write(f"\r{Fore.GREEN}[{'=' * bar_length}] 100.0% | {size_info} | Done in {elapsed_time:.1f}s{Style.RESET_ALL}\n")
        else:
            print(f"{Fore.GREEN}✅ Download completed (size unknown) in {time.time() - start_time:.1f}s{Style.RESET_ALL}")

        return os.path.getsize(filename)

    except requests.RequestException as e:
        print(f"{Fore.RED}❌ Network error downloading {filename}: {e}{Style.RESET_ALL}")
        logging.error(f"Network error downloading {filename}: {e}")
        return 0
    except PermissionError as e:
        print(f"{Fore.RED}❌ Permission error: {e}{Style.RESET_ALL}")
        logging.error(f"Permission error: {e}")
        return 0
    except Exception as e:
        print(f"{Fore.RED}❌ Unexpected error downloading {filename}: {e}{Style.RESET_ALL}")
        logging.error(f"Unexpected error downloading {filename}: {e}", exc_info=True)
        return 0

def compute_file_hash(filename):
    hash_md5 = hashlib.md5()
    with open(filename, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def parse_version_file():
    if not os.path.exists("version.txt"):
        return None, None, {}
    
    with open("version.txt", "r") as f:
        content = f.read().strip().splitlines()
    
    version = None
    title = None
    files = {}
    for line in content:
        if line.startswith("version:"):
            version = line.split("version:")[1].strip()
        elif line.startswith("title:"):
            title = line.split("title:")[1].strip()
        elif line.strip() and not line.startswith("---"):
            parts = line.split()
            if len(parts) == 2:
                filename, size = parts
                files[filename] = int(size)
    
    return version, title, files

def write_version_file(version, title, files):
    with open("version.txt", "w") as f:
        f.write("-------------------------\n")
        f.write(f"version: {version}\n")
        f.write(f"title: {title}\n")
        f.write("-------------------------\n")
        for filename, size in files.items():
            f.write(f"{filename} {size}\n")
        f.write("-------------------------\n")

def check_and_update(config):
    latest_release = get_latest_release(config)
    if not latest_release:
        print(f"{Fore.RED}❌ Could not check for updates. Skipping...{Style.RESET_ALL}")
        return
    github_version = latest_release['tag_name']
    github_title = latest_release['name']
    github_assets = {asset['name']: asset for asset in latest_release['assets']}
    
    local_version, local_title, local_files = parse_version_file()
    
    if config["channel"] == "Stable":
        expected_files = ["smi.exe", "SharpMonoInjector.dll", "r.e.p.o.cheat.dll"]
    else:
        expected_files = ["dark_cheat.dll"]

    print(f"{Fore.CYAN}🔍 Checking for updates...{Style.RESET_ALL}")
    logging.info("Checking for updates")

    if local_version != github_version or local_title != github_title:
        print(f"{Fore.YELLOW}🔄 Update detected: Version ({local_version} ≠ {github_version}) or Title ({local_title} ≠ {github_title}). Updating all files...{Style.RESET_ALL}")
        logging.info(f"Update detected: local_version={local_version}, github_version={github_version}, local_title={local_title}, github_title={github_title}")
        for filename in expected_files:
            if os.path.exists(filename):
                os.remove(filename)
                print(f"{Fore.RED}🗑️ Deleted local file: {filename}{Style.RESET_ALL}")
        
        new_files = {}
        for filename in expected_files:
            if filename in github_assets:
                download_url = github_assets[filename]['browser_download_url']
                size = download_file(download_url, filename, config)
                new_files[filename] = size
                logging.info(f"Downloaded {filename}, size={size}")
            else:
                print(f"{Fore.YELLOW}⚠ File {filename} not found in GitHub release for {config['channel']} channel.{Style.RESET_ALL}")
        write_version_file(github_version, github_title, new_files)
        config["last_version_check"] = time.time()
        save_config(config)
        print(f"{Fore.GREEN}✅ Update completed to version {github_version} (Title: {github_title})!{Style.RESET_ALL}")
        return

    updated = False
    new_files = local_files.copy()
    
    for filename in expected_files:
        if filename not in github_assets:
            if filename in local_files:
                print(f"{Fore.YELLOW}⚠ File {filename} not found in GitHub release. Replacing...{Style.RESET_ALL}")
                os.remove(filename)
                logging.info(f"Deleted outdated file: {filename}")
            continue
        
        github_size = github_assets[filename]['size']
        local_size = local_files.get(filename, -1)
        
        if not os.path.exists(filename) or local_size != github_size:
            print(f"{Fore.YELLOW}🔧 File {filename} size mismatch (local={local_size}, github={github_size}). Repairing...{Style.RESET_ALL}")
            if os.path.exists(filename):
                os.remove(filename)
                logging.info(f"Deleted mismatched file: {filename}")
            download_url = github_assets[filename]['browser_download_url']
            size = download_file(download_url, filename, config)
            new_files[filename] = size
            updated = True
            logging.info(f"Repaired {filename}, size={size}")
    
    for local_file in local_files:
        if local_file not in expected_files:
            print(f"{Fore.YELLOW}⚠ Unexpected file {local_file} found locally. Removing...{Style.RESET_ALL}")
            os.remove(local_file)
            del new_files[local_file]
            updated = True
            logging.info(f"Removed unexpected file: {local_file}")

    if updated:
        write_version_file(github_version, github_title, new_files)
        config["last_version_check"] = time.time()
        save_config(config)
        print(f"{Fore.GREEN}✅ Repair completed!{Style.RESET_ALL}")
    else:
        print(f"{Fore.CYAN}📋 Verifying file integrity for version {github_version} (Title: {github_title})...{Style.RESET_ALL}")
        all_valid = True
        for filename in expected_files:
            if filename in local_files and os.path.exists(filename):
                local_size = local_files[filename]
                github_size = github_assets[filename]['size']
                local_hash = compute_file_hash(filename)
                print(f"  {filename}: Size={local_size} bytes, Hash={local_hash}")
                if local_size != github_size:
                    all_valid = False
            else:
                all_valid = False
                print(f"{Fore.RED}❌ Missing or invalid file: {filename}{Style.RESET_ALL}")
        
        if all_valid:
            print(f"{Fore.GREEN}✅ All files are up to date and verified with version {github_version} (Title: {github_title})!{Style.RESET_ALL}")
            logging.info("All files verified and up to date")
        else:
            print(f"{Fore.YELLOW}⚠ Some files may be corrupted. Consider manual update.{Style.RESET_ALL}")
            logging.warning("File integrity check failed")
        
        config["last_version_check"] = time.time()
        save_config(config)

def load_config():
    default_config = {
        "auto_inject": True,
        "inject_wait_time": 15,
        "auto_inject_failed": False,
        "repo_path": "",
        "dll_path": "",
        "last_version_check": 0,
        "use_steam": False,
        "auto_close_after_inject": False,
        "channel": "Stable"
    }
    if os.path.exists("config.json"):
        try:
            with open("config.json", "r") as f:
                config = json.load(f)
                for key in default_config:
                    if key not in config:
                        config[key] = default_config[key]
                return config
        except json.JSONDecodeError:
            print(f"{Fore.RED}❌ Config file is corrupted! Starting with new config.{Style.RESET_ALL}")
            logging.error("Config file corrupted, using default")
            return default_config
        except Exception as e:
            print(f"{Fore.RED}❌ Error loading config: {e}. Starting with new config.{Style.RESET_ALL}")
            logging.error(f"Error loading config: {e}, using default")
            return default_config
    return default_config

def save_config(config):
    try:
        with open("config.json", "w") as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        print(f"{Fore.RED}❌ Error saving config: {e}{Style.RESET_ALL}")
        logging.error(f"Error saving config: {e}")

def is_process_running(process_name):
    possible_names = ["repo", "r.e.p.o", "r.e.p.o."]
    for proc in psutil.process_iter(['name']):
        proc_name = proc.info['name'].lower()
        for name in possible_names:
            if name in proc_name:
                return True
    return False

def wait_for_process(process_name, timeout=30):
    start_time = time.time()
    while time.time() - start_time < timeout:
        if is_process_running(process_name):
            return True
        time.sleep(0.5)
    return False

def start_game(config):
    steam_app_id = "3241660"
    if config["use_steam"]:
        subprocess.Popen(["start", f"steam://rungameid/{steam_app_id}"], shell=True)
        logging.info(f"Starting via Steam with AppID {steam_app_id}")
    else:
        if not config["repo_path"] or not os.path.exists(config["repo_path"]):
            print(f"{Fore.RED}❌ REPO.exe path is invalid or missing!{Style.RESET_ALL}")
            return
        subprocess.Popen(config["repo_path"], cwd=os.path.dirname(config["repo_path"]))
        logging.info(f"Starting directly from {config['repo_path']}")

def get_inject_wait_time(config):
    root = Tk()
    root.withdraw()
    icon_path = setup_icon()
    if icon_path:
        try:
            root.iconbitmap(icon_path)
        except Exception as e:
            print(f"{Fore.YELLOW}⚠ Failed to load icon at {icon_path}: {e}{Style.RESET_ALL}")
    wait_time = simpledialog.askinteger("Inject Wait Time", "Enter wait time before injection (seconds):", minvalue=0, initialvalue=10)
    root.destroy()
    if wait_time is None:
        print(f"{Fore.YELLOW}⚠ No wait time provided! Using default: 10 seconds.{Style.RESET_ALL}")
        return 10
    return wait_time

def is_valid_dll(dll_path):
    try:
        with open(dll_path, 'rb') as f:
            header = f.read(2)
            if header != b'MZ':
                return False
        return os.path.getsize(dll_path) > 0
    except Exception as e:
        logging.error(f"DLL validation failed: {e}")
        return False

def show_inject_success(config):
    dll_name = os.path.basename(config["dll_path"])
    repo_name = "REPO"
    root = Tk()
    root.withdraw()
    icon_path = setup_icon()
    if icon_path:
        try:
            root.iconbitmap(icon_path)
        except Exception as e:
            print(f"{Fore.YELLOW}⚠ Failed to load icon at {icon_path}: {e}{Style.RESET_ALL}")
    messagebox.showinfo("Injection Successful", f"DLL '{dll_name}' has been successfully injected into {repo_name}!")
    root.destroy()
    if config["auto_close_after_inject"]:
        print(f"{Fore.GREEN}✅ Auto closing after successful injection...{Style.RESET_ALL}")
        sys.exit(0)

def show_inject_failure(error_log, config, log_file=None):
    root = Tk()
    root.withdraw()
    icon_path = setup_icon()
    if icon_path:
        try:
            root.iconbitmap(icon_path)
        except Exception as e:
            print(f"{Fore.YELLOW}⚠ Failed to load icon at {icon_path}: {e}{Style.RESET_ALL}")
    message = f"Injection failed!\nError Log: {error_log}\n"
    if log_file:
        message += f"Log saved to: {log_file}\n"
    message += "\nWould you like to try again?"
    retry = messagebox.askretrycancel("Injection Failed", message)
    root.destroy()
    if retry:
        perform_injection(config)

def ensure_log_directory():
    log_dir = "inject-fail-logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    return log_dir

def perform_injection(config):
    dll_name = os.path.basename(config["dll_path"])
    repo_names = ["REPO", "R.E.P.O."]
    
    disclaimer = (
        f"{Fore.YELLOW}⚠ DISCLAIMER: This is just an \"automated\" launcher. Any inject failure issues are due to "
        f"the injector and the injector dll. Completely \"unrelated\" to the launcher. We only take responsibility "
        f"for errors related to our launcher.{Style.RESET_ALL}"
    )
    print(disclaimer)
    
    namespace = NAMESPACE_MAPPING.get(config["channel"], "r.e.p.o_cheat")
    
    print(f"{Fore.YELLOW}💉 Injecting DLL with namespace '{namespace}'...{Style.RESET_ALL}")
    logging.info(f"Starting injection for DLL: {dll_name} with namespace: {namespace}")
    
    for repo_name in repo_names:
        inject_cmd = f'smi.exe inject -p "{repo_name}" -a "{dll_name}" -n {namespace} -c Loader -m Init'
        logging.info(f"Trying injection with command: {inject_cmd}")
        
        result = subprocess.run(inject_cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"{Fore.GREEN}✅ Injection successful with process '{repo_name}'{Style.RESET_ALL}")
            logging.info(f"Injection successful for {dll_name} into {repo_name}")
            return True
        else:
            print(f"{Fore.YELLOW}⚠ Injection failed with process '{repo_name}'. Trying next name...{Style.RESET_ALL}")
            logging.warning(f"Injection failed with {repo_name}: {result.stderr}")
    
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    log_dir = ensure_log_directory()
    log_file = os.path.join(log_dir, f"inject_fail_{timestamp}.log")
    
    with open(log_file, "w") as f:
        f.write(f"Inject Command Attempts:\n")
        for repo_name in repo_names:
            cmd = f'smi.exe inject -p "{repo_name}" -a "{dll_name}" -n {namespace} -c Loader -m Init'
            f.write(f"{cmd}\n")
        f.write(f"Timestamp: {time.ctime()}\n")
        f.write(f"Error Output:\n{result.stderr}\n")
        f.write(f"Standard Output:\n{result.stdout}\n")
    
    print(f"{Fore.RED}❌ Injection failed with all process names! Error log saved to {log_file}{Style.RESET_ALL}")
    show_inject_failure(result.stderr, config, log_file)
    return False

def download_dll(url, config):
    filename = os.path.basename(url) if url.endswith('.dll') else "downloaded.dll"
    print(f"{Fore.CYAN}Downloading DLL from {url}...{Style.RESET_ALL}")
    logging.info(f"Downloading DLL from {url}")
    download_file(url, filename, config)
    if is_valid_dll(filename):
        config["dll_path"] = os.path.abspath(filename)
        save_config(config)
        print(f"{Fore.GREEN}DLL downloaded successfully to {config['dll_path']}!{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}❌ Downloaded DLL is invalid!{Style.RESET_ALL}")

def kill_game():
    for proc in psutil.process_iter(['name']):
        if "REPO" in proc.info['name'].upper():
            proc.kill()
            print(f"{Fore.YELLOW}🔪 Game process terminated.{Style.RESET_ALL}")
            return True
    print(f"{Fore.YELLOW}⚠ No REPO process found to kill. Starting game anyway...{Style.RESET_ALL}")
    return False

usage = {
    "inject": "inject (-i) [time] [--force]: Inject DLL into game, optionally wait [time] seconds.",
    "kill": "kill (-k): Terminate the game process.",
    "restart": "restart (-r) [time]: Restart game, optionally delay by [time] seconds.",
    "auto_inject": "auto_inject (-aj) [True/False] [time]: Toggle or set auto inject.",
    "inject_wait_time": "inject_wait_time (-iwt): Open UI to set inject wait time.",
    "status": "status (-s): Show current configuration and game status.",
    "download_dll": "download_dll (-ddl) <url>: Download a DLL from a URL.",
    "config": "config (-c): Open the configuration GUI to modify settings."
}

def show_usage(command, config):
    cmd = command.split()[0].lower() if command else ""
    if cmd in usage:
        print(f"{Fore.YELLOW}⚠ Usage: {usage[cmd]}{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}❌ Unknown command: {command}. Type 'help' for available commands.{Style.RESET_ALL}")

def handle_commands(command, config):
    commands = re.split(r";|&&", command.strip())
    for cmd in commands:
        cmd = cmd.strip()
        if not cmd:
            continue
        parts = cmd.split()
        action = parts[0].lower()

        if action in ("exit", "quit"):
            print(f"{Fore.YELLOW}⚠ Exiting program...{Style.RESET_ALL}")
            sys.exit(0)

        if action in ("help", "-h"):
            print(f"{Fore.CYAN}Available Commands:{Style.RESET_ALL}")
            for cmd, desc in usage.items():
                print(f"  {cmd}: {desc}")

        elif action in ("inject", "-i"):
            force = "--force" in parts
            if force:
                parts.remove("--force")
            if len(parts) > 2 or (len(parts) == 2 and not parts[1].isdigit()):
                show_usage("inject", config)
            elif config["auto_inject"] and not config.get("auto_inject_failed", False) and not force:
                print(f"{Fore.RED}❌ Cannot use 'inject' while auto_inject is enabled. Disable it or use --force.{Style.RESET_ALL}")
            else:
                repo_name = "REPO"
                wait_time = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
                if not is_process_running(repo_name):
                    print(f"{Fore.YELLOW}🚀 Game not running. Starting REPO.exe...{Style.RESET_ALL}")
                    start_game(config)
                    if not wait_for_process(repo_name):
                        print(f"{Fore.RED}❌ REPO.exe did not start within timeout.{Style.RESET_ALL}")
                        continue
                    print(f"{Fore.GREEN}✅ REPO detected.{Style.RESET_ALL}")
                
                if wait_time > 0:
                    print(f"{Fore.CYAN}⏳ Waiting {wait_time} seconds before injection...{Style.RESET_ALL}")
                    time.sleep(wait_time)
                
                if perform_injection(config):
                    show_inject_success(config)
                    print(f"{Fore.GREEN}🎉 DLL has been successfully injected into {repo_name}!{Style.RESET_ALL}")

        elif action in ("kill", "-k"):
            if len(parts) > 1:
                show_usage("kill", config)
            else:
                kill_game()

        elif action in ("restart", "-r"):
            if len(parts) > 2 or (len(parts) == 2 and not parts[1].isdigit()):
                show_usage("restart", config)
            else:
                repo_name = "REPO"
                delay = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
                
                kill_game()
                
                if delay > 0:
                    print(f"{Fore.CYAN}⏳ Waiting {delay} seconds before restarting...{Style.RESET_ALL}")
                    time.sleep(delay)
                
                print(f"{Fore.YELLOW}🚀 Restarting REPO.exe...{Style.RESET_ALL}")
                start_game(config)
                
                if wait_for_process(repo_name):
                    print(f"{Fore.GREEN}✅ REPO detected.{Style.RESET_ALL}")
                    if config["auto_inject"] and not config.get("auto_inject_failed", False):
                        print(f"{Fore.CYAN}⏳ Waiting {config['inject_wait_time']} seconds before auto injection...{Style.RESET_ALL}")
                        time.sleep(config["inject_wait_time"])
                        if perform_injection(config):
                            show_inject_success(config)
                            print(f"{Fore.GREEN}🎉 DLL has been successfully injected into {repo_name} via auto_inject!{Style.RESET_ALL}")
                        else:
                            config["auto_inject_failed"] = True
                            config["auto_inject"] = False
                            save_config(config)
                            print(f"{Fore.RED}❌ Auto injection failed after restart. Disabled auto_inject.{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}❌ REPO.exe did not start within timeout.{Style.RESET_ALL}")

        elif action in ("auto_inject", "-aj"):
            if len(parts) == 1:
                config["auto_inject"] = not config["auto_inject"]
                print(f"{Fore.GREEN}✅ Auto inject set to {config['auto_inject']}{Style.RESET_ALL}")
            elif len(parts) >= 2 and parts[1].lower() in ("true", "false"):
                value = parts[1].lower() == "true"
                config["auto_inject"] = value
                if len(parts) == 3 and parts[2].isdigit():
                    config["inject_wait_time"] = int(parts[2])
                elif len(parts) > 3:
                    show_usage("auto_inject", config)
                    continue
                print(f"{Fore.GREEN}✅ Auto inject set to {value}, wait time: {config['inject_wait_time']}{Style.RESET_ALL}")
            else:
                show_usage("auto_inject", config)
                continue
            save_config(config)

        elif action in ("inject_wait_time", "-iwt"):
            if len(parts) > 1:
                show_usage("inject_wait_time", config)
            else:
                config["inject_wait_time"] = get_inject_wait_time({})
                save_config(config)
                print(f"{Fore.GREEN}✅ Inject wait time set to {config['inject_wait_time']} seconds{Style.RESET_ALL}")

        elif action in ("status", "-s"):
            print(f"{Fore.CYAN}📊 Current Status:{Style.RESET_ALL}")
            print(f"  Auto Inject: {config['auto_inject']}")
            print(f"  Inject Wait Time: {config['inject_wait_time']} seconds")
            print(f"  DLL Path: {config['dll_path']}")
            print(f"  REPO Path: {config['repo_path']}")
            print(f"  Use Steam: {config['use_steam']}")
            print(f"  Game Running: {is_process_running('REPO')}")
            print(f"  Auto Inject Failed: {config.get('auto_inject_failed', False)}")
            print(f"  Auto Close After Inject: {config['auto_close_after_inject']}")
            print(f"  Channel: {config['channel']}")
            print(f"  Last Version Check: {int(time.time() - config['last_version_check'])}s ago")

        elif action in ("download_dll", "-ddl"):
            if len(parts) != 2:
                show_usage("download_dll", config)
            else:
                download_dll(parts[1], config)

        elif action in ("config", "-c"):
            if len(parts) > 1:
                show_usage("config", config)
            else:
                print(f"{Fore.GREEN}✅ Configuration GUI opened. Changes will be saved upon clicking 'Save'.{Style.RESET_ALL}")
                config_gui(config, standalone=True)

        else:
            show_usage(cmd, config)

def get_windows_wallpaper():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop")
        wallpaper_path, _ = winreg.QueryValueEx(key, "WallPaper")
        if os.path.exists(wallpaper_path):
            return wallpaper_path
        return None
    except Exception as e:
        print(f"{Fore.YELLOW}⚠ Could not retrieve wallpaper: {e}{Style.RESET_ALL}")
        return None

def get_windows_accent_color():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\DWM")
        color, _ = winreg.QueryValueEx(key, "AccentColor")
        b = (color & 0xFF0000) >> 16
        g = (color & 0x00FF00) >> 8
        r = color & 0x0000FF
        return f"#{r:02x}{g:02x}{b:02x}"
    except Exception as e:
        print(f"{Fore.YELLOW}⚠ Could not retrieve accent color: {e}{Style.RESET_ALL}")
        return "#0078D4"

def apply_mica_effect(hwnd):
    dwm = ctypes.windll.dwmapi
    mica_enabled = ctypes.c_int(1)
    dark_mode_enabled = ctypes.c_int(1)
    
    dwm.DwmSetWindowAttribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(dark_mode_enabled), ctypes.sizeof(dark_mode_enabled))
    dwm.DwmSetWindowAttribute(hwnd, DWMWA_MICA_EFFECT, ctypes.byref(mica_enabled), ctypes.sizeof(mica_enabled))

def apply_theme(root, wallpaper_path=None, initial=False):
    try:
        if not root.winfo_exists():
            return
    except tkinter.TclError:
        print(f"{Fore.YELLOW}⚠ Window already destroyed. Skipping theme application.{Style.RESET_ALL}")
        return
    
    style = ttk.Style()
    style.theme_use("darkly")
    
    accent_color = get_windows_accent_color()
    
    style.configure("Accent.TButton", foreground="white", background=accent_color, borderwidth=0)
    style.map("Accent.TButton", 
              background=[('active', f"{accent_color}cc"), ('pressed', f"{accent_color}aa")],
              foreground=[('active', 'white')])
    
    if initial and wallpaper_path:
        try:
            img = Image.open(wallpaper_path)
            img = img.resize((root.winfo_screenwidth(), root.winfo_screenheight()), Image.Resampling.LANCZOS)
            bg_image = ImageTk.PhotoImage(img)
            bg_label = Label(root, image=bg_image)
            bg_label.image = bg_image
            bg_label.place(x=0, y=0, relwidth=1, relheight=1)
            bg_label.lower()
        except Exception as e:
            print(f"{Fore.YELLOW}⚠ Could not load wallpaper: {e}{Style.RESET_ALL}")
    
    try:
        hwnd = win32gui.GetParent(root.winfo_id())
        apply_mica_effect(hwnd)
    except tkinter.TclError:
        print(f"{Fore.YELLOW}⚠ Window destroyed before applying Mica effect.{Style.RESET_ALL}")

def select_file(title, filetypes):
    return filedialog.askopenfilename(title=title, filetypes=filetypes)

def download_stable_injector_files(config):
    stable_channel = "Stable"
    latest_release = get_latest_release(config, channel_override=stable_channel)
    if not latest_release:
        print(f"{Fore.RED}❌ Could not fetch Stable release for injector files. Skipping...{Style.RESET_ALL}")
        return False

    github_assets = {asset['name']: asset for asset in latest_release['assets']}
    injector_files = ["smi.exe", "SharpMonoInjector.dll"]

    success = True
    for filename in injector_files:
        if filename in github_assets:
            download_url = github_assets[filename]['browser_download_url']
            size = download_file(download_url, filename, config)
            if size > 0:
                print(f"{Fore.GREEN}✅ Downloaded {filename} successfully.{Style.RESET_ALL}")
                logging.info(f"Downloaded {filename}, size={size}")
            else:
                print(f"{Fore.RED}❌ Failed to download {filename}.{Style.RESET_ALL}")
                success = False
        else:
            print(f"{Fore.YELLOW}⚠ {filename} not found in Stable release.{Style.RESET_ALL}")
            success = False
    
    return success

def config_gui(config, standalone=False, first_launch=False):
    try:
        root = Tk()
        root.title("Setup Config GUI")
        root.resizable(False, False)
        icon_path = setup_icon()
        if icon_path:
            try:
                root.iconbitmap(icon_path)
            except Exception as e:
                print(f"{Fore.YELLOW}⚠ Failed to load icon at {icon_path}: {e}{Style.RESET_ALL}")

        wallpaper_path = get_windows_wallpaper()
        apply_theme(root, wallpaper_path, initial=True)

        game_label = Label(root, text="Game Path:")
        game_label.grid(row=0, column=0, padx=5, pady=5)
        repo_entry = ttk.Entry(root, width=50)
        repo_entry.grid(row=0, column=1, padx=5, pady=5)
        repo_entry.insert(0, config.get("repo_path", ""))
        browse_button = ttk.Button(root, text="Browse", command=lambda: [repo_entry.configure(state="normal"), repo_entry.delete(0, END), repo_entry.insert(0, select_file("Select REPO.exe", [("Executable files", "*.exe")])), config.update({"use_steam": False})], style="Outline.TButton")
        browse_button.grid(row=0, column=2, padx=5, pady=5)

        def toggle_game_source():
            if config["use_steam"]:
                repo_entry.configure(state="normal")
                browse_button.grid()
                steam_local_button.config(text="Steam Game")
                config["use_steam"] = False
                repo_entry.delete(0, END)
                repo_entry.insert(0, config.get("repo_path", ""))
            else:
                repo_entry.delete(0, END)
                repo_entry.insert(0, "Start with Steam")
                repo_entry.configure(state="disabled")
                browse_button.grid_remove()
                steam_local_button.config(text="Local Game")
                config["use_steam"] = True

        steam_local_button = ttk.Button(root, text="Steam Game" if not config["use_steam"] else "Local Game", command=toggle_game_source, style="Outline.TButton")
        steam_local_button.grid(row=0, column=3, padx=5, pady=5)

        if config["use_steam"]:
            repo_entry.delete(0, END)
            repo_entry.insert(0, "Start with Steam")
            repo_entry.configure(state="disabled")
            browse_button.grid_remove()

        Label(root, text="DLL Path:").grid(row=1, column=0, padx=5, pady=5)
        dll_entry = ttk.Entry(root, width=50)
        dll_entry.grid(row=1, column=1, padx=5, pady=5)
        default_dll = os.path.abspath("r.e.p.o.cheat.dll")
        if os.path.exists(default_dll) and is_valid_dll(default_dll):
            dll_entry.insert(0, default_dll)
        else:
            dll_entry.insert(0, config.get("dll_path", ""))
        ttk.Button(root, text="Browse", command=lambda: [dll_entry.delete(0, END), dll_entry.insert(0, select_file("Select DLL file", [("DLL files", "*.dll")]))], style="Outline.TButton").grid(row=1, column=2, padx=5, pady=5)

        auto_inject_var = ttk.BooleanVar(value=config["auto_inject"])
        Checkbutton(root, text="Auto Inject", variable=auto_inject_var).grid(row=2, column=0, columnspan=2, pady=5)

        Label(root, text="Inject Wait Time (seconds):").grid(row=3, column=0, padx=5, pady=5)
        wait_time_entry = ttk.Entry(root, width=10)
        wait_time_entry.grid(row=3, column=1, padx=5, pady=5, sticky="w")
        wait_time_entry.insert(0, config["inject_wait_time"])

        auto_close_var = ttk.BooleanVar(value=config["auto_close_after_inject"])
        Checkbutton(root, text="Auto Close After Inject", variable=auto_close_var).grid(row=4, column=0, columnspan=2, pady=5)
        
        Label(root, text="Release Channel:").grid(row=5, column=0, padx=5, pady=5)
        channel_var = ttk.StringVar(value=config.get("channel", "Stable"))
        channel_combo = ttk.Combobox(root, textvariable=channel_var, values=["Stable", "Beta"], state="readonly", width=10)
        channel_combo.grid(row=5, column=1, padx=5, pady=5, sticky="w")

        def save_config_and_close():
            new_repo_path = repo_entry.get() if not config["use_steam"] else ""
            new_dll_path = dll_entry.get()
            if not first_launch and (not new_dll_path or not os.path.exists(new_dll_path) or not is_valid_dll(new_dll_path)):
                messagebox.showerror("Error", "Invalid or missing DLL path!")
                return
            if not config["use_steam"] and (not new_repo_path or not os.path.exists(new_repo_path)):
                messagebox.showerror("Error", "Invalid or missing REPO path!")
                return
            config["repo_path"] = new_repo_path
            config["dll_path"] = new_dll_path if not first_launch else ""
            config["auto_inject"] = auto_inject_var.get()
            config["inject_wait_time"] = int(wait_time_entry.get()) if wait_time_entry.get().isdigit() else 10
            config["auto_close_after_inject"] = auto_close_var.get()
            config["channel"] = channel_var.get()
            save_config(config)
            root.destroy()

        if standalone:
            ttk.Button(root, text="Save", command=save_config_and_close, style="Accent.TButton").grid(row=6, column=0, columnspan=4, pady=10)
        else:
            ttk.Button(root, text="Save & Start", command=save_config_and_close, style="Accent.TButton").grid(row=6, column=0, columnspan=4, pady=10)

        root.protocol("WM_DELETE_WINDOW", lambda: root.destroy() if standalone else sys.exit(1))
        root.mainloop()
        return config
    except Exception as e:
        print(f"{Fore.RED}❌ Error in config_gui: {e}{Style.RESET_ALL}")
        logging.error(f"Error in config_gui: {e}", exc_info=True)
        return config

def handle_commands_loop(config):
    print(f"{Fore.YELLOW}⚙ Enter commands below (type 'help' for list, 'exit' to quit):{Style.RESET_ALL}")
    while True:
        try:
            if not is_process_running("REPO"):
                print(f"{Fore.RED}❌ Game (REPO) has exited.{Style.RESET_ALL}")
            command = input("> ")
            handle_commands(command, config)
        except EOFError:
            print(f"{Fore.YELLOW}⚠ Console input closed. Exiting command loop...{Style.RESET_ALL}")
            break
        except Exception as e:
            print(f"{Fore.RED}❌ Error in command loop: {e}{Style.RESET_ALL}")
            break

def run_launcher(config):
    setup_logging()
    set_app_user_model_id()
    print()
    print(f"{Fore.CYAN}📢 D.A.R.K Launcher become open source. Check out: {Fore.RESET}https://github.com/sang765/DARK-Launcher-Open")
    print()
    print(f"{Fore.RED}Вы, должно быть, в отчаянии, раз пришли ко мне.{Style.RESET_ALL}")
    print(f"{Fore.BLUE}Launcher made by SengsDeyy{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Leave our project with a star: https://github.com/D4rkks/r.e.p.o-cheat{Style.RESET_ALL}")
    logging.info("Launcher started")

    if not is_admin():
        print(f"{Fore.YELLOW}⚠ Running without admin privileges. Attempting to elevate...{Style.RESET_ALL}")
        run_as_admin()
        return

    config = load_config()
    check_and_update(config)
    ensure_log_directory()

def main():
    try:
        config = load_config()
        setup_logging()
        set_app_user_model_id()

        if NO_CONSOLE_MODE:
            if not config["auto_inject"]:
                logging.error("Cannot run --no-console without auto_inject enabled")
                sys.exit(1)
            if os.name == 'nt':
                ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

        if not NO_CONSOLE_MODE:
            print()
            print(f"{Fore.CYAN}📢 D.A.R.K Launcher become open source. Check out: {Fore.RESET}https://github.com/sang765/DARK-Launcher-Open")
            print()
            print(f"{Fore.YELLOW}Stable Channel: https://github.com/D4rkks/r.e.p.o-cheat{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Beta Channel: https://github.com/peeberpoober/beta-r.e.p.o-cheat{Style.RESET_ALL}")
            print()
            print(f"{Fore.RED}Вы, должно быть, в отчаянии, раз пришли ко мне.{Style.RESET_ALL}")
            print(f"{Fore.BLUE}Launcher made by SengsDeyy{Style.RESET_ALL}")
        logging.info("Launcher started")

        if NO_INJECT_MODE:
            print(f"{Fore.CYAN}🔧 Starting in --no-inject mode. No game injection will occur.{Style.RESET_ALL}")
            return

        if not is_admin():
            if not NO_CONSOLE_MODE:
                print(f"{Fore.YELLOW}⚠ Running without admin privileges. Attempting to elevate...{Style.RESET_ALL}")
            run_as_admin()
            return

        first_launch = not os.path.exists("config.json")
        if first_launch:
            if not NO_CONSOLE_MODE:
                print(f"{Fore.YELLOW}⚠ First launch detected. Downloading injector files from Stable channel...{Style.RESET_ALL}")
            download_stable_injector_files(config)
            if not NO_CONSOLE_MODE:
                print(f"{Fore.YELLOW}⚠ Opening configuration GUI to select channel...{Style.RESET_ALL}")
            config = config_gui(config, first_launch=True)
            save_config(config)
            if not NO_CONSOLE_MODE:
                print(f"{Fore.GREEN}✅ Configuration saved. Downloading DLL based on selected channel...{Style.RESET_ALL}")
            check_and_update(config)
        else:
            config = load_config()
            check_and_update(config)

        ensure_log_directory()

        if first_launch and (not config["dll_path"] or not os.path.exists(config["dll_path"])):
            default_dll = os.path.abspath("r.e.p.o.cheat.dll" if config["channel"] == "Stable" else "dark_cheat.dll")
            if os.path.exists(default_dll) and is_valid_dll(default_dll):
                config["dll_path"] = default_dll
                save_config(config)
                if not NO_CONSOLE_MODE:
                    print(f"{Fore.GREEN}✅ DLL '{default_dll}' automatically selected and saved to config.{Style.RESET_ALL}")
            else:
                if not NO_CONSOLE_MODE:
                    print(f"{Fore.RED}❌ DLL '{default_dll}' not found after update. Please configure manually.{Style.RESET_ALL}")

        while True:
            if not config["dll_path"] or not os.path.exists(config["dll_path"]) or \
               (not config["use_steam"] and (not config["repo_path"] or not os.path.exists(config["repo_path"]))):
                if not NO_CONSOLE_MODE:
                    print(f"{Fore.YELLOW}⚠ Configuration is incomplete or invalid. Please configure again.{Style.RESET_ALL}")
                config = config_gui(config, first_launch=False)
                if not config["dll_path"] or (not config["use_steam"] and not config["repo_path"]):
                    response = messagebox.askyesno("Configuration Required", "DLL path or Game path (if not using Steam) is still missing. Retry configuration?")
                    if not response:
                        if not NO_CONSOLE_MODE:
                            print(f"{Fore.RED}❌ Configuration incomplete. Exiting...{Style.RESET_ALL}")
                        sys.exit(1)
                elif not is_valid_dll(config["dll_path"]):
                    if not NO_CONSOLE_MODE:
                        print(f"{Fore.RED}❌ Selected DLL is invalid or corrupted!{Style.RESET_ALL}")
                    config["dll_path"] = ""
            else:
                break

        repo_name = "REPO"
        game_already_running = is_process_running(repo_name)

        if not game_already_running:
            if not NO_CONSOLE_MODE:
                print(f"{Fore.YELLOW}🚀 Game not running. Starting REPO.exe...{Style.RESET_ALL}")
            start_game(config)
            if wait_for_process(repo_name):
                if not NO_CONSOLE_MODE:
                    print(f"{Fore.GREEN}✅ REPO detected.{Style.RESET_ALL}")
                if config["auto_inject"]:
                    if not NO_CONSOLE_MODE:
                        print(f"{Fore.GREEN}✅ REPO started, waiting {config['inject_wait_time']} seconds before injection...{Style.RESET_ALL}")
                    time.sleep(config["inject_wait_time"])
                    if perform_injection(config):
                        if not NO_CONSOLE_MODE:
                            show_inject_success(config)
                            print(f"{Fore.GREEN}🎉 DLL has been successfully injected via auto_inject!{Style.RESET_ALL}")
                        if NO_CONSOLE_MODE or config["auto_close_after_inject"]:
                            sys.exit(0)
                    else:
                        config["auto_inject_failed"] = True
                        config["auto_inject"] = False
                        save_config(config)
                        if not NO_CONSOLE_MODE:
                            print(f"{Fore.RED}❌ Auto injection failed. Disabled auto_inject.{Style.RESET_ALL}")
            else:
                if not NO_CONSOLE_MODE:
                    print(f"{Fore.RED}❌ REPO.exe did not start within timeout.{Style.RESET_ALL}")
        else:
            if not NO_CONSOLE_MODE:
                print(f"{Fore.GREEN}✅ REPO or R.E.P.O. is already running.{Style.RESET_ALL}")
            if config["auto_inject"]:
                if not NO_CONSOLE_MODE:
                    print(f"{Fore.GREEN}✅ Game already running, injecting immediately...{Style.RESET_ALL}")
                if perform_injection(config):
                    if not NO_CONSOLE_MODE:
                        show_inject_success(config)
                        print(f"{Fore.GREEN}🎉 DLL has been successfully injected via auto_inject!{Style.RESET_ALL}")
                    if NO_CONSOLE_MODE or config["auto_close_after_inject"]:
                        sys.exit(0)
                else:
                    config["auto_inject_failed"] = True
                    config["auto_inject"] = False
                    save_config(config)
                    if not NO_CONSOLE_MODE:
                        print(f"{Fore.RED}❌ Auto injection failed. Disabled auto_inject.{Style.RESET_ALL}")

        if not NO_CONSOLE_MODE:
            handle_commands_loop(config)

    except KeyboardInterrupt:
        print(f"{Fore.YELLOW}⚠ Program interrupted by user.{Style.RESET_ALL}")
        sys.exit(0)
    except Exception as e:
        if not NO_CONSOLE_MODE:
            print(f"{Fore.RED}❌ Fatal error occurred: {str(e)}{Style.RESET_ALL}")
        logging.error(f"Fatal error in main: {str(e)}", exc_info=True)
        if not NO_CONSOLE_MODE:
            input("Press Enter to exit...")
        sys.exit(1)
    finally:
        if not NO_CONSOLE_MODE:
            print(f"{Fore.YELLOW}⚠ Program finished.{Style.RESET_ALL}")
        logging.shutdown()
        try:
            subprocess.run(['taskkill', '/F', '/IM', 'D.A.R.K Launcher.exe'], check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception as e:
            if not NO_CONSOLE_MODE:
                print(f"{Fore.YELLOW}⚠ Could not kill process: {e}{Style.RESET_ALL}")
        sys.exit(0)

if __name__ == "__main__":
    main()