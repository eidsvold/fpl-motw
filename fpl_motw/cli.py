import typer

from fpl_motw.motw import manager_of_the_week

app = typer.Typer()
app.command()(manager_of_the_week)


if __name__ == "__main__":
    app()
