from io import BytesIO
from typing import Tuple

import polars as pl
import requests

from ..integrations.fpl_api import FantasyPremierLeagueAPI


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

    def generate_report(
        self,
        league_id: str,
        *,
        limit: int = 10,
    ) -> Tuple[str, BytesIO]:
        """
        Generate the Manager of the Week report for a given league.
        """

        standings = self._compile_league_standings(league_id).sort(
            "event_total", descending=True
        )
        current_gw = self.fpl_api.get_manager_details(standings["entry"][0])[
            "current_event"
        ]

        limit = len(standings) if limit > len(standings) else limit
        transfers_cost = []
        n_zero_transfers = 0
        i = 0
        while (
            n_zero_transfers < limit
        ):  # Find at least `limit` managers with zero transfers
            manager_id = standings["entry"][i]
            picks = self.fpl_api.get_manager_gameweek_picks(manager_id, current_gw)
            cost = picks["entry_history"]["event_transfers_cost"]
            if cost == 0:
                n_zero_transfers += 1
            transfers_cost.append(cost)
            i += 1

        standings = (
            standings.slice(0, len(transfers_cost))
            .with_columns(pl.Series("transfers_cost", transfers_cost).cast(pl.Int64))
            .with_columns(
                (pl.col("event_total") - pl.col("transfers_cost")).alias(
                    "net_event_total"
                )
            )
            .sort("net_event_total", descending=True)
        )
        limit_score = standings["net_event_total"][
            limit - 1
        ]  # Include all tied at the limit
        standings = standings.filter(pl.col("net_event_total") >= limit_score)

        filename = f"fpl-motw-league-{league_id}-gw-{current_gw}.csv"
        buffer = BytesIO()
        self._prettify_report(standings, current_gw).write_csv(
            buffer, include_bom=True, separator=";"
        )
        buffer.seek(0)

        return filename, buffer

    def _compile_league_standings(self, league_id: str) -> pl.DataFrame:
        """
        Compile complete standings for a private classic league.
        """

        standings = []
        page = 1
        has_next = True
        validated = False

        while has_next:
            try:
                response = self.fpl_api.get_classic_league_standings(
                    league_id, page=page
                )

                # Only validate on the first page
                if not validated:
                    valid = response["league"]["league_type"] == "x"
                    if not valid:
                        raise InvalidLeagueError(
                            f"League ID {league_id} is not a private classic league"
                        )
                    validated = True

                standings.extend(response["standings"]["results"])

                has_next = response["standings"]["has_next"]
                page += 1

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 404:
                    raise LeagueNotFoundError(f"League ID {league_id} not found")
                raise e

        return pl.DataFrame(standings)

    def _prettify_report(
        self,
        standings: pl.DataFrame,
        gameweek_id: int,
    ) -> pl.DataFrame:
        """
        Prettify column names and add the web link to each manager's gameweek points.
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
