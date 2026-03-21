"""
Plotly Dash callback functions
Handles user interactions and data updates in the dashboard
"""
from dash import Input, Output, State, callback
import requests
from datetime import datetime, timedelta
import pandas as pd


def register_callbacks(app):
    """
    Register all Dash callbacks for the app.
    
    Callbacks handle:
    - League selection
    - Date range selection
    - Weight adjustment
    - Rankings calculation and display
    """
    
    # ===== League Selection Callback =====
    @app.callback(
        [Output("current-league-id", "data"),
         Output("league-dropdown", "options")],
        Input("league-dropdown", "id"),
        prevent_initial_call=True
    )
    def load_leagues(_):
        """Load available leagues from API."""
        try:
            response = requests.get("http://localhost:8000/api/leagues")
            if response.status_code == 200:
                leagues_data = response.json()
                leagues = leagues_data.get("leagues", [])
                
                # Format for dropdown
                options = [
                    {"label": league.get("name"), "value": league.get("id")}
                    for league in leagues
                ]
                
                return "", options
            else:
                return "", [{"label": "Error loading leagues", "value": ""}]
        except Exception as e:
            print(f"Error loading leagues: {e}")
            return "", [{"label": "Error loading leagues", "value": ""}]
    
    
    # ===== Date Range Selection Callbacks =====
    @app.callback(
        [Output("current-start-date", "data"),
         Output("current-end-date", "data")],
        [Input("btn-7days", "n_clicks"),
         Input("btn-14days", "n_clicks"),
         Input("btn-30days", "n_clicks")],
        prevent_initial_call=True
    )
    def update_date_range(clicks_7, clicks_14, clicks_30):
        """Update date range based on preset buttons."""
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        # Determine which button was clicked
        if clicks_7 > 0:
            start_date = (datetime.now() - timedelta(days=8)).strftime("%Y-%m-%d")
        elif clicks_14 > 0:
            start_date = (datetime.now() - timedelta(days=15)).strftime("%Y-%m-%d")
        elif clicks_30 > 0:
            start_date = (datetime.now() - timedelta(days=31)).strftime("%Y-%m-%d")
        else:
            start_date = (datetime.now() - timedelta(days=31)).strftime("%Y-%m-%d")
        
        return start_date, yesterday
    
    
    @app.callback(
        Output("custom-range-div", "style"),
        Input("btn-custom-range", "n_clicks"),
        prevent_initial_call=True
    )
    def toggle_custom_range(n_clicks):
        """Toggle custom date range picker visibility."""
        if n_clicks > 0:
            return {"display": "flex"}
        return {"display": "none"}
    
    
    # ===== Weight Adjustment Callbacks =====
    @app.callback(
        [Output("weight-xwoba-display", "children"),
         Output("weight-pull-air-display", "children"),
         Output("weight-bbk-display", "children"),
         Output("weight-sbpa-display", "children"),
         Output("weights-sum-display", "children"),
         Output("current-weights", "data")],
        [Input("weight-xwoba", "value"),
         Input("weight-pull-air", "value"),
         Input("weight-bbk", "value"),
         Input("weight-sbpa", "value"),
         Input("btn-reset-weights", "n_clicks")],
        prevent_initial_call=True
    )
    def update_weights(xwoba, pull_air, bbk, sbpa, reset_clicks):
        """Update weight displays and current weights store."""
        
        # Reset to defaults if button clicked
        if reset_clicks and reset_clicks > 0:
            xwoba = 0.40
            pull_air = 0.20
            bbk = 0.30
            sbpa = 0.10
        
        # Calculate total weight
        total_weight = xwoba + pull_air + bbk + sbpa
        
        # Prepare displays
        displays = [
            f"Weight: {xwoba:.2f}",
            f"Weight: {pull_air:.2f}",
            f"Weight: {bbk:.2f}",
            f"Weight: {sbpa:.2f}",
            f"Total Weight: {total_weight:.2f}",
        ]
        
        # Store current weights
        current_weights = {
            "xwOBA": xwoba,
            "Pull Air %": pull_air,
            "BB:K": bbk,
            "SB per PA": sbpa
        }
        
        return displays + [current_weights]
    
    
    # ===== Rankings Update Callback =====
    @app.callback(
        [Output("rankings-table-div", "children"),
         Output("refresh-timestamp", "children")],
        [Input("league-dropdown", "value"),
         Input("current-start-date", "data"),
         Input("current-end-date", "data")],
        State("current-weights", "data"),
        prevent_initial_call=True
    )
    def update_rankings(league_id, start_date, end_date, weights):
        """Fetch and display player rankings."""
        
        if not league_id:
            return "Select a league to view rankings", "Last updated: Never"
        
        try:
            # Calculate days back
            if start_date and end_date:
                days_back = (datetime.strptime(end_date, "%Y-%m-%d") - 
                            datetime.strptime(start_date, "%Y-%m-%d")).days
            else:
                days_back = 30
            
            # Fetch stats from API
            response = requests.get(
                f"http://localhost:8000/api/stats/{league_id}",
                params={
                    "days_back": days_back,
                    "weights": weights
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                rankings = data.get("rankings", [])
                updated_at = data.get("updated_at", datetime.now().isoformat())
                
                # Create table
                if rankings:
                    df = pd.DataFrame(rankings)
                    
                    # Import DataTable from Dash
                    from dash import dash_table
                    
                    table = dash_table.DataTable(
                        data=df.to_dict("records"),
                        columns=[{"name": col, "id": col} for col in df.columns],
                        style_cell={"textAlign": "left"},
                        style_header={
                            "backgroundColor": "rgb(230, 230, 230)",
                            "fontWeight": "bold"
                        },
                        style_data_conditional=[
                            {
                                "if": {"row_index": "odd"},
                                "backgroundColor": "rgb(248, 248, 248)"
                            }
                        ],
                        sort_action="native",
                        page_action="native",
                        page_current=0,
                        page_size=20
                    )
                    
                    # Format timestamp
                    try:
                        dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                        timestamp_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                    except:
                        timestamp_str = str(updated_at)
                    
                    return table, f"Last updated: {timestamp_str}"
                else:
                    return "No rankings available for this league", "Last updated: Never"
            else:
                return f"Error loading rankings: {response.status_code}", "Last updated: Never"
        
        except Exception as e:
            return f"Error: {str(e)}", "Last updated: Never"
