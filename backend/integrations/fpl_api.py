from typing import Dict

import requests


class FantasyPremierLeagueAPI:
    """
    A class to interact with the Fantasy Premier League API.
    """

    def __init__(self, base_url: str = "https://fantasy.premierleague.com/api"):
        self.base_url = base_url

    def get_classic_league_standings(
        self,
        league_id: str,
        page: int = 1,
        phase: int = 1,
    ) -> Dict:
        """
        Get the standings of a classic league.

        Args:
            league_id (str): The ID of the league.
            page (int): The page number for paginated results. Defaults to 1.
            phase (int): The phase to filter by. Defaults to 1.

        Returns:
            Dict: League standings as returned by the FPL API.
        """
        url = f"{self.base_url}/leagues-classic/{league_id}/standings/"
        response = requests.get(url, params={"page_standings": page, "phase": phase})
        response.raise_for_status()
        return response.json()

    def get_manager_details(self, manager_id: str) -> Dict:
        """
        Get details of a specific manager.

        Args:
            manager_id (str): The ID of the manager.

        Returns:
            Dict: Manager details as returned by the FPL API.
        """
        url = f"{self.base_url}/entry/{manager_id}"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()

    def get_manager_gameweek_picks(self, manager_id: str, gameweek_id: int) -> Dict:
        """
        Get the gameweek picks for a specific manager.

        Args:
            manager_id (str): The ID of the manager.
            gameweek_id (int): The ID of the gameweek.
        Returns:
            Dict: Gameweek picks as returned by the FPL API.
        """
        url = f"{self.base_url}/entry/{manager_id}/event/{gameweek_id}/picks"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
