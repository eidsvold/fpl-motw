from typing import Dict

import requests

base_url = "https://fantasy.premierleague.com/api"


def get_manager_details(manager_id: str) -> Dict:
    url = f"{base_url}/entry/{manager_id}"
    response = requests.get(url)
    return response.json()


def get_league_standings(league_id: str, page: int = 1, phase: int = 1) -> Dict:
    url = f"{base_url}/leagues-classic/{league_id}/standings"
    response = requests.get(url, params={"page_standings": page, "phase": phase})
    return response.json()


def url_league_standings(league_id: str) -> str:
    return f"{base_url}/leagues-classic/{league_id}/standings"


def url_manager_details(manager_id: str) -> str:
    return f"{base_url}/entry/{manager_id}"


def url_manager_gameweek_picks(manager_id: str, gameweek_id: int) -> str:
    return f"{base_url}/entry/{manager_id}/event/{gameweek_id}/picks"
