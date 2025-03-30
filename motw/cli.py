import typer

from .motw import managers_of_the_week

app = typer.Typer()
app.command()(managers_of_the_week)


if __name__ == "__main__":
    app()
