import os
import shutil
import subprocess
from datetime import datetime
import hashlib
import requests
import json
import pyperclip
import time
import re

def calculate_file_hashes(file_path):
    hash_md5 = hashlib.md5()
    hash_sha1 = hashlib.sha1()
    hash_sha256 = hashlib.sha256()
    
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
            hash_sha1.update(chunk)
            hash_sha256.update(chunk)
    
    return {
        'MD5': hash_md5.hexdigest(),
        'SHA-1': hash_sha1.hexdigest(),
        'SHA-256': hash_sha256.hexdigest()
    }

def get_file_size(file_path):
    size_bytes = os.path.getsize(file_path)
    size_mb = size_bytes / (1024 * 1024)
    return f"{size_mb:.2f}"

def manage_backup_limit(backup_path, max_backups=5):
    backup_files = [f for f in os.listdir(backup_path) if f.endswith('.bak')]
    backup_files.sort(key=lambda x: os.path.getmtime(os.path.join(backup_path, x)))
    
    while len(backup_files) >= max_backups:
        oldest_file = backup_files.pop(0)
        file_path = os.path.join(backup_path, oldest_file)
        print(f"Removing oldest backup: {file_path}")
        os.remove(file_path)

def upload_to_donarev419(file_path):
    url = "https://donarev419.com/api/files/sharex/new"
    headers = {
    "Authorization": os.getenv("DONAREV419_API_KEY", "") # go to donarev419.com to create account and get API key
    }
    files = {
        "file": (os.path.basename(file_path), open(file_path, "rb"))
    }
    
    print(f"Uploading {file_path} to donarev419.com...")
    response = requests.post(url, headers=headers, files=files)
    
    if response.status_code == 200:
        try:
            response_data = response.json()
            download_url = response_data.get("url")
            if download_url:
                upload_timestamp = int(time.time())
                print(f"Upload successful! Download URL: {download_url}")
                print(f"Upload timestamp: {upload_timestamp}")
                return download_url, upload_timestamp
            else:
                print("Upload succeeded but no URL found in response!")
                print(f"Response: {response.text}")
                return None, None
        except json.JSONDecodeError:
            print("Failed to parse JSON response!")
            print(f"Response: {response.text}")
            return None, None
    else:
        print(f"Upload failed with status code: {response.status_code}")
        print(f"Error message: {response.text}")
        return None, None

def update_release_md(hashes, download_url, timestamp, file_size):
    release_md_path = "Release.md"
    abs_release_md_path = os.path.abspath(release_md_path)
    
    if not os.path.exists(release_md_path):
        print(f"Error: {abs_release_md_path} does not exist! Please check the file path.")
        return
    
    try:
        with open(release_md_path, "r", encoding="utf-8") as f:
            content = f.readlines()
    except Exception as e:
        print(f"Error reading {abs_release_md_path}: {e}")
        return
    
    print("Original content:")
    print("".join(content))
    
    updated_content = []
    hash_keys = {'MD5': hashes['MD5'], 'SHA-1': hashes['SHA-1'], 'SHA-256': hashes['SHA-256']}
    discord_timestamp = f"<t:{timestamp}>"
    new_update_line = f"> - 🆙 Last update: **{discord_timestamp}**\n"
    new_size_line = f"> - 📦 Size: **{file_size} MB**\n"
    new_download_line = f"> - ⬇️ **[Download](<{download_url}>)**\n"

    for line in content:
        matched = False
        for key, value in hash_keys.items():
            if re.search(rf"> - {key}: \*\*\w+\*\*", line.strip()):
                line = f"> - {key}: **{value}**\n"
                print(f"Matched and updated hash line: {line.strip()}")
                matched = True
        
        if re.search(r"> - 🆙 Last update: \*\*<t:\d+>\*\*", line.strip()):
            line = new_update_line
            print(f"Matched and updated update line: {line.strip()}")
            matched = True
        elif re.search(r"> - 📦 Size: \*\*\d+\.\d+ MB\*\*", line.strip()):
            line = new_size_line
            print(f"Matched and updated size line: {line.strip()}")
            matched = True
        elif re.search(r"> - ⬇️ \*\*\[Download\]\(<[^>]+>\)\*\*", line.strip()):
            line = new_download_line
            print(f"Matched and updated download line: {line.strip()}")
            matched = True
        
        if not matched:
            print(f"No match for line: {line.strip()}")
        updated_content.append(line)
    
    final_content = "".join(updated_content)
    print("Updated content:")
    print(final_content)
    
    try:
        with open(release_md_path, "w", encoding="utf-8") as f:
            f.write(final_content)
        print(f"Successfully updated {abs_release_md_path} with new hashes, timestamp, file size, and download link.")
    except Exception as e:
        print(f"Failed to write to {abs_release_md_path}: {e}")
        print("Check if the file is open elsewhere or if you have write permissions.")
        return
    
    pyperclip.copy(final_content)
    print(f"Copied the entire content of {abs_release_md_path} to clipboard!")

