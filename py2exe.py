import os
import shutil
import subprocess
import sys
from datetime import datetime
import hashlib
import requests
import json
import pyperclip
import time
import re
import logging
from colorama import Fore, init
from dotenv import load_dotenv
import argparse

init(autoreset=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger()

load_dotenv()

CONFIG = {
    "upload_url": os.getenv("UPLOAD_URL"),
    "upload_token": os.getenv("UPLOAD_TOKEN"),
    "signtool_path": os.getenv("SIGNTOOL_PATH"),
    "cert_file": os.getenv("CERT_FILE"),
    "cert_password": os.getenv("CERT_PASSWORD"),
    "dist_path": os.getenv("DIST_PATH", "dist"),
    "backup_path": os.getenv("BACKUP_PATH", "backup"),
    "exe_name": os.getenv("EXE_NAME", "D.A.R.K Launcher.exe"),
    "max_backups": int(os.getenv("MAX_BACKUPS", 10))
}

def check_config_requirements():
    required = ["upload_url", "upload_token", "signtool_path", "cert_file", "cert_password"]
    missing = [key for key in required if CONFIG[key] is None]
    return missing

def calculate_file_hashes(file_path):
    try:
        hash_md5 = hashlib.md5()
        hash_sha1 = hashlib.sha1()
        hash_sha256 = hashlib.sha256()
        
        with open(file_path, "rb") as f:
            while chunk := f.read(4096):
                hash_md5.update(chunk)
                hash_sha1.update(chunk)
                hash_sha256.update(chunk)
        
        return {
            'MD5': hash_md5.hexdigest(),
            'SHA-1': hash_sha1.hexdigest(),
            'SHA-256': hash_sha256.hexdigest()
        }
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        return None

def get_file_size(file_path):
    try:
        size_bytes = os.path.getsize(file_path)
        size_mb = size_bytes / (1024 * 1024)
        return f"{size_mb:.2f}"
    except OSError as e:
        logger.error(f"Error getting file size for {file_path}: {e}")
        return "0.00"

def manage_backup_limit(backup_path, max_backups):
    try:
        backup_files = [f for f in os.listdir(backup_path) if f.endswith('.bak')]
        backup_files.sort(key=lambda x: os.path.getmtime(os.path.join(backup_path, x)))
        
        while len(backup_files) >= max_backups:
            oldest_file = backup_files.pop(0)
            file_path = os.path.join(backup_path, oldest_file)
            logger.warning(f"Removing oldest backup: {file_path}")
            os.remove(file_path)
    except OSError as e:
        logger.error(f"Error managing backups in {backup_path}: {e}")

def upload_to_donarev419(file_path, skip_on_error=False):
    if not CONFIG["upload_url"] or not CONFIG["upload_token"]:
        logger.warning("Missing upload configuration. Skipping upload step.")
        return None, None
    
    url = CONFIG["upload_url"]
    headers = {"Authorization": CONFIG["upload_token"]}
    
    try:
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f)}
            logger.info(f"Uploading {file_path} to donarev419.com...")
            response = requests.post(url, headers=headers, files=files, timeout=30)
        
        if response.status_code == 200:
            response_data = response.json()
            download_url = response_data.get("url")
            upload_timestamp = int(time.time())
            if download_url:
                logger.info(f"Upload successful! URL: {download_url}")
                return download_url, upload_timestamp
            logger.warning("Upload succeeded but no URL found in response!")
            return None, None
        logger.error(f"Upload failed: {response.status_code} - {response.text}")
        return None, None if skip_on_error else sys.exit(1)
    except requests.RequestException as e:
        logger.error(f"Upload error: {e}")
        return None, None if skip_on_error else sys.exit(1)

