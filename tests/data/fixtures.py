"""Small hand-built payload fixtures shaped like real FPL API responses."""

TEAMS_PAYLOAD = [
    {
        "id": 1,
        "name": "Arsenal",
        "short_name": "ARS",
        "strength_overall_home": 1200,
        "strength_overall_away": 1250,
        "strength_attack_home": 1200,
        "strength_attack_away": 1250,
        "strength_defence_home": 1200,
        "strength_defence_away": 1250,
    },
    {
        "id": 2,
        "name": "Chelsea",
        "short_name": "CHE",
        "strength_overall_home": 1150,
        "strength_overall_away": 1180,
        "strength_attack_home": 1150,
        "strength_attack_away": 1180,
        "strength_defence_home": 1150,
        "strength_defence_away": 1180,
    },
]

ELEMENTS_PAYLOAD = [
    {
        "id": 101,
        "team": 1,
        "first_name": "David",
        "second_name": "Raya",
        "web_name": "Raya",
        "element_type": 1,
        "now_cost": 55,
        "selected_by_percent": "31.2",
        "form": "4.5",
        "total_points": 120,
        "status": "a",
        "chance_of_playing_next_round": None,
        "news": "",
    },
]

FIXTURES_PAYLOAD = [
    {
        "id": 1001,
        "event": 1,
        "kickoff_time": "2026-08-21T19:00:00Z",
        "finished": False,
        "team_h": 1,
        "team_a": 2,
        "team_h_score": None,
        "team_a_score": None,
        "team_h_difficulty": 2,
        "team_a_difficulty": 4,
    },
]

PLAYER_HISTORY_PAYLOAD = [
    {
        "round": 1,
        "fixture": 1001,
        "opponent_team": 2,
        "was_home": True,
        "kickoff_time": "2026-08-21T19:00:00Z",
        "minutes": 90,
        "total_points": 6,
        "goals_scored": 0,
        "assists": 0,
        "clean_sheets": 1,
        "goals_conceded": 0,
        "bonus": 2,
        "bps": 30,
        "influence": "20.0",
        "creativity": "0.0",
        "threat": "0.0",
        "ict_index": "2.0",
        "expected_goals": "0.00",
        "expected_assists": "0.00",
        "expected_goal_involvements": "0.00",
        "expected_goals_conceded": "0.80",
        "value": 55,
        "selected": 500000,
        "transfers_in": 1000,
        "transfers_out": 500,
    },
]
