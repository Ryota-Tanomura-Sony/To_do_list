"""
Simple test app to diagnose template rendering
"""
import panel as pn

pn.extension("notifications")

# Simple sidebar and main content
sidebar = [
    "## Test Sidebar",
    pn.widgets.TextInput(name="Test Input", value="Hello"),
    pn.widgets.Button(name="Click Me", button_type="success"),
]

main_content = [
    pn.pane.Markdown("# Main Content\n\nThis is a test of VanillaTemplate rendering."),
    pn.pane.Markdown("If you see this, rendering is working!"),
]

# Use VanillaTemplate
template = pn.template.VanillaTemplate(
    title="Test App",
    sidebar=sidebar,
    main=main_content,
)

template.servable()
