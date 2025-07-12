from io import BytesIO
from typing import Tuple

import polars as pl
import requests

from ..external.fpl_api import FantasyPremierLeagueAPI


class LeagueNotFoundError(Exception):
    """Raised when a league cannot be found."""

    pass


class InvalidLeagueError(Exception):
    """Raised when the league is invalid."""

    pass


class ManagerOfTheWeek:
    """
    Class to handle the logic for generating the Manager of the Week report.
    """

    def __init__(self, fpl_api: FantasyPremierLeagueAPI):
        self.fpl_api = fpl_api

    def generate_report(self, league_id: str) -> Tuple[str, BytesIO]:
        """Generate the Manager of the Week report for a given league."""
        standings = self._get_league_standings(league_id)
        standings = self._filter_standings_by_threshold(standings)
        current_gameweek = self._get_current_gameweek(standings["entry"][0])
        standings = self._add_manager_picks_transfers_cost(standings, current_gameweek)
        standings = self._filter_net_top_managers(standings)
        standings = self._format_report(standings, current_gameweek)

        filename = f"fpl-motw-league-{league_id}-gameweek-{current_gameweek}.csv"
        buffer = BytesIO()
        standings.write_csv(buffer, include_bom=True, separator=";")
        buffer.seek(0)

        return filename, buffer

    def _get_league_standings(self, league_id: str) -> pl.DataFrame:
        """
        Get standings for a private classic league.

        Args:
            league_id: The FPL league ID to fetch standings for.

        Raises:
            LeagueNotFoundError: If the league does not exist.
            InvalidLeagueError: If the league is not classic and private.

        Returns:
            Dict: A dictionary containing league information and standings.
        """
        all_standings = []
        page = 1
        has_next = True
        validated = False

        while has_next:
            try:
                standings = self.fpl_api.get_classic_league_standings(
                    league_id, page=page
                )

                # Only validate on the first page
                if not validated:
                    valid = (
                        standings["league"]["league_type"] == "x"
                        and standings["league"]["code_privacy"] == "p"
                    )
                    if not valid:
                        raise InvalidLeagueError(
                            f"League ID {league_id} is not a private classic league"
                        )
                    validated = True

                # Add results from this page
                all_standings.extend(standings["standings"]["results"])

                # Check if there are more pages
                has_next = standings["standings"]["has_next"]
                page += 1

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 404:
                    raise LeagueNotFoundError(f"League ID {league_id} not found")
                raise e

        return pl.DataFrame(all_standings)

    def _get_current_gameweek(self, manager_id: str) -> int:
        """
        Get the current gameweek for a specific manager.

        Args:
            manager_id: The FPL manager ID.

        Returns:
            int: The current gameweek ID.
        """
        manager_details = self.fpl_api.get_manager_details(manager_id)
        return manager_details["current_event"]

    def _filter_standings_by_threshold(
        self,
        standings: pl.DataFrame,
        hits: int = 4,
    ) -> pl.DataFrame:
        """
        Get standings where the points are equal or above the threshold. The threshold is
        calculated as the maximum points in the current gameweek minus a set amount of hits.
        The cost of a hit is 4 points.

        Args:
            standings: The league standings DataFrame.
            hits: The number of hits to subtract from the top score (default is 4).

        Returns:
            pl.DataFrame: Filtered DataFrame with standings above the top score minus hits.
        """
        threshold = standings["event_total"].max() - (hits * 4)
        return standings.filter(pl.col("event_total") >= threshold)

    def _add_manager_picks_transfers_cost(
        self,
        standings: pl.DataFrame,
        gameweek_id: int,
    ) -> pl.DataFrame:
        """
        Add the transfer cost for each manager in the standings DataFrame.

        Args:
            standings: The league standings DataFrame.
            gameweek_id: The gameweek ID.

        Returns:
            pl.DataFrame: Updated DataFrame with transfer costs added.
        """
        transfers_cost = []
        for manager_id in standings["entry"]:
            picks = self.fpl_api.get_manager_gameweek_picks(manager_id, gameweek_id)
            cost = picks["entry_history"]["event_transfers_cost"]
            transfers_cost.append(cost)
        standings = standings.with_columns(
            pl.Series("transfers_cost", transfers_cost).cast(pl.Int64)
        )
        return standings

    def _filter_net_top_managers(
        self,
        standings: pl.DataFrame,
        limit: int = 10,
    ) -> pl.DataFrame:
        """
        Get the top managers of the week based on their net event total after accounting
        for transfers.

        Args:
            standings: The league standings DataFrame.
            limit: The number of top manager to return (default is 10).

        Returns:
            pl.DataFrame: A DataFrame with the top managers of the week.
        """
        if standings.height < limit:
            limit = standings.height
        standings = standings.with_columns(
            (pl.col("event_total") - pl.col("transfers_cost")).alias("net_event_total")
        )
        standings = standings.sort("net_event_total", descending=True)
        limit_score = standings["net_event_total"][limit - 1]
        return standings.filter(pl.col("net_event_total") >= limit_score)

    def _format_report(
        self,
        standings: pl.DataFrame,
        gameweek_id: int,
    ) -> pl.DataFrame:
        """
        Add the web link to each manager's gameweek picks.

        Args:
            standings: The DataFrame with the managers results.
            gameweek_id: The gameweek ID.

        Returns:
            pl.DataFrame: Updated DataFrame with the web link added as column `web_link`.
        """
        standings = standings.with_columns(
            pl.format(
                "https://fantasy.premierleague.com/entry/{}/event/{}",
                pl.col("entry"),
                pl.lit(gameweek_id),
            ).alias("web_link")
        )
        headers = {
            "entry_name": "Team",
            "player_name": "Manager",
            "event_total": "Gameweek Points",
            "transfers_cost": "Transfers Cost",
            "net_event_total": "Net Gameweek Points",
            "web_link": "Web Link",
        }
        standings = standings.select(headers.keys()).rename(headers)
        return standings