def update_release_md(hashes, download_url, timestamp, file_size):
    release_md_path = "Release.md"
    if not os.path.exists(release_md_path):
        logger.error(f"{release_md_path} does not exist!")
        return
    
    try:
        with open(release_md_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        hash_keys = {'MD5': hashes['MD5'], 'SHA-1': hashes['SHA-1'], 'SHA-256': hashes['SHA-256']}
        discord_timestamp = f"<t:{timestamp}>"
        new_download_line = f"> - ⬇️ **[Download](<{download_url}>)**"

        for key, value in hash_keys.items():
            content = re.sub(rf"> - {key}: \*\*\w+\*\*", f"> - {key}: **{value}**", content)

        content = re.sub(r"> - 🆙 Last update: \*\*<t:\d+>\*\*", f"> - 🆙 Last update: **{discord_timestamp}**", content)
        content = re.sub(r"> - 📦 Size: \*\*\d+\.\d+ MB\*\*", f"> - 📦 Size: **{file_size} MB**", content)
        content = re.sub(r"> - ⬇️ \*\*\[Download\]\(<[^>]+>\)\*\*", new_download_line, content)  # Chỉ thay link download chính

        with open(release_md_path, "w", encoding="utf-8") as f:
            f.write(content)
        pyperclip.copy(content)
        logger.info(f"Updated {release_md_path} and copied to clipboard!")
    except Exception as e:
        logger.error(f"Error updating {release_md_path}: {e}")

def backup_and_build(max_backups=None, skip_steps=None):
    skip_steps = skip_steps or {}
    max_backups = max_backups or CONFIG["max_backups"]
    dist_path, backup_path, exe_name = CONFIG["dist_path"], CONFIG["backup_path"], CONFIG["exe_name"]
    source_exe = os.path.join(dist_path, exe_name)

    missing_configs = check_config_requirements()
    if missing_configs:
        logger.warning(f"Missing required configurations: {', '.join(missing_configs)}")

    if not skip_steps.get("backup"):
        if not os.path.exists(backup_path):
            os.makedirs(backup_path)
        
        if os.path.exists(source_exe):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"{exe_name}_{timestamp}.bak"
            shutil.move(source_exe, os.path.join(backup_path, backup_file))
            manage_backup_limit(backup_path, max_backups)
    
    if not skip_steps.get("build"):
        if not os.path.exists("main.py"):
            logger.error("main.py not found!")
            return
        
        pyinstaller_cmd = [
            "pyinstaller",
            "--onefile",              
            "--console",             
            "--uac-admin",  
            "--version-file", "version.txt",         
            "--add-data", "manifest.xml;.",  
            "--add-data", "icon.ico;.",      
            "-n", "D.A.R.K Launcher",        
            "--icon", "icon.ico",            
            "main.py"                        
        ]
        
        logger.info("Building new EXE...")
        if subprocess.run(pyinstaller_cmd, shell=True).returncode != 0:
            logger.error("PyInstaller failed!")
            if skip_steps.get("build_on_error"):
                logger.info("Skipping build step due to error.")
            else:
                return
    
    if not skip_steps.get("sign") and not any(k in missing_configs for k in ["signtool_path", "cert_file", "cert_password"]):
        signtool_cmd = [
            CONFIG["signtool_path"], "sign", "/f", CONFIG["cert_file"],
            "/p", CONFIG["cert_password"], "/fd", "sha256",
            "/tr", "http://timestamp.digicert.com", "/td", "sha256",
            source_exe
        ]
        
        logger.info(f"Signing EXE at {source_exe}...")
        if subprocess.run(signtool_cmd, shell=True).returncode == 0:
            hashes = calculate_file_hashes(source_exe)
            if hashes:
                file_size = get_file_size(source_exe)
                if not skip_steps.get("upload"):
                    download_url, upload_timestamp = upload_to_donarev419(source_exe, skip_on_error=True)
                    if download_url and upload_timestamp:
                        update_release_md(hashes, download_url, upload_timestamp, file_size)
                    else:
                        logger.info("Upload skipped or failed, proceeding without updating Release.md.")
        else:
            logger.error("Failed to sign the EXE!")
            if skip_steps.get("sign_on_error"):
                logger.info("Skipping sign step due to error.")
            else:
                return

def parse_arguments():
    parser = argparse.ArgumentParser(description="Build and release script with step skipping.")
    parser.add_argument("--skip-backup", action="store_true", help="Skip the backup step")
    parser.add_argument("--skip-build", action="store_true", help="Skip the build step")
    parser.add_argument("--skip-sign", action="store_true", help="Skip the sign step")
    parser.add_argument("--skip-upload", action="store_true", help="Skip the upload step")
    parser.add_argument("--skip-on-error", action="store_true", help="Skip steps on error instead of exiting")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_arguments()
    skip_steps = {
        "backup": args.skip_backup,
        "build": args.skip_build,
        "sign": args.skip_sign,
        "upload": args.skip_upload,
        "build_on_error": args.skip_on_error,
        "sign_on_error": args.skip_on_error
    }
    backup_and_build(max_backups=10, skip_steps=skip_steps)