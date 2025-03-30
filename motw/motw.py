import typer
from typing_extensions import Annotated


def managers_of_the_week(
    league_id: Annotated[
        str,
        typer.Option("--league", "-l", help="The ID of the league."),
    ],
    output_dir: Annotated[
        str,
        typer.Option(
            "--output-dir",
            "-o",
            help="The directory to save the output files.",
        ),
    ] = "dist",
    debug: Annotated[
        bool,
        typer.Option(
            "--debug",
            "-d",
            help="Enable debug mode. This will enable logging and writing of temporary files.",
        ),
    ] = False,
):

    print(f"League ID: {league_id}")
    print(f"Output Directory: {output_dir}")
    print(f"Debug Mode: {debug}")
