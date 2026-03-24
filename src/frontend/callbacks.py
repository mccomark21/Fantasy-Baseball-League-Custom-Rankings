"""Plotly Dash callback functions."""
from dash import Input, Output, State, callback, ctx, html, no_update
from dash.dash_table.Format import Format, Scheme
import requests
from datetime import datetime, timedelta
import pandas as pd
import json


RAW_METRIC_COLUMNS = ["plate_appearances", "batted_ball_events", "xwOBA", "Pull Air %", "BB:K", "SB per PA"]
RAW_SECTION_COLUMNS = ["plate_appearances", "batted_ball_events", "xwOBA", "Pull Air %", "BB:K", "SB per PA"]
Z_SCORE_SECTION_COLUMNS = ["xwOBA_zscore", "Pull Air %_zscore", "BB:K_zscore", "SB per PA_zscore"]
COLUMN_LABELS = {
    "rank": "Rank",
    "player_name": "Player",
    "fantasy_status": "Fantasy Team / Status",
    "position": "Pos",
    "mlb_team": "MLB",
    "plate_appearances": "PA",
    "batted_ball_events": "BBE",
    "xwOBA": "xwOBA",
    "xwOBA_zscore": "xwOBA Z",
    "Pull Air %": "Pull Air %",
    "Pull Air %_zscore": "Pull Air % Z",
    "BB:K": "BB:K",
    "BB:K_zscore": "BB:K Z",
    "SB per PA": "SB per PA",
    "SB per PA_zscore": "SB per PA Z",
    "composite_score": "Composite",
    "data_status": "Data Status",
    "match_status": "Match Status",
    "review_reason": "Review Reason",
}
THEME_TABLE_STYLES = {
    "dark": {
        "cell": {
            "textAlign": "left",
            "whiteSpace": "normal",
            "height": "auto",
            "backgroundColor": "rgba(8, 14, 26, 0.76)",
            "color": "#edf4ff",
            "border": "1px solid rgba(148, 163, 184, 0.16)",
            "padding": "10px",
        },
        "header": {
            "backgroundColor": "rgba(19, 31, 51, 0.95)",
            "color": "#edf4ff",
            "fontWeight": "bold",
            "border": "1px solid rgba(148, 163, 184, 0.22)",
        },
        "odd": "rgba(255, 255, 255, 0.03)",
    },
    "light": {
        "cell": {
            "textAlign": "left",
            "whiteSpace": "normal",
            "height": "auto",
            "backgroundColor": "rgba(255, 255, 255, 0.96)",
            "color": "#132033",
            "border": "1px solid rgba(15, 23, 42, 0.08)",
            "padding": "10px",
        },
        "header": {
            "backgroundColor": "rgba(226, 236, 247, 0.96)",
            "color": "#132033",
            "fontWeight": "bold",
            "border": "1px solid rgba(15, 23, 42, 0.12)",
        },
        "odd": "rgba(15, 23, 42, 0.03)",
    },
}


def _parse_iso_date(value):
    if not value:
        return None
    return datetime.fromisoformat(str(value)[:10])


def _resolve_reference_end(current_end_date):
    return _parse_iso_date(current_end_date) or (datetime.now() - timedelta(days=1))


def _build_z_score_tier_styles(df):
    tier_colors = ["#8f2720", "#c96a62", "rgba(255, 255, 255, 0.04)", "#58aa78", "#1f7a49"]
    styles = []

    for column in Z_SCORE_SECTION_COLUMNS:
        if column not in df.columns:
            continue

        styles.extend([
            {
                "if": {"column_id": column, "filter_query": f"{{{column}}} <= -1.5"},
                "backgroundColor": tier_colors[0],
                "color": "#ffffff",
                "fontWeight": 600,
            },
            {
                "if": {"column_id": column, "filter_query": f"{{{column}}} > -1.5 && {{{column}}} <= -0.5"},
                "backgroundColor": tier_colors[1],
                "color": "#ffffff",
                "fontWeight": 600,
            },
            {
                "if": {"column_id": column, "filter_query": f"{{{column}}} > -0.5 && {{{column}}} < 0.5"},
                "backgroundColor": tier_colors[2],
                "color": "inherit",
            },
            {
                "if": {"column_id": column, "filter_query": f"{{{column}}} >= 0.5 && {{{column}}} < 1.5"},
                "backgroundColor": tier_colors[3],
                "color": "#ffffff",
                "fontWeight": 600,
            },
            {
                "if": {"column_id": column, "filter_query": f"{{{column}}} >= 1.5"},
                "backgroundColor": tier_colors[4],
                "color": "#ffffff",
                "fontWeight": 600,
            },
        ])

    return styles


