from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from pokedex_completer_gen5.saveio.gen5_save import build_save_output, write_save_report

app = typer.Typer(help="Generation 5 Living Dex completer.")
console = Console()


@app.command()
def version() -> None:
    """Print package version."""
    from pokedex_completer_gen5 import __version__

    console.print(f"pokedex-completer-gen5 {__version__}")


@app.command("inspect-save")
def inspect_save(
    save_path: Path = typer.Argument(..., help="Path to Gen 5 save file."),
    game: str = typer.Option("white", help="black, white, black2, or white2."),
    copy: str = typer.Option("auto", help="auto, 0, or 1."),
) -> None:
    """Read a Gen 5 save and print physical party/PC extraction plus planner status."""
    console.print(build_save_output(save_path, game, copy, "markdown"))


@app.command("report-living-dex")
def report_living_dex(
    save_path: Path = typer.Argument(..., help="Path to Gen 5 save file."),
    game: str = typer.Option("white", help="black, white, black2, or white2."),
    copy: str = typer.Option("auto", help="auto, 0, or 1."),
    output: Path | None = typer.Option(None, help="Optional report output path."),
    format: str = typer.Option("markdown", help="markdown or json."),
) -> None:
    """Generate a read-only Living Dex report from a Gen 5 save file."""
    output_path, report = write_save_report(save_path, game, copy, output, format)
    console.print(report)
    console.print(f"[green]Report written to:[/green] {output_path}")


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", help="REST API bind host."),
    port: int = typer.Option(8787, help="REST API bind port."),
) -> None:
    """Run the local REST API skeleton."""
    import uvicorn

    uvicorn.run("pokedex_completer_gen5.server.rest:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    app()
