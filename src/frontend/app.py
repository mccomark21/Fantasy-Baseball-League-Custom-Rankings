"""Plotly Dash frontend for Fantasy Baseball Ranking application."""
import dash

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
                font-family: "Aptos", "Trebuchet MS", "Segoe UI", sans-serif;
                margin: 0;
                background:
                    radial-gradient(circle at top, rgba(33, 198, 142, 0.18), transparent 28%),
                    linear-gradient(180deg, #09111c 0%, #111c2b 100%);
            }
            .theme-shell {
                min-height: 100vh;
                padding: 20px;
                color: var(--text-primary);
                background: var(--shell-background);
                transition: background-color 0.25s ease, color 0.25s ease;
            }
            .theme-dark {
                --shell-background: transparent;
                --panel-background: rgba(11, 18, 31, 0.92);
                --panel-secondary: rgba(19, 31, 51, 0.88);
                --surface-background: rgba(255, 255, 255, 0.05);
                --surface-elevated: rgba(255, 255, 255, 0.08);
                --border-color: rgba(148, 163, 184, 0.22);
                --text-primary: #edf4ff;
                --text-secondary: #a9bad4;
                --accent-color: #61d4a0;
                --accent-strong: #2ab87d;
                --shadow-color: rgba(3, 7, 18, 0.42);
                --link-color: #8ae6bd;
                --input-background: rgba(8, 14, 26, 0.92);
            }
            .theme-light {
                --shell-background: linear-gradient(180deg, #edf3ff 0%, #f8fbff 100%);
                --panel-background: rgba(255, 255, 255, 0.92);
                --panel-secondary: rgba(239, 247, 255, 0.95);
                --surface-background: rgba(241, 246, 252, 0.96);
                --surface-elevated: rgba(255, 255, 255, 0.98);
                --border-color: rgba(15, 23, 42, 0.12);
                --text-primary: #132033;
                --text-secondary: #526377;
                --accent-color: #0f8f63;
                --accent-strong: #0b6d4b;
                --shadow-color: rgba(15, 23, 42, 0.12);
                --link-color: #0f8f63;
                --input-background: rgba(255, 255, 255, 0.96);
            }
            .app-container {
                max-width: 1400px;
                margin: 0 auto;
                background: var(--panel-background);
                border-radius: 24px;
                box-shadow: 0 20px 50px var(--shadow-color);
                padding: 24px;
                border: 1px solid var(--border-color);
                backdrop-filter: blur(14px);
            }
            .header {
                border-bottom: 1px solid var(--border-color);
                padding-bottom: 18px;
                margin-bottom: 20px;
            }
            .header-row {
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                gap: 16px;
            }
            .header h1 {
                margin: 0;
                color: var(--text-primary);
                letter-spacing: 0.01em;
            }
            .header-subtitle,
            .supporting-text {
                color: var(--text-secondary);
            }
            .subtle-text {
                opacity: 0.92;
            }
            .controls-section {
                background: var(--panel-secondary);
                padding: 15px;
                border-radius: 16px;
                margin-bottom: 20px;
                border: 1px solid var(--border-color);
                border-left: 4px solid var(--accent-color);
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
                color: var(--text-primary);
            }
            .metrics-section {
                background: var(--panel-secondary);
                padding: 15px;
                border-radius: 16px;
                margin-bottom: 20px;
                border: 1px solid var(--border-color);
            }
            .metrics-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
            }
            .metric-slider {
                padding: 10px;
                background: var(--surface-elevated);
                border-radius: 12px;
                border: 1px solid var(--border-color);
            }
            .metric-slider label {
                font-weight: 600;
                display: block;
                margin-bottom: 5px;
                color: var(--text-primary);
            }
            .metric-weight-display {
                font-size: 12px;
                color: var(--text-secondary);
                margin-top: 5px;
            }
            .surface-card {
                padding: 10px 12px;
                background: var(--surface-background);
                border-radius: 12px;
                border: 1px solid var(--border-color);
                color: var(--text-primary);
            }
            .button-group {
                display: flex;
                gap: 10px;
                margin-top: 15px;
                flex-wrap: wrap;
            }
            .btn {
                padding: 10px 20px;
                border: 1px solid transparent;
                border-radius: 999px;
                cursor: pointer;
                font-weight: 600;
                transition: background-color 0.2s ease, color 0.2s ease, border-color 0.2s ease, transform 0.2s ease;
            }
            .btn:hover {
                transform: translateY(-1px);
            }
            .btn-primary {
                background-color: var(--accent-color);
                color: #08111f;
            }
            .btn-primary:hover {
                background-color: var(--accent-strong);
            }
            .btn-secondary {
                background: var(--surface-elevated);
                color: var(--text-primary);
                border-color: var(--border-color);
            }
            .btn-secondary:hover {
                background: var(--surface-background);
            }
            .btn-theme-toggle {
                align-self: center;
            }
            .refreshed-at {
                font-size: 12px;
                color: var(--text-secondary);
                margin-top: 15px;
                padding-top: 15px;
                border-top: 1px solid var(--border-color);
            }
            .theme-shell a {
                color: var(--link-color);
            }
            .theme-shell .Select-control,
            .theme-shell .DateInput,
            .theme-shell .DateInput_input {
                background: var(--input-background) !important;
                color: var(--text-primary) !important;
                border-color: var(--border-color) !important;
            }
            .theme-shell .Select-control:hover,
            .theme-shell .is-open > .Select-control {
                border-color: var(--accent-color) !important;
                box-shadow: 0 0 0 1px var(--accent-color) !important;
            }
            .theme-shell .Select-menu-outer {
                background: var(--input-background) !important;
                border: 1px solid var(--border-color) !important;
                box-shadow: 0 14px 30px var(--shadow-color) !important;
            }
            .theme-shell .Select-menu-outer,
            .theme-shell .Select-menu,
            .theme-shell .Select-option,
            .theme-shell .Select-value-label,
            .theme-shell .DateInput_input {
                color: var(--text-primary) !important;
            }
            .theme-shell .Select-option,
            .theme-shell .VirtualizedSelectOption {
                background: var(--input-background) !important;
                color: var(--text-primary) !important;
            }
            .theme-shell .Select-value,
            .theme-shell .Select-value-label,
            .theme-shell .Select-arrow,
            .theme-shell .Select-arrow-zone,
            .theme-shell .Select-clear-zone,
            .theme-shell .Select-input > input {
                color: var(--text-primary) !important;
            }
            .theme-shell .Select-option.is-focused,
            .theme-shell .Select-option:hover,
            .theme-shell .VirtualizedSelectFocusedOption,
            .theme-shell .VirtualizedSelectOption:hover {
                background: var(--surface-elevated) !important;
                color: var(--text-primary) !important;
            }
            .theme-shell .Select-option.is-selected,
            .theme-shell .VirtualizedSelectSelectedOption {
                background: var(--accent-color) !important;
                color: #08111f !important;
            }
            .theme-shell .Select-placeholder {
                color: var(--text-secondary) !important;
            }
            .theme-shell .dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner td.focused,
            .theme-shell .dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner td.cell--selected {
                background: rgba(97, 212, 160, 0.10) !important;
                color: var(--text-primary) !important;
                border-color: var(--accent-color) !important;
            }
            @media (max-width: 768px) {
                .theme-shell {
                    padding: 12px;
                }
                .app-container {
                    padding: 16px;
                    border-radius: 18px;
                }
                .header-row {
                    flex-direction: column;
                    align-items: stretch;
                }
                .btn-theme-toggle {
                    width: 100%;
                }
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
    app.run_server(debug=False, host="127.0.0.1", port=8050)