def backup_and_build(max_backups=5):
    dist_path = "dist"
    backup_path = "backup"
    exe_name = "D.A.R.K Launcher.exe"
    source_exe = os.path.join(dist_path, exe_name)
    
    if not os.path.exists(backup_path):
        os.makedirs(backup_path)
    
    if os.path.exists(source_exe):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"{exe_name}_{timestamp}.bak"
        backup_dest = os.path.join(backup_path, backup_file)
        
        print(f"Backing up old EXE to {backup_dest}")
        shutil.move(source_exe, backup_dest)
        manage_backup_limit(backup_path, max_backups)
    
    pyinstaller_cmd = [
        "pyinstaller",
        "--onefile",
        "--console",
        "--uac-admin",
        "--add-data", "icon.ico;.",
        "-n", "D.A.R.K Launcher",
        "--icon=icon.ico",
        "main.py"
    ]
    
    print("Building new EXE...")
    result = subprocess.run(pyinstaller_cmd, shell=True)
    if result.returncode != 0:
        print("PyInstaller failed!")
        return
    
    signtool_path = os.getenv("SIGNTOOL_PATH", "signtool.exe")
    cert_file = "certificate.pfx"
    cert_password = os.getenv("CERT_PASSWORD")
    exe_path = os.path.join(dist_path, exe_name)
    
    signing_skipped = False
    if not os.path.exists(cert_file):
        print(f"Certificate file '{cert_file}' not found. Skipping signing step...")
        signing_skipped = True
    else:
        signtool_cmd = [
            signtool_path,
            "sign",
            "/f", cert_file,
            "/p", cert_password,
            "/fd", "sha256",
            "/tr", "http://timestamp.digicert.com",
            "/td", "sha256",
            exe_path
        ]
        
        print(f"Signing EXE at {exe_path}...")
        result = subprocess.run(signtool_cmd, shell=True)
        if result.returncode == 0:
            print("Successfully signed the EXE!")
        else:
            print("Failed to sign the EXE! Proceeding without signing...")
            signing_skipped = True
    
    if os.path.exists(exe_path):
        print("\nFile Hash Values:")
        hashes = calculate_file_hashes(exe_path)
        for hash_type, hash_value in hashes.items():
            print(f"{hash_type}: **{hash_value}**")
        
        file_size = get_file_size(exe_path)
        print(f"File Size: {file_size} MB")
        
        download_url, upload_timestamp = upload_to_donarev419(exe_path)
        
        if download_url and upload_timestamp:
            update_release_md(hashes, download_url, upload_timestamp, file_size)
        else:
            print("Failed to get download URL or timestamp from upload!")
    else:
        print("Error: Could not find EXE file for hash calculation!")

if __name__ == "__main__":
    backup_and_build(max_backups=10)