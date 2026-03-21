"""
Plotly Dash frontend for Fantasy Baseball Ranking application
Main app initialization and layout definition
"""
import dash
from dash import dcc, html, Input, Output, State
import requests
from datetime import datetime, timedelta
import json

from src.frontend.layouts import create_dashboard_layout
from src.frontend.callbacks import register_callbacks

# Initialize Dash app
app = dash.Dash(
    __name__,
    suppress_callback_exceptions=True,
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"}
    ]
)

# Set app title
app.title = "Fantasy Baseball Custom Rankings"

# Create layout
app.layout = create_dashboard_layout()

# Register callbacks
register_callbacks(app)

# CSS styling
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", "Oxygen",
                    "Ubuntu", "Cantarell", "Fira Sans", "Droid Sans", "Helvetica Neue",
                    sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .app-container {
                max-width: 1400px;
                margin: 0 auto;
                background-color: white;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                padding: 20px;
            }
            .header {
                border-bottom: 2px solid #007bff;
                padding-bottom: 15px;
                margin-bottom: 20px;
            }
            .header h1 {
                margin: 0;
                color: #333;
            }
            .controls-section {
                background-color: #f9f9f9;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 20px;
                border-left: 4px solid #007bff;
            }
            .control-row {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 15px;
                margin-bottom: 15px;
            }
            .control-group {
                display: flex;
                flex-direction: column;
            }
            .control-group label {
                font-weight: 600;
                margin-bottom: 8px;
                color: #333;
            }
            .metrics-section {
                background-color: #f0f8ff;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 20px;
            }
            .metrics-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
            }
            .metric-slider {
                padding: 10px;
                background: white;
                border-radius: 4px;
            }
            .metric-slider label {
                font-weight: 600;
                display: block;
                margin-bottom: 5px;
                color: #333;
            }
            .metric-weight-display {
                font-size: 12px;
                color: #666;
                margin-top: 5px;
            }
            .button-group {
                display: flex;
                gap: 10px;
                margin-top: 15px;
            }
            .btn {
                padding: 10px 20px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-weight: 600;
                transition: background-color 0.3s;
            }
            .btn-primary {
                background-color: #007bff;
                color: white;
            }
            .btn-primary:hover {
                background-color: #0056b3;
            }
            .btn-secondary {
                background-color: #6c757d;
                color: white;
            }
            .btn-secondary:hover {
                background-color: #5a6268;
            }
            .refreshed-at {
                font-size: 12px;
                color: #666;
                margin-top: 15px;
                padding-top: 15px;
                border-top: 1px solid #ddd;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

if __name__ == "__main__":
    app.run_server(debug=True, host="127.0.0.1", port=8050)
