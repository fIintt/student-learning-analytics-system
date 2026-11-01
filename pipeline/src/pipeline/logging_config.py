import logging
from typing import TypedDict, get_type_hints

from rich import box
from rich.logging import RichHandler
from rich.table import Table
from rich.console import Console


class PipelineLogs(TypedDict):
    read: int
    duplicated: int
    rejected: int
    skipped: int
    loaded: int
    elapsed: float


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(name)s | %(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
    )


def log_summary(results: dict[str, PipelineLogs]) -> None:
    table = Table(title="Summary", title_style="bold", box=box.MINIMAL, expand=True)

    table.add_column("pipeline")

    for col in list(get_type_hints(PipelineLogs)):
        table.add_column(col, justify="right")

    for name, r in results.items():
        table.add_row(
            name,
            str(r["read"]),
            str(r["duplicated"]),
            f"[red]{r['rejected']}[/red]" if r["rejected"] else "0",
            str(r["skipped"]),
            f"[green]{r['loaded']}[/green]",
            f"{r['elapsed']:.2f}s",
        )

    Console().print(table)
