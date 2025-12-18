"""Utility functions for the Facebook photo uploader."""

import logging
from pathlib import Path

from fb_photo_uploader.models import Album

logger = logging.getLogger(__name__)

# Supported image extensions
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".heic"}


def is_image_file(path: Path) -> bool:
    """Check if a file is a supported image format.

    Args:
        path: Path to the file to check

    Returns:
        True if the file is a supported image format, False otherwise
    """
    return path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS


def scan_albums(root_dir: Path) -> list[Album]:
    """Scan root directory for albums.

    Each subdirectory in the root is treated as an album, with its name
    as the album title. All image files in the subdirectory are collected
    as photos for that album.

    Args:
        root_dir: Root directory to scan

    Returns:
        List of Album objects

    Raises:
        FileNotFoundError: If root_dir doesn't exist
        NotADirectoryError: If root_dir is not a directory
    """
    if not root_dir.exists():
        raise FileNotFoundError(f"Root directory does not exist: {root_dir}")

    if not root_dir.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {root_dir}")

    albums: list[Album] = []

    for subdir in sorted(root_dir.iterdir()):
        if not subdir.is_dir():
            logger.debug(f"Skipping non-directory: {subdir}")
            continue

        photos = [photo for photo in sorted(subdir.iterdir()) if is_image_file(photo)]

        if photos:
            album = Album(title=subdir.name, photos=photos)
            albums.append(album)
            logger.info(
                f"Found album '{album.title}' with {len(album.photos)} photo(s)"
            )
        else:
            logger.warning(f"Skipping empty album directory: {subdir}")

    logger.info(f"Found {len(albums)} album(s) with photos")
    return albums
