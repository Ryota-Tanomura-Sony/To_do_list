#!/usr/bin/env python3
"""
Minimal test to debug Panel rendering - with HTML fallback
"""
import panel as pn

# Don't use extension - try direct HTML
html_content = """
<html>
<body>
<h1>Hello World</h1>
<p>This is a test</p>
<button>Click Me</button>
</body>
</html>
"""

pn.pane.HTML(html_content).servable()
