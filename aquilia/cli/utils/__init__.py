"""Color utilities for CLI output."""

import click


def success(message: str) -> None:
    """Print success message in green."""
    click.echo(click.style(message, fg='green'))


def error(message: str) -> None:
    """Print error message in red."""
    click.echo(click.style(message, fg='red'))


def warning(message: str) -> None:
    """Print warning message in yellow."""
    click.echo(click.style(message, fg='yellow'))


def info(message: str) -> None:
    """Print info message in blue."""
    click.echo(click.style(message, fg='blue'))


def dim(message: str) -> None:
    """Print dimmed message."""
    click.echo(click.style(message, dim=True))


def bold(message: str) -> str:
    """Return bold text."""
    return click.style(message, bold=True)
