"""Pytest configuration and shared fixtures."""

import pytest
from pathlib import Path
import tempfile
import shutil


@pytest.fixture
def temp_photos_dir(tmp_path: Path) -> Path:
    """Create a temporary directory structure with test photos.

    Structure:
        temp_dir/
            album1/
                photo1.jpg
                photo2.png
            album2/
                photo3.jpg
            empty_album/
            not_a_dir.txt
    """
    # Create album directories
    album1 = tmp_path / "album1"
    album1.mkdir()
    (album1 / "photo1.jpg").write_text("fake jpg content")
    (album1 / "photo2.png").write_text("fake png content")

    album2 = tmp_path / "album2"
    album2.mkdir()
    (album2 / "photo3.jpg").write_text("fake jpg content")

    # Empty album directory
    empty_album = tmp_path / "empty_album"
    empty_album.mkdir()

    # Non-directory file
    (tmp_path / "not_a_dir.txt").write_text("not a directory")

    return tmp_path


@pytest.fixture
def access_token() -> str:
    """Return a fake access token for testing."""
    return "test_access_token_123"
