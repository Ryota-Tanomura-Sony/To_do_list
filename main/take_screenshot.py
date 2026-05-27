#!/usr/bin/env python3
"""
Screenshot using direct subprocess command
"""
import subprocess
import time
import os

chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
output_file = r"C:\Users\0107409306\Documents\To_do_list.worktrees\copilot-update-readme-from-main-dir\main\debug_chrome.png"

# Kill any existing Chrome processes that might interfere
os.system("taskkill /F /IM chrome.exe 2>nul")
time.sleep(2)

# Launch Chrome with debugging port
print("[DEBUG] Launching Chrome with debugging capabilities...")
proc = subprocess.Popen([
    chrome_path,
    "--new-window",
    "http://localhost:5007/To_do",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    f"--screenshot={output_file}",
], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

print("[DEBUG] Chrome launched with PID:", proc.pid)
print("[DEBUG] Waiting for screenshot to be captured...")

# Wait for Chrome to capture the screenshot
time.sleep(8)

# Try to gracefully close Chrome
try:
    proc.terminate()
    proc.wait(timeout=5)
except:
    os.system(f"taskkill /F /PID {proc.pid} 2>nul")

time.sleep(2)

# Check if screenshot was created
if os.path.exists(output_file):
    size = os.path.getsize(output_file)
    print(f"[SUCCESS] Screenshot saved: {output_file} ({size} bytes)")
else:
    print(f"[WARNING] Screenshot file not found: {output_file}")
    # Try alternative method: use Chrome's headless mode
    print("[DEBUG] Trying headless screenshot...")
    
    proc2 = subprocess.Popen([
        chrome_path,
        "--headless",
        "--disable-gpu",
        f"--screenshot={output_file}",
        "http://localhost:5007/To_do",
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    print("[DEBUG] Chrome headless launched with PID:", proc2.pid)
    time.sleep(10)
    
    try:
        proc2.terminate()
        proc2.wait(timeout=5)
    except:
        os.system(f"taskkill /F /PID {proc2.pid} 2>nul")
    
    time.sleep(2)
    if os.path.exists(output_file):
        size = os.path.getsize(output_file)
        print(f"[SUCCESS] Headless screenshot saved: {output_file} ({size} bytes)")
    else:
        print(f"[ERROR] Screenshot still not found")

print("[DEBUG] Done.")
