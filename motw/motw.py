import time

import polars as pl
import typer
from rich.progress import Progress
from typing_extensions import Annotated

from .api import get_league_standings, get_manager_details


# This is the CLI tool entry point.
def managers_of_the_week(
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
        increment = 100 / 2
        task = progress.add_task(
            f"[green]Loading standings for {league_id}...",
            total=100,
        )
        df = load_standings(league_id, dev_mode=dev_mode)
        progress.update(
            task,
            advance=increment,
            description="[green]Finding current gameweek...",
        )
        gameweek_id = find_current_gameweek(df["id"][0])
        progress.update(
            task,
            advance=increment,
            description=f"[green]Completed in {time.time() - start_time:.2f} seconds",
        )


def load_standings(
    league_id: str,
    *,
    dev_mode: bool = False,
) -> pl.DataFrame:
    """
    Load the league's current standings from the API.

    If dev mode is enabled, the function will try to load the standings from a local
    file at `/tmp/standings-{league_id}.parquet`. If the file does not exist, it will
    load from the API and save the file.

    :param league_id: The league ID.
    :param dev_mode (optional): Turn on development mode to enable writing of temporary
    files.

    :return: A DataFrame with the current standings.
    """
    tmp_file = f"/tmp/standings-{league_id}.parquet"
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
