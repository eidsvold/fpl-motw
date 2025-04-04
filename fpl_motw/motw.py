import os
import time

import polars as pl
import typer
from rich.progress import Progress
from typing_extensions import Annotated

from fpl_motw.api import (
    get_league_standings,
    get_manager_details,
    get_manager_gameweek_picks,
)


# This is the CLI tool entry point.
def manager_of_the_week(
    league_id: Annotated[
        str,
        typer.Option("--league", "-l", help="The ID of the league."),
    ],
    output_dir: Annotated[
        str,
        typer.Option(
            "--output-dir",
            help="""
            The directory to save the output files. Defaults to the current directory.
            """,
        ),
    ] = ".",
    dev_mode: Annotated[
        bool,
        typer.Option(
            "--dev-mode",
            help="""
            Turn on development mode. This will enable writing of temporary files.
            """,
        ),
    ] = False,
):
    start_time = time.time()
    with Progress() as progress:
        increment = 100 / 4
        task = progress.add_task(f"[green]Loading league results...", total=100)
        df = load_current_league_results(league_id, dev_mode=dev_mode)

        progress.update(
            task,
            advance=increment,
            description="[green]Finding current gameweek...",
        )
        gameweek_id = find_current_gameweek(df["entry"][0])

        progress.update(
            task,
            advance=increment,
            description=f"[green]Calcualting net top managers...",
        )
        df = net_managers_of_the_week(
            df, gameweek_id, limit=10, dev_mode=dev_mode, league_id=league_id
        )

        progress.update(
            task,
            advance=increment,
            description="[green]Writing results to file...",
        )
        filename = f"{league_id}-motw-gw-{gameweek_id}.csv"
        path = os.path.join(output_dir, filename)
        pretty_cols = {
            "entry": "Manager ID",
            "player_name": "Manager",
            "entry_name": "Team",
            "rank": "League Rank",
            "event_total": "GW Points",
            "transfer_cost": "GW Transfer Cost",
            "net_event_total": "GW Net Points",
            "web_link": "Web Link",
        }
        df = df.select(pretty_cols.keys()).rename(pretty_cols)
        df.write_csv(path, separator=";", include_bom=True)

        progress.update(
            task,
            completed=100,
            description=f"[green]Completed in {time.time() - start_time:.2f} seconds",
        )

    with pl.Config(tbl_cols=len(df.columns), tbl_rows=len(df)):
        typer.echo(f"Manager of the Week - GW{gameweek_id} -- league {league_id}:")
        typer.echo(df)


def load_current_league_results(
    league_id: str,
    *,
    dev_mode: bool = False,
) -> pl.DataFrame:
    """
    Load the league's current results from the API.

    If dev mode is enabled, the function will try to load the results from a local file
    at `/tmp/results-{league_id}.parquet`. If the file does not exist, it will load from
    the API and save the file.

    :param league_id: The league ID.
    :param dev_mode (optional): Turn on development mode to enable writing of temporary
    files.

    :return: A DataFrame with the results, ordered by highest gross score.
    """

    tmp_file = f"/tmp/{league_id}-current-results.parquet"
    # if dev mode is enabled, try to load the standings from local temp file
    if dev_mode:
        try:
            df = pl.read_parquet(tmp_file)
            return df
        except FileNotFoundError:
            pass

    standings = []
    page = 1
    has_next = True

    while has_next:
        response = get_league_standings(league_id, page=page)
        standings += response["standings"]["results"]
        has_next = response["standings"]["has_next"]
        page += 1

    df = pl.DataFrame(standings).sort("event_total", descending=True)

    # if dev mode is enabled, save the standings to local temp file
    if dev_mode:
        df.write_parquet(tmp_file)

    return df


def find_current_gameweek(manager_id: str) -> int:
    """
    Find the current gameweek from a manager's details.

    :param manager_id: The manager ID.

    :return: The current gameweek.
    """
    response = get_manager_details(manager_id)
    return response["current_event"]


def net_managers_of_the_week(
    df: pl.DataFrame,
    gameweek_id: int,
    *,
    hits: int = 4,
    limit: int = 10,
    dev_mode: bool = False,
    league_id: str = None,  # required if dev_mode is True
):
    """
    Calculate the top net managers of the week and return the top `limit` managers.
    The net score is calculated by subtracting the transfer cost from the event total.
    It will start from the highest event total and work downwards until it finds a manager
    with a transfer cost of 0 and the limit is reached.

    If dev mode is enabled, the function will try to load the results from a local file
    at `/tmp/{league_id}-motw-gw-{gameweek_id}.parquet`. If the file does not exist, it
    will load from the API and save the file.

    :param df: The DataFrame with the managers results.
    :param gameweek_id: The gameweek ID.
    :param limit (optional): The number of managers to return.
    :param dev_mode (optional): Turn on development mode to enable writing of temporary
    files.
    :param league_id (optional): The league ID. Required if `dev_mode` is True.

    :return: A DataFrame with the top managers of the week.
    """

    tmp_file = f"/tmp/{league_id}-motw-gw-{gameweek_id}.parquet"
    # if dev mode is enabled, try to load the standings from local temp file
    if dev_mode:
        try:
            df = pl.read_parquet(tmp_file)
            return df
        except FileNotFoundError:
            pass

    lowest_cost = 2**31 - 1
    lowest_score = 2**31 - 1
    top_df = df.head(0).with_columns(
        pl.lit(0).cast(pl.Int64).alias("transfer_cost"),
        pl.lit(0).cast(pl.Int64).alias("net_event_total"),
    )

    for row in df.iter_rows(named=True):
        response = get_manager_gameweek_picks(row["entry"], gameweek_id)
        cost = response["entry_history"]["event_transfers_cost"]
        if cost < lowest_cost:
            lowest_cost = cost
        net_score = row["event_total"] - cost
        if net_score < lowest_score:
            lowest_score = net_score
        row_df = pl.DataFrame(
            {
                **row,
                "transfer_cost": cost,
                "net_event_total": net_score,
            }
        )
        top_df = top_df.vstack(row_df)
        if len(top_df) >= limit and lowest_cost == 0:
            break

    # in case there are multiple managers tied for the lowest score
    for row in df.filter(pl.col("event_total") == lowest_score).iter_rows(named=True):
        if not top_df.filter(pl.col("entry") == row["entry"]).is_empty():
            # already added this manager in the previous loop
            continue
        response = get_manager_gameweek_picks(row["entry"], gameweek_id)
        cost = response["entry_history"]["event_transfers_cost"]
        net_score = row["event_total"] - cost
        if net_score < lowest_score:
            break
        row_df = pl.DataFrame(
            {
                **row,
                "transfer_cost": cost,
                "net_event_total": net_score,
            }
        )
        top_df = top_df.vstack(row_df)

    top_df = top_df.sort("net_event_total", descending=True)
    top_df = add_event_web_link(top_df, gameweek_id)
    if dev_mode:
        top_df.write_parquet(tmp_file)

    return top_df


def add_event_web_link(df: pl.DataFrame, gameweek_id: int) -> pl.DataFrame:
    """
    Add the web link to each manager's gameweek picks.

    :param df: The DataFrame with the managers results.
    :param event: The gameweek ID.

    :return: A DataFrame with the web link added as column `web_link`.
    """

    df = df.with_columns(
        pl.format(
            "https://fantasy.premierleague.com/entry/{}/event/{}",
            pl.col("entry"),
            pl.lit(gameweek_id),
        ).alias("web_link")
    )
    return df


__all__ = ["manager_of_the_week"]
