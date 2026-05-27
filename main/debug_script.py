# Debug script for To_do.py using Selenium
import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

print("[DEBUG] Starting Selenium debug script...")

# Initialize Chrome driver
options = webdriver.ChromeOptions()
# options.add_argument('--headless')  # Run in headless mode
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-web-resources')

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

try:
    # Navigate to the app
    print("[DEBUG] Navigating to http://localhost:5007/To_do")
    driver.get("http://localhost:5007/To_do")
    
    # Wait for page to load
    print("[DEBUG] Waiting 5 seconds for page to fully load...")
    time.sleep(5)
    
    # Get rendered DOM
    print("\n[1] Page content (DOM):")
    page_content = driver.page_source
    print(f"    Content length: {len(page_content)} chars")
    print(f"    First 1000 chars:\n{page_content[:1000]}")
    
    # Get sidebar info
    print("\n[2] Sidebar info:")
    try:
        sidebar = driver.find_element(By.ID, "sidebar")
        if sidebar:
            print(f"    Sidebar found: {sidebar.tag_name}")
            location = sidebar.location
            size = sidebar.size
            print(f"    Bounding rect: x={location['x']}, y={location['y']}, width={size['width']}, height={size['height']}")
            
            # Get computed styles
            computed_style = driver.execute_script(
                "const elem = document.querySelector('#sidebar'); "
                "const style = window.getComputedStyle(elem); "
                "return { "
                "  color: style.color, "
                "  backgroundColor: style.backgroundColor, "
                "  visibility: style.visibility, "
                "  display: style.display, "
                "  opacity: style.opacity, "
                "  width: style.width, "
                "  height: style.height "
                "};"
            )
            print(f"    Computed styles: {json.dumps(computed_style, indent=6)}")
    except Exception as e:
        print(f"    Sidebar not found or error: {e}")
    
    # Get main area (first .bk-root)
    print("\n[3] Main area (.bk-root) info:")
    try:
        main_areas = driver.find_elements(By.CLASS_NAME, "bk-root")
        if main_areas:
            print(f"    Found {len(main_areas)} .bk-root elements")
            for i, area in enumerate(main_areas[:3]):
                location = area.location
                size = area.size
                print(f"    [{i}] bk-root: x={location['x']}, y={location['y']}, width={size['width']}, height={size['height']}")
                
                if i == 0:
                    computed_style = driver.execute_script(
                        "const elem = document.querySelectorAll('.bk-root')[0]; "
                        "const style = window.getComputedStyle(elem); "
                        "return { "
                        "  display: style.display, "
                        "  visibility: style.visibility, "
                        "  opacity: style.opacity, "
                        "  width: style.width, "
                        "  height: style.height, "
                        "  backgroundColor: style.backgroundColor "
                        "};"
                    )
                    print(f"        Computed styles: {json.dumps(computed_style, indent=8)}")
    except Exception as e:
        print(f"    Error getting .bk-root: {e}")
    
    # Get console messages
    print("\n[4] Console logs:")
    console_logs = driver.get_log('browser')
    if console_logs:
        for log in console_logs[:10]:
            print(f"    [{log['level']}] {log['message'][:200]}")
    else:
        print("    No console logs captured")
    
    # Get page title and other metadata
    print("\n[5] Page metadata:")
    print(f"    Title: {driver.title}")
    print(f"    Current URL: {driver.current_url}")
    
    # Check for visible widgets
    print("\n[6] Widget count:")
    try:
        buttons = driver.find_elements(By.TAG_NAME, "button")
        inputs = driver.find_elements(By.TAG_NAME, "input")
        selects = driver.find_elements(By.TAG_NAME, "select")
        print(f"    Buttons: {len(buttons)}")
        print(f"    Inputs: {len(inputs)}")
        print(f"    Selects: {len(selects)}")
    except Exception as e:
        print(f"    Error counting widgets: {e}")
    
    # Check header/sidebar visibility
    print("\n[7] Visibility check:")
    try:
        header = driver.find_element(By.TAG_NAME, "header")
        print(f"    Header found and visible")
    except:
        print(f"    Header not found")
    
    # Take screenshot
    screenshot_path = r"C:\Users\0107409306\Documents\To_do_list.worktrees\copilot-update-readme-from-main-dir\main\debug.png"
    print(f"\n[8] Taking screenshot to {screenshot_path}")
    driver.save_screenshot(screenshot_path)
    print(f"    Screenshot saved!")
    
    # Scroll and wait a bit more
    print("\n[9] Scrolling page and checking for dynamic content...")
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(1)
    
    # Final screenshot
    screenshot_path_final = r"C:\Users\0107409306\Documents\To_do_list.worktrees\copilot-update-readme-from-main-dir\main\debug_final.png"
    print(f"[10] Taking final screenshot to {screenshot_path_final}")
    driver.save_screenshot(screenshot_path_final)
    print(f"    Final screenshot saved!")
    
finally:
    driver.quit()
    print("\n[DEBUG] Browser closed. Debug script completed.")
