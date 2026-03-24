"""
Plotly Dash dashboard layout components
Defines the structure and UI elements of the dashboard
"""
from dash import dcc, html
from datetime import datetime, timedelta

from src.backend.demo_data import DEMO_LEAGUE_ID


DEMO_START_DATE = "2025-08-01"
DEMO_END_DATE = "2025-08-30"


def create_dashboard_layout():
    """
    Create the main dashboard layout.
    
    Sections:
    1. Header
    2. League Selector
    3. Date Range Picker
    4. Rankings Table
    5. Last Updated Timestamp
    """
    
    return html.Div(
        id="app-theme-root",
        className="theme-shell theme-dark",
        children=[
            html.Div(
                className="app-container",
                children=[
            # ===== Header =====
            html.Div(
                className="header",
                children=[
                    html.Div(
                        className="header-row",
                        children=[
                            html.Div(
                                children=[
                                    html.H1("Fantasy Baseball Custom Rankings"),
                                    html.P(
                                        "Sync Yahoo Fantasy rosters with statcast data for custom hitter rankings",
                                        className="header-subtitle",
                                    ),
                                ]
                            ),
                            html.Button(
                                "Switch to Light Mode",
                                id="btn-theme-toggle",
                                className="btn btn-theme-toggle",
                                n_clicks=0,
                            ),
                        ],
                    )
                ]
            ),
            
            # ===== Controls Section =====
            html.Div(
                className="controls-section",
                children=[
                    # League Selector
                    html.Div(
                        className="control-row",
                        children=[
                            html.Div(
                                className="control-group",
                                children=[
                                    html.Label("Select League", htmlFor="league-dropdown"),
                                    dcc.Dropdown(
                                        id="league-dropdown",
                                        options=[
                                            {"label": "Demo League (2025 Reference)", "value": DEMO_LEAGUE_ID}
                                        ],
                                        value=DEMO_LEAGUE_ID,
                                        placeholder="Select a league",
                                        style={"width": "100%"}
                                    )
                                ]
                            ),
                            html.Div(
                                className="control-group",
                                children=[
                                    html.Label("Player Filter", htmlFor="ownership-filter"),
                                    dcc.Dropdown(
                                        id="ownership-filter",
                                        options=[{"label": "All Players", "value": "all"}],
                                        value="all",
                                        clearable=False,
                                        style={"width": "100%"}
                                    )
                                ]
                            )
                        ]
                    ),
                    
                    # Date Range Selector
                    html.Div(
                        className="control-row",
                        children=[
                            html.Div(
                                className="control-group",
                                children=[
                                    html.Label("Date Range", htmlFor="date-range-dropdown"),
                                    dcc.Dropdown(
                                        id="date-range-dropdown",
                                        options=[
                                            {"label": "Last 7 Days", "value": "7d"},
                                            {"label": "Last 14 Days", "value": "14d"},
                                            {"label": "Last 30 Days", "value": "30d"},
                                            {"label": "Season to Date", "value": "season"},
                                            {"label": "Custom Range", "value": "custom"},
                                        ],
                                        value="season",
                                        clearable=False,
                                        style={"width": "100%"},
                                    )
                                ]
                            ),
                            html.Div(
                                className="control-group",
                                children=[
                                    html.Label("Active Range"),
                                    html.Div(
                                        id="active-range-display",
                                        className="surface-card",
                                        style={"minHeight": "20px"},
                                        children=f"{DEMO_START_DATE} to {DEMO_END_DATE}"
                                    )
                                ]
                            )
                        ]
                    ),
                    
                    # Custom Date Range (Hidden by default)
                    html.Div(
                        id="custom-range-div",
                        className="control-row",
                        style={"display": "none"},
                        children=[
                            html.Div(
                                className="control-group",
                                children=[
                                    html.Label("Start Date"),
                                    dcc.DatePickerSingle(
                                        id="date-picker-start",
                                        date=DEMO_START_DATE,
                                        style={"width": "100%"}
                                    )
                                ]
                            ),
                            html.Div(
                                className="control-group",
                                children=[
                                    html.Label("End Date"),
                                    dcc.DatePickerSingle(
                                        id="date-picker-end",
                                        date=DEMO_END_DATE,
                                        style={"width": "100%"}
                                    )
                                ]
                            )
                        ]
                    ),
                    html.Div(
                        className="button-group",
                        children=[
                            html.Button(
                                "Apply Filters",
                                id="btn-apply-filters",
                                className="btn btn-primary",
                                n_clicks=0
                            )
                        ]
                    )
                ]
            ),
            
            # ===== Rankings Table =====
            html.Div(
                children=[
                    html.H3("Player Rankings"),
                    html.Div(
                        id="rankings-summary",
                        className="supporting-text",
                        style={"marginBottom": "12px", "fontSize": "14px"},
                        children="Select a league to load rankings."
                    ),
                    html.Div(
                        id="mismatch-review",
                        className="supporting-text subtle-text",
                        style={"marginBottom": "12px", "fontSize": "13px"},
                        children="Mismatch review will appear here when needed."
                    ),
                    dcc.Loading(
                        id="loading",
                        type="default",
                        children=[
                            html.Div(id="rankings-table-div")
                        ]
                    )
                ]
            ),
            
            # ===== Last Updated Timestamp =====
            html.Div(
                id="refresh-timestamp",
                className="refreshed-at",
                children="Last updated: Never"
            ),
            
            # ===== Hidden Stores =====
            dcc.Interval(id="initial-load", interval=250, n_intervals=0, max_intervals=1),
            dcc.Store(id="current-league-id", data=DEMO_LEAGUE_ID),
            dcc.Store(id="current-start-date", data=DEMO_START_DATE),
            dcc.Store(id="current-end-date", data=DEMO_END_DATE),
            dcc.Store(id="selected-range-label", data="custom"),
            dcc.Store(id="current-display-rows", data=[]),
            dcc.Store(id="current-theme", data="dark"),
            dcc.Store(id="current-weights", data={
                "xwOBA": 0.40,
                "Pull Air %": 0.20,
                "BB:K": 0.30,
                "SB per PA": 0.10
            })
        ]
            )
        ]
    )
