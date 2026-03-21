"""
Plotly Dash dashboard layout components
Defines the structure and UI elements of the dashboard
"""
from dash import dcc, html
from datetime import datetime, timedelta


def create_dashboard_layout():
    """
    Create the main dashboard layout.
    
    Sections:
    1. Header
    2. League Selector
    3. Date Range Picker
    4. Weight Customizer
    5. Rankings Table
    6. Last Updated Timestamp
    """
    
    return html.Div(
        className="app-container",
        children=[
            # ===== Header =====
            html.Div(
                className="header",
                children=[
                    html.H1("Fantasy Baseball Custom Rankings"),
                    html.P(
                        "Sync Yahoo Fantasy rosters with statcast data for custom hitter rankings",
                        style={"color": "#666", "margin": "5px 0 0 0"}
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
                                            {"label": "Select a league...", "value": ""}
                                        ],
                                        value="",
                                        placeholder="Select a league",
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
                                    html.Label("Date Range", htmlFor="date-range-buttons"),
                                    html.Div(
                                        id="date-range-buttons",
                                        style={
                                            "display": "flex",
                                            "gap": "10px",
                                            "flex-wrap": "wrap"
                                        },
                                        children=[
                                            html.Button(
                                                "Last 7 Days",
                                                id="btn-7days",
                                                className="btn btn-secondary",
                                                n_clicks=0
                                            ),
                                            html.Button(
                                                "Last 14 Days",
                                                id="btn-14days",
                                                className="btn btn-secondary",
                                                n_clicks=0
                                            ),
                                            html.Button(
                                                "Last 30 Days",
                                                id="btn-30days",
                                                className="btn btn-secondary",
                                                n_clicks=0
                                            ),
                                            html.Button(
                                                "Custom Range",
                                                id="btn-custom-range",
                                                className="btn btn-secondary",
                                                n_clicks=0
                                            )
                                        ]
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
                                        date=datetime.now() - timedelta(days=30),
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
                                        date=datetime.now() - timedelta(days=1),
                                        style={"width": "100%"}
                                    )
                                ]
                            )
                        ]
                    )
                ]
            ),
            
            # ===== Weight Customizer Section =====
            html.Div(
                className="metrics-section",
                children=[
                    html.H3("Customize Ranking Weights"),
                    html.Div(
                        className="metrics-grid",
                        children=[
                            # xwOBA Weight
                            html.Div(
                                className="metric-slider",
                                children=[
                                    html.Label("xwOBA", htmlFor="weight-xwoba"),
                                    dcc.Slider(
                                        id="weight-xwoba",
                                        min=0,
                                        max=1,
                                        step=0.01,
                                        value=0.40,
                                        marks=None,
                                        tooltip={
                                            "placement": "bottom",
                                            "always_visible": True
                                        }
                                    ),
                                    html.Div(
                                        id="weight-xwoba-display",
                                        className="metric-weight-display",
                                        children="Weight: 0.40"
                                    )
                                ]
                            ),
                            
                            # Pull Air % Weight
                            html.Div(
                                className="metric-slider",
                                children=[
                                    html.Label("Pull Air %", htmlFor="weight-pull-air"),
                                    dcc.Slider(
                                        id="weight-pull-air",
                                        min=0,
                                        max=1,
                                        step=0.01,
                                        value=0.20,
                                        marks=None,
                                        tooltip={
                                            "placement": "bottom",
                                            "always_visible": True
                                        }
                                    ),
                                    html.Div(
                                        id="weight-pull-air-display",
                                        className="metric-weight-display",
                                        children="Weight: 0.20"
                                    )
                                ]
                            ),
                            
                            # BB:K Weight
                            html.Div(
                                className="metric-slider",
                                children=[
                                    html.Label("BB:K", htmlFor="weight-bbk"),
                                    dcc.Slider(
                                        id="weight-bbk",
                                        min=0,
                                        max=1,
                                        step=0.01,
                                        value=0.30,
                                        marks=None,
                                        tooltip={
                                            "placement": "bottom",
                                            "always_visible": True
                                        }
                                    ),
                                    html.Div(
                                        id="weight-bbk-display",
                                        className="metric-weight-display",
                                        children="Weight: 0.30"
                                    )
                                ]
                            ),
                            
                            # SB per PA Weight
                            html.Div(
                                className="metric-slider",
                                children=[
                                    html.Label("SB per PA", htmlFor="weight-sbpa"),
                                    dcc.Slider(
                                        id="weight-sbpa",
                                        min=0,
                                        max=1,
                                        step=0.01,
                                        value=0.10,
                                        marks=None,
                                        tooltip={
                                            "placement": "bottom",
                                            "always_visible": True
                                        }
                                    ),
                                    html.Div(
                                        id="weight-sbpa-display",
                                        className="metric-weight-display",
                                        children="Weight: 0.10"
                                    )
                                ]
                            )
                        ]
                    ),
                    
                    # Button Group
                    html.Div(
                        className="button-group",
                        children=[
                            html.Button(
                                "Reset to Defaults",
                                id="btn-reset-weights",
                                className="btn btn-secondary",
                                n_clicks=0
                            )
                        ]
                    ),
                    
                    # Weight Sum Display
                    html.Div(
                        id="weights-sum-display",
                        style={
                            "margin-top": "10px",
                            "padding": "10px",
                            "background-color": "#fff",
                            "border-radius": "4px",
                            "font-size": "14px"
                        },
                        children="Total Weight: 1.00"
                    )
                ]
            ),
            
            # ===== Rankings Table =====
            html.Div(
                children=[
                    html.H3("Player Rankings"),
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
            dcc.Store(id="current-league-id", data=""),
            dcc.Store(id="current-start-date", data=""),
            dcc.Store(id="current-end-date", data=""),
            dcc.Store(id="current-weights", data={
                "xwOBA": 0.40,
                "Pull Air %": 0.20,
                "BB:K": 0.30,
                "SB per PA": 0.10
            })
        ]
    )
