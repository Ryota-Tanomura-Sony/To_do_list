#!/usr/bin/env python3
"""
Simple debug script using requests to check Panel app rendering
"""
import sys
import time
import json
import requests

print("[DEBUG] Starting HTTP debug check...")

try:
    # Check if server is running
    print("[1] Checking if server is running on port 5007...")
    resp = requests.get("http://localhost:5007/To_do", timeout=10)
    print(f"    Status: {resp.status_code}")
    print(f"    Content-Type: {resp.headers.get('Content-Type')}")
    print(f"    Content-Length: {len(resp.content)}")
    
    html = resp.text
    
    # Check for key elements
    checks = {
        "FastListTemplate CSS": "fast_list_template.css" in html,
        "FastListTemplate HTML": "sidenav" in html and 'id="sidebar"' in html,
        "Bokeh JS": "bokeh" in html.lower(),
        "Bokeh root": "bk-root" in html,
        "Widgets div": 'data-root-id' in html,
        "Panel widgets": "pn-vert" in html or "pn-row" in html or 'pn-widgets' in html.lower(),
        "Script tags": "<script" in html,
    }
    
    print("\n[2] Content checks:")
    for check_name, result in checks.items():
        print(f"    {check_name}: {'✓' if result else '✗'}")
    
    # Find panel/bokeh initialization
    print("\n[3] Searching for Bokeh/Panel initialization...")
    if "Bokeh" in html:
        # Find the JSON initialization
        import re
        bokeh_init = re.findall(r'Bokeh\.embed\.embed_items.*?;', html, re.DOTALL)
        if bokeh_init:
            print(f"    Found {len(bokeh_init)} embed_items calls")
            for i, init in enumerate(bokeh_init[:2]):
                print(f"    [{i}] {init[:200]}...")
    
    # Check CSS for display: none or similar
    print("\n[4] Checking for hiding styles...")
    hiding_patterns = [
        "display: none",
        "visibility: hidden",
        "opacity: 0",
        "height: 0",
        "width: 0",
    ]
    
    for pattern in hiding_patterns:
        if pattern in html:
            count = html.count(pattern)
            print(f"    Found '{pattern}': {count} times")
    
    # Save HTML for inspection
    output_file = r"C:\Users\0107409306\Documents\To_do_list.worktrees\copilot-update-readme-from-main-dir\main\debug_response.html"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"\n[5] Saved full HTML to: {output_file}")
    print(f"    File size: {len(html)} bytes")
    
except requests.exceptions.ConnectionError as e:
    print(f"[ERROR] Failed to connect to server: {e}")
    sys.exit(1)
except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n[DEBUG] HTTP debug check completed.")
