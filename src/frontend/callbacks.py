"""
Plotly Dash callback functions
Handles user interactions and data updates in the dashboard
"""
from dash import Input, Output, State, callback, ctx, html
import requests
from datetime import datetime, timedelta
import pandas as pd
import json


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
         Output("league-dropdown", "options"),
         Output("league-dropdown", "value")],
        Input("initial-load", "n_intervals")
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
                if not options:
                    options = [{"label": "No leagues available", "value": ""}]
                default_league = options[0]["value"] if options and options[0]["value"] else ""
                return default_league, options, default_league
            else:
                return "", [{"label": "Error loading leagues", "value": ""}], ""
        except Exception as e:
            print(f"Error loading leagues: {e}")
            return "", [{"label": "Error loading leagues", "value": ""}], ""


    @app.callback(
        [Output("current-start-date", "data", allow_duplicate=True),
         Output("current-end-date", "data", allow_duplicate=True),
         Output("selected-range-label", "data", allow_duplicate=True)],
        Input("league-dropdown", "value"),
        prevent_initial_call=True
    )
    def initialize_date_range_from_dataset(league_id):
        """Initialize the working date range from the dataset that the API returns for the selected league."""
        if not league_id:
            return "", "", "30d"

        try:
            response = requests.get(
                f"http://localhost:8000/api/stats/{league_id}",
                params={"include_windows": "true"},
                timeout=15,
            )
            if response.status_code != 200:
                return "", "", "30d"

            payload = response.json()
            return payload.get("start_date", ""), payload.get("end_date", ""), "custom"
        except Exception as exc:
            print(f"Error initializing date range: {exc}")
            return "", "", "30d"


    @app.callback(
        Output("active-range-display", "children"),
        [Input("current-start-date", "data"),
         Input("current-end-date", "data")],
        prevent_initial_call=False
    )
    def update_active_range_display(start_date, end_date):
        """Show the currently active date range even when the custom picker is hidden."""
        if start_date and end_date:
            return f"{start_date} to {end_date}"
        return "No active range selected"
    
    
    # ===== Date Range Selection Callbacks =====
    @app.callback(
        [Output("current-start-date", "data"),
         Output("current-end-date", "data"),
         Output("selected-range-label", "data")],
        [Input("btn-7days", "n_clicks"),
         Input("btn-14days", "n_clicks"),
         Input("btn-30days", "n_clicks")],
        prevent_initial_call=True
    )
    def update_date_range(clicks_7, clicks_14, clicks_30):
        """Update date range based on preset buttons."""
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        triggered_id = ctx.triggered_id
        if triggered_id == "btn-7days":
            start_date = (datetime.now() - timedelta(days=6)).strftime("%Y-%m-%d")
            range_label = "7d"
        elif triggered_id == "btn-14days":
            start_date = (datetime.now() - timedelta(days=13)).strftime("%Y-%m-%d")
            range_label = "14d"
        elif triggered_id == "btn-30days":
            start_date = (datetime.now() - timedelta(days=29)).strftime("%Y-%m-%d")
            range_label = "30d"
        else:
            start_date = (datetime.now() - timedelta(days=29)).strftime("%Y-%m-%d")
            range_label = "30d"
        
        return start_date, yesterday, range_label


    @app.callback(
        [Output("current-start-date", "data", allow_duplicate=True),
         Output("current-end-date", "data", allow_duplicate=True),
         Output("selected-range-label", "data", allow_duplicate=True)],
        [Input("date-picker-start", "date"),
         Input("date-picker-end", "date")],
        prevent_initial_call=True
    )
    def update_custom_date_range(start_date, end_date):
        """Update current dates when the custom picker changes."""
        if not start_date or not end_date:
            return "", "", "custom"
        return str(start_date), str(end_date), "custom"
    
    
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
        [Output("rankings-summary", "children"),
         Output("current-display-rows", "data"),
         Output("ownership-filter", "options"),
         Output("ownership-filter", "value"),
         Output("mismatch-review", "children"),
         Output("refresh-timestamp", "children")],
        [Input("initial-load", "n_intervals"),
         Input("btn-apply-filters", "n_clicks")],
        [State("league-dropdown", "value"),
         State("current-start-date", "data"),
         State("current-end-date", "data"),
         State("current-weights", "data"),
         State("selected-range-label", "data")],
        prevent_initial_call=False
    )
    def update_rankings(_, __, league_id, start_date, end_date, weights, range_label):
        """Fetch rankings or preseason roster rows and update dashboard state."""
        
        if not league_id:
            default_options = [{"label": "All Players", "value": "all"}]
            return "Select a league to view rankings.", [], default_options, "all", "Mismatch review will appear here when needed.", "Last updated: Never"
        
        try:
            # Calculate days back
            if start_date and end_date:
                days_back = (datetime.strptime(end_date, "%Y-%m-%d") - 
                            datetime.strptime(start_date, "%Y-%m-%d")).days + 1
            else:
                days_back = 30
            
            # Fetch stats from API
            response = requests.get(
                f"http://localhost:8000/api/stats/{league_id}",
                params={
                    "days_back": days_back,
                    "start_date": start_date,
                    "end_date": end_date,
                    "include_windows": "true",
                    "weights": json.dumps(weights)
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                precomputed_windows = data.get("precomputed_windows", {})
                rankings = precomputed_windows.get(range_label, data.get("rankings", [])) if range_label in {"7d", "14d", "30d"} and data.get("stats_available") else data.get("rankings", [])
                updated_at = data.get("updated_at", datetime.now().isoformat())
                matched_count = data.get("matched_player_count", 0)
                mismatch_count = data.get("mismatch_count", 0)
                season_phase = data.get("season_phase", "unknown")
                status_message = data.get("status_message", "")
                summary = (
                    f"{status_message} Range: {start_date or 'N/A'} to {end_date or 'N/A'} | "
                    f"Matched players: {matched_count} | Mismatches: {mismatch_count} | Phase: {season_phase}"
                )
                filter_options = data.get("ownership_filter_options") or [{"label": "All Players", "value": "all"}]
                mismatch_debug_path = data.get("mismatch_debug_path")
                if mismatch_count > 0 and mismatch_debug_path:
                    mismatch_review = html.A(
                        f"Review {mismatch_count} unresolved player mappings",
                        href=f"http://localhost:8000{mismatch_debug_path}",
                        target="_blank",
                    )
                else:
                    mismatch_review = "No unresolved player mappings in the current dataset."

                try:
                    dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                    timestamp_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    timestamp_str = str(updated_at)
                    
                return summary, rankings, filter_options, "all", mismatch_review, f"Last updated: {timestamp_str}"
            else:
                default_options = [{"label": "All Players", "value": "all"}]
                return "Unable to load rankings.", [], default_options, "all", "Mismatch review unavailable.", f"Error loading rankings: {response.status_code}"
        
        except Exception as e:
            default_options = [{"label": "All Players", "value": "all"}]
            return "Unable to load rankings.", [], default_options, "all", "Mismatch review unavailable.", f"Error: {str(e)}"


    @app.callback(
        Output("rankings-table-div", "children"),
        [Input("current-display-rows", "data"),
         Input("ownership-filter", "value")],
        prevent_initial_call=False
    )
    def render_rankings_table(rows, ownership_filter):
        """Render the rankings or preseason roster table using the current ownership filter."""
        if not rows:
            return "No player rows available for the current selection."

        filtered_rows = []
        for row in rows:
            fantasy_status = row.get("fantasy_status")
            if ownership_filter == "all":
                include_row = True
            elif ownership_filter == "free_agents":
                include_row = fantasy_status == "Free Agent"
            elif ownership_filter == "waivers":
                include_row = fantasy_status == "Waivers"
            elif ownership_filter == "rostered":
                include_row = fantasy_status not in {"Free Agent", "Waivers", None, ""}
            else:
                include_row = fantasy_status == ownership_filter

            if include_row:
                filtered_rows.append(row)

        if not filtered_rows:
            return "No players match the current filter."

        df = pd.DataFrame(filtered_rows)
        preferred_columns = [
            "rank",
            "player_name",
            "fantasy_status",
            "position",
            "mlb_team",
            "xwOBA",
            "Pull Air %",
            "BB:K",
            "SB per PA",
            "composite_score",
            "data_status",
            "match_status",
            "review_reason",
        ]
        visible_columns = [column for column in preferred_columns if column in df.columns]
        if visible_columns:
            df = df[visible_columns]

        from dash import dash_table

        return dash_table.DataTable(
            data=df.to_dict("records"),
            columns=[{"name": col, "id": col} for col in df.columns],
            style_cell={"textAlign": "left", "whiteSpace": "normal", "height": "auto"},
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