def _build_group_separator_styles(theme_key):
    divider_color = "rgba(97, 212, 160, 0.55)" if theme_key == "dark" else "rgba(15, 143, 99, 0.32)"
    divider_shadow = "rgba(97, 212, 160, 0.18)" if theme_key == "dark" else "rgba(15, 143, 99, 0.12)"
    return [
        {
            "if": {"column_id": "plate_appearances"},
            "borderLeft": f"3px solid {divider_color}",
            "boxShadow": f"inset 8px 0 0 {divider_shadow}",
        },
        {
            "if": {"column_id": "xwOBA_zscore"},
            "borderLeft": f"3px solid {divider_color}",
            "boxShadow": f"inset 8px 0 0 {divider_shadow}",
        },
    ]


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
         Output("selected-range-label", "data", allow_duplicate=True),
         Output("date-range-dropdown", "value", allow_duplicate=True)],
        Input("league-dropdown", "value"),
        prevent_initial_call=True
    )
    def initialize_date_range_from_dataset(league_id):
        """Initialize the working date range from the dataset that the API returns for the selected league."""
        if not league_id:
            return "", "", "season", "season"

        try:
            response = requests.get(
                f"http://localhost:8000/api/stats/{league_id}",
                params={"include_windows": "true"},
                timeout=15,
            )
            if response.status_code != 200:
                return "", "", "season", "season"

            payload = response.json()
            return payload.get("start_date", ""), payload.get("end_date", ""), "season", "season"
        except Exception as exc:
            print(f"Error initializing date range: {exc}")
            return "", "", "season", "season"


    @app.callback(
        Output("active-range-display", "children"),
        [Input("current-start-date", "data"),
         Input("current-end-date", "data"),
         Input("selected-range-label", "data")],
        prevent_initial_call=False
    )
    def update_active_range_display(start_date, end_date, range_label):
        """Show the currently active date range even when the custom picker is hidden."""
        if start_date and end_date:
            label_prefix = {
                "7d": "Last 7 Days",
                "14d": "Last 14 Days",
                "30d": "Last 30 Days",
                "season": "Season to Date",
                "custom": "Custom Range",
            }.get(range_label, "Active Range")
            return f"{label_prefix}: {start_date} to {end_date}"
        return "No active range selected"
    
    
    # ===== Date Range Selection Callbacks =====
    @app.callback(
        [Output("current-start-date", "data"),
         Output("current-end-date", "data"),
         Output("selected-range-label", "data"),
         Output("custom-range-div", "style")],
        Input("date-range-dropdown", "value"),
        State("current-end-date", "data"),
        prevent_initial_call=True
    )
    def update_date_range(selected_range, current_end_date):
        """Update date range based on the selected preset dropdown value."""
        reference_end = _resolve_reference_end(current_end_date)

        if selected_range == "custom":
            return no_update, no_update, "custom", {"display": "flex"}
        if selected_range == "7d":
            start_date = reference_end - timedelta(days=6)
        elif selected_range == "14d":
            start_date = reference_end - timedelta(days=13)
        elif selected_range == "30d":
            start_date = reference_end - timedelta(days=29)
        else:
            start_date = datetime(reference_end.year, 3, 1)
            selected_range = "season"

        return (
            start_date.strftime("%Y-%m-%d"),
            reference_end.strftime("%Y-%m-%d"),
            selected_range,
            {"display": "none"},
        )


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
        [Output("current-theme", "data"),
         Output("app-theme-root", "className"),
         Output("btn-theme-toggle", "children")],
        Input("btn-theme-toggle", "n_clicks"),
        State("current-theme", "data"),
        prevent_initial_call=False
    )
    def update_theme(n_clicks, current_theme):
        """Toggle the dashboard theme between dark and light modes."""
        theme = current_theme or "dark"
        if ctx.triggered_id == "btn-theme-toggle" and n_clicks:
            theme = "light" if theme == "dark" else "dark"

        next_label = "Switch to Dark Mode" if theme == "light" else "Switch to Light Mode"
        return theme, f"theme-shell theme-{theme}", next_label
    
    
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
                resolved_start_date = data.get("start_date") or start_date or "N/A"
                resolved_end_date = data.get("end_date") or end_date or "N/A"
                summary = (
                    f"{status_message} Range: {resolved_start_date} to {resolved_end_date} | "
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
         Input("ownership-filter", "value"),
         Input("current-theme", "data")],
        prevent_initial_call=False
    )
    def render_rankings_table(rows, ownership_filter, current_theme):
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
            "plate_appearances",
            "batted_ball_events",
            "xwOBA",
            "Pull Air %",
            "BB:K",
            "SB per PA",
            "xwOBA_zscore",
            "Pull Air %_zscore",
            "BB:K_zscore",
            "SB per PA_zscore",
            "composite_score",
            "data_status",
            "match_status",
            "review_reason",
        ]
        visible_columns = [column for column in preferred_columns if column in df.columns]
        if visible_columns:
            df = df[visible_columns]

        for numeric_column in Z_SCORE_SECTION_COLUMNS:
            if numeric_column in df.columns:
                df[numeric_column] = pd.to_numeric(df[numeric_column], errors="coerce").round(2)

        if "composite_score" in df.columns:
            df["composite_score"] = pd.to_numeric(df["composite_score"], errors="coerce").map(
                lambda value: None if pd.isna(value) else float(f"{value:.2f}")
            )

        from dash import dash_table

        theme_key = "light" if current_theme == "light" else "dark"
        theme_styles = THEME_TABLE_STYLES[theme_key]
        style_data_conditional = [
            {
                "if": {"row_index": "odd"},
                "backgroundColor": theme_styles["odd"],
            },
            *(_build_group_separator_styles(theme_key)),
            *(_build_z_score_tier_styles(df)),
            {
                "if": {"state": "active"},
                "backgroundColor": "rgba(97, 212, 160, 0.10)" if theme_key == "dark" else "rgba(15, 143, 99, 0.10)",
                "color": theme_styles["cell"]["color"],
                "border": f"1px solid {'rgba(97, 212, 160, 0.55)' if theme_key == 'dark' else 'rgba(15, 143, 99, 0.32)'}",
            },
            {
                "if": {"state": "selected"},
                "backgroundColor": "rgba(97, 212, 160, 0.12)" if theme_key == "dark" else "rgba(15, 143, 99, 0.12)",
                "color": theme_styles["cell"]["color"],
                "border": f"1px solid {'rgba(97, 212, 160, 0.55)' if theme_key == 'dark' else 'rgba(15, 143, 99, 0.32)'}",
            },
        ]

        table_css = [
            {
                "selector": ".dash-spreadsheet-inner tr:hover td",
                "rule": "background-color: inherit !important; color: inherit !important; box-shadow: none !important;",
            },
            {
                "selector": ".dash-spreadsheet-inner tr:hover td div",
                "rule": "background-color: transparent !important; color: inherit !important;",
            },
            {
                "selector": ".dash-spreadsheet-inner tbody tr:hover td",
                "rule": "background-color: inherit !important; color: inherit !important; box-shadow: none !important;",
            },
            {
                "selector": ".dash-spreadsheet-inner tbody tr:hover td div",
                "rule": "background-color: transparent !important; color: inherit !important;",
            },
        ]

        columns = []
        for col in df.columns:
            column_config = {"name": COLUMN_LABELS.get(col, col), "id": col}
            if col in Z_SCORE_SECTION_COLUMNS or col == "composite_score":
                column_config["type"] = "numeric"
                column_config["format"] = Format(precision=2, scheme=Scheme.fixed)
            columns.append(column_config)

        return dash_table.DataTable(
            data=df.to_dict("records"),
            columns=columns,
            style_cell=theme_styles["cell"],
            style_header=theme_styles["header"],
            style_header_conditional=_build_group_separator_styles(theme_key),
            style_data_conditional=style_data_conditional,
            css=table_css,
            sort_action="native",
            page_action="native",
            page_current=0,
            page_size=20,
            style_table={"overflowX": "auto", "borderRadius": "14px", "overflowY": "hidden"},
        )
