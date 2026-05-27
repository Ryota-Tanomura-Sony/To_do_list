"""
Simplified test with explicit sizing
"""
import panel as pn
import param
import pandas as pd
import datetime as dt

pn.extension("notifications")

# Sample data
data = {
    "id": [1, 2, 3],
    "title": ["Task 1", "Task 2", "Task 3"],
    "quadrant": ["Do", "Schedule", "Delegate"],
}
df = pd.DataFrame(data)

# Simple widgets
title_input = pn.widgets.TextInput(name="Task Title", placeholder="Enter task", width=400)
add_button = pn.widgets.Button(name="Add", button_type="primary", width=100)

# Display area
task_table = pn.widgets.DataFrame(df, name="Tasks")

# Main content with explicit sizing
content = pn.Column(
    pn.pane.Markdown("# Task Manager"),
    pn.Row(title_input, add_button, width=600),
    task_table,
    width=1000,
    height=700,
)

content.servable()
