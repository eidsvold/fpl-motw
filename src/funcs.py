import time

import polars as pl
import requests

base_url = "https://fantasy.premierleague.com/api"


def load_standings(league_id: str) -> pl.DataFrame:
    """
    Load the standings for a given league. League max size is 100k entries.

    :param league_id: The league ID.

    :return: A DataFrame with the columns `entry`, `entry_name`, `player_name`, `rank`, `total`, `event_total`.

    :raises ValueError: If the max page is reached. This is to avoid too large requests.
    """
    url = f"{base_url}/leagues-classic/{league_id}/standings"
    phase = 1
    page = 1
    max_page = 2_000  # 50 per page, so 100k entries as max
    standings = []

    has_next = True
    while has_next:
        if page > max_page:
            raise ValueError(f"Max page reached: {max_page}")

        time.sleep(0.05)  # make sure we don't get rate limited

        response = requests.get(url, params={"phase": phase, "page_standings": page})
        data = response.json()
        results = data.get("standings", {}).get("results", [])

        for result in results:
            standings.append(
                {
                    "entry_id": result["entry"],
                    "entry_name": result["entry_name"],
                    "player_name": result["player_name"],
                    "total_points": result["total"],
                    "event_points": result["event_total"],
                    "rank": result["rank"],
                }
            )

        has_next = data.get("standings", {}).get("has_next", False)
        page += 1

    return pl.DataFrame(standings)


def top_players_by_diff(df: pl.DataFrame, diff: int) -> pl.DataFrame:
    """
    Filter the top players in the standings by finding the highest score and filtering
    all players that are within `diff` points of the highest score. This is a more
    considerate approach than just filtering N top players, as N top players might have
    the same score but all have made hits, making the winner potentially someone outside
    of the top N.

    :param df: The DataFrame with the top players, in descending order.
    :param diff: The difference in points to the highest score.

    :return: A DataFrame with the top players.
    """
    highest = df["event_points"].max()
    return df.filter(pl.col("event_points") >= highest - diff).sort(
        "event_points", descending=True
    )


def add_transfer_cost(df: pl.DataFrame, event_id: int) -> pl.DataFrame:
    """
    Add the transfer cost for each entry in the DataFrame.

    :param df: The DataFrame with the entries.
    :param event: The event number.

    :return: A DataFrame with the transfer cost added as column `transfer_cost`.
    """

    additional = []
    for row in df.iter_rows(named=True):
        entry_id = row["entry_id"]
        url = f"{base_url}/entry/{entry_id}/event/{event_id}/picks"
        response = requests.get(url)
        data = response.json()
        cost = data.get("entry_history", {}).get("event_transfers_cost")
        additional.append({"entry_id": entry_id, "transfer_cost": cost})

        time.sleep(0.05)  # make sure we don't get rate limited

    return df.join(pl.DataFrame(additional), on="entry_id")


def get_current_event(entry_id: str) -> int:
    url = f"{base_url}/entry/{entry_id}"
    response = requests.get(url)
    data = response.json()
    return data.get("current_event")


def net_top_players(df: pl.DataFrame, event_id: int) -> pl.DataFrame:
    """
    Calculate the net event points for each entry in the DataFrame.

    :param df: The DataFrame with the entries.
    :param event_id: The event number.

    :return: A DataFrame with the net event points added as column `net_event_points`.
    """

    df = add_transfer_cost(df, event_id)
    df = df.with_columns(
        net_event_points=pl.col("event_points") - pl.col("transfer_cost")
    )

    return df.sort("net_event_points", descending=True)


__all__ = [
    "load_standings",
    "top_players_by_diff",
    "add_transfer_cost",
    "get_current_event",
    "net_top_players",
]
