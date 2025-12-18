"""Command-line interface for Facebook photo uploader."""

import asyncio
import logging
from pathlib import Path

import typer
from rich.console import Console
from rich.logging import RichHandler

from fb_photo_uploader.api_client import FacebookAPIClient
from fb_photo_uploader.uploader import PhotoUploader
from fb_photo_uploader.utils import scan_albums

app = typer.Typer(
    name="fb-photo-uploader",
    help="Upload photos to Facebook albums in batch",
    add_completion=False,
)
console = Console()


def setup_logging(verbose: bool) -> None:
    """Configure logging with Rich handler.

    Args:
        verbose: Enable verbose (DEBUG) logging
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(rich_tracebacks=True, console=console)],
    )


async def async_upload(
    root_dir: Path,
    access_token: str,
    dry_run: bool,
    max_concurrent: int,
) -> int:
    """Async upload implementation.

    Args:
        root_dir: Root directory containing album subdirectories
        access_token: Facebook API access token
        dry_run: If True, simulate uploads without API calls
        max_concurrent: Maximum concurrent uploads

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    logger = logging.getLogger(__name__)

    try:
        # Scan for albums
        logger.info(f"Scanning for albums in: {root_dir}")
        albums = scan_albums(root_dir)

        if not albums:
            logger.warning("No albums found to upload")
            return 0

        total_photos = sum(len(album.photos) for album in albums)
        logger.info(f"Found {len(albums)} album(s) with {total_photos} photo(s) total")

        # Upload albums
        async with FacebookAPIClient(access_token) as api_client:
            uploader = PhotoUploader(
                api_client,
                max_concurrent_uploads=max_concurrent,
                dry_run=dry_run,
            )
            results = await uploader.upload_albums(albums)

        # Print summary
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful

        console.print("\n[bold]Upload Summary:[/bold]")
        console.print(f"  Total photos: {len(results)}")
        console.print(f"  [green]Successful: {successful}[/green]")
        console.print(f"  [red]Failed: {failed}[/red]")

        if failed > 0:
            console.print("\n[bold red]Failed uploads:[/bold red]")
            for result in results:
                if not result.success:
                    console.print(
                        f"  - {result.photo_path.name} ({result.album_title}): "
                        f"{result.error_message}"
                    )
            return 1

        return 0

    except Exception as e:
        logger.error(f"Upload failed: {e}", exc_info=True)
        return 1


@app.command()
def upload(
    root_dir: Path = typer.Argument(
        ...,
        help="Root directory containing album subdirectories",
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
    ),
    access_token: str = typer.Option(
        None,
        "--access-token",
        "-t",
        envvar="FB_ACCESS_TOKEN",
        help="Facebook API access token (or set FB_ACCESS_TOKEN env var)",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Simulate uploads without making API calls",
    ),
    max_concurrent: int = typer.Option(
        10,
        "--max-concurrent",
        "-c",
        min=1,
        max=50,
        help="Maximum number of concurrent uploads",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging",
    ),
) -> None:
    """Upload photos to Facebook albums.

    Scans ROOT_DIR for subdirectories. Each subdirectory becomes an album
    with the subdirectory name as the album title. All image files in each
    subdirectory are uploaded to the corresponding album.
    """
    setup_logging(verbose)

    if not dry_run and not access_token:
        console.print(
            "[red]Error: Facebook access token is required. "
            "Provide via --access-token or FB_ACCESS_TOKEN environment variable.[/red]"
        )
        raise typer.Exit(1)

    # Use a dummy token for dry run if not provided
    if dry_run and not access_token:
        access_token = "dry_run_token"

    exit_code = asyncio.run(
        async_upload(root_dir, access_token, dry_run, max_concurrent)
    )
    raise typer.Exit(exit_code)


if __name__ == "__main__":
    app()
