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
        task = progress.add_task(
            f"[green]Loading results for {league_id}...", total=None
        )
        df = load_current_league_results(league_id, dev_mode=dev_mode)

        gameweek_id = find_current_gameweek(df["entry"][0])
        progress.update(
            task,
            description=f"[green]Calculating GW{gameweek_id} MOTW...",
        )
        df = net_managers_of_the_week(
            df, gameweek_id, limit=10, dev_mode=dev_mode, league_id=league_id
        )

        filename = f"fpl-motw-{league_id}-gw{gameweek_id}.csv"
        path = os.path.join(output_dir, filename)
        progress.update(
            task,
            description=f"[green]Saving to {path}...",
        )
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

    typer.echo(f"Results saved to {path}")
    with pl.Config(tbl_cols=len(df.columns), tbl_rows=len(df)):
        typer.echo(f"FPL Manager of the Week - {league_id} - GW{gameweek_id}")
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

    :return: A DataFrame with the current league results.
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

        time.sleep(0.01)

    df = pl.DataFrame(standings)
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
    It assumes that the top manager hasn't made more than `hits` hits. One hit is 4 points.

    If dev mode is enabled, the function will try to load the results from a local file
    at `/tmp/motw-{league_id}-gw{gameweek_id}.parquet`. If the file does not exist, it
    will load from the API and save the file.

    :param df: The DataFrame with the managers results, sorted by highest gross points.
    :param gameweek_id: The gameweek ID.
    :param limit (optional): The number of managers to return.
    :param dev_mode (optional): Turn on development mode to enable writing of temporary
    files.
    :param league_id (optional): The league ID. Required if `dev_mode` is True.

    :return: A DataFrame with the top managers of the week.
    """

    tmp_file = f"/tmp/motw-{league_id}-gw{gameweek_id}.parquet"
    # if dev mode is enabled, try to load the standings from local temp file
    if dev_mode:
        try:
            df = pl.read_parquet(tmp_file)
            return df
        except FileNotFoundError:
            pass

    gross_highest = df["event_total"].max()
    df_motw = df.head(0).with_columns(
        pl.lit(0).cast(pl.Int64).alias("transfer_cost"),
        pl.lit(0).cast(pl.Int64).alias("net_event_total"),
    )

    for row in df.filter(pl.col("event_total") >= gross_highest - (hits * 4)).iter_rows(
        named=True
    ):
        response = get_manager_gameweek_picks(row["entry"], gameweek_id)
        transfers_cost = response["entry_history"]["event_transfers_cost"]
        net_event_total = row["event_total"] - transfers_cost
        df_motw = df_motw.vstack(
            pl.DataFrame(
                {
                    **row,
                    "transfer_cost": transfers_cost,
                    "net_event_total": net_event_total,
                }
            )
        )

        time.sleep(0.01)

    df_motw = df_motw.sort("net_event_total", descending=True)
    limit_score = df_motw["net_event_total"][limit - 1]
    df_motw = df_motw.filter(pl.col("net_event_total") >= limit_score)

    df_motw = add_event_web_link(df_motw, gameweek_id)
    if dev_mode:
        df_motw.write_parquet(tmp_file)

    return df_motw


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
