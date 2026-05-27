#!/usr/bin/env python3
"""
Debug: Test different template types with To_do app
"""
import panel as pn

pn.extension("notifications", sizing_mode="stretch_width")

# Simple test content
title_input = pn.widgets.TextInput(name="Title", placeholder="Enter task title")
add_button = pn.widgets.Button(name="Add Task", button_type="success", width=100)
main_content = pn.pane.Markdown("# Main Content\n\nThis is the main area.")
sidebar_content = [
    "## Sidebar",
    title_input,
    add_button,
]

# Test 1: FastListTemplate (default)
print("[TEST 1] FastListTemplate...")
try:
    template1 = pn.template.FastListTemplate(
        title="Test FastListTemplate",
        sidebar=sidebar_content,
        main=[main_content],
    )
    print("  ✓ FastListTemplate created successfully")
except Exception as e:
    print(f"  ✗ FastListTemplate error: {e}")

# Test 2: BootstrapTemplate
print("[TEST 2] BootstrapTemplate...")
try:
    template2 = pn.template.BootstrapTemplate(
        title="Test BootstrapTemplate",
        sidebar=sidebar_content,
        main=[main_content],
    )
    print("  ✓ BootstrapTemplate created successfully")
except Exception as e:
    print(f"  ✗ BootstrapTemplate error: {e}")

# Test 3: MaterialTemplate
print("[TEST 3] MaterialTemplate...")
try:
    template3 = pn.template.MaterialTemplate(
        title="Test MaterialTemplate",
        sidebar=sidebar_content,
        main=[main_content],
    )
    print("  ✓ MaterialTemplate created successfully")
except Exception as e:
    print(f"  ✗ MaterialTemplate error: {e}")

# Test 4: VanillaTemplate
print("[TEST 4] VanillaTemplate...")
try:
    template4 = pn.template.VanillaTemplate(
        title="Test VanillaTemplate",
        sidebar=sidebar_content,
        main=[main_content],
    )
    print("  ✓ VanillaTemplate created successfully")
except Exception as e:
    print(f"  ✗ VanillaTemplate error: {e}")

# Test 5: DarkTemplate
print("[TEST 5] DarkTemplate...")
try:
    template5 = pn.template.DarkTemplate(
        title="Test DarkTemplate",
        sidebar=sidebar_content,
        main=[main_content],
    )
    print("  ✓ DarkTemplate created successfully")
except Exception as e:
    print(f"  ✗ DarkTemplate error: {e}")

print("\nAll template types tested.")
