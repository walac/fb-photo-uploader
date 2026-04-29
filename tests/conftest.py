"""Pytest configuration and shared fixtures."""

import pytest
from pathlib import Path
from pytest_httpx import HTTPXMock


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

    Note: mock_successful_uploads assumes this exact layout (2 albums, 3 photos).
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


@pytest.fixture
def mock_successful_uploads(httpx_mock: HTTPXMock) -> HTTPXMock:
    """Mock successful album creation and photo uploads for the standard temp_photos_dir layout.

    Mocks 2 album creations (IDs 1001, 1002) and 3 photo uploads
    (2 for album 1001, 1 for album 1002).
    """
    httpx_mock.add_response(
        method="POST",
        url="https://graph.facebook.com/v22.0/me/albums",
        json={"id": "1001"},
        status_code=200,
    )
    httpx_mock.add_response(
        method="POST",
        url="https://graph.facebook.com/v22.0/me/albums",
        json={"id": "1002"},
        status_code=200,
    )
    httpx_mock.add_response(
        method="POST",
        url="https://graph.facebook.com/v22.0/1001/photos",
        json={"id": "photo_1_0"},
        status_code=200,
    )
    httpx_mock.add_response(
        method="POST",
        url="https://graph.facebook.com/v22.0/1001/photos",
        json={"id": "photo_1_1"},
        status_code=200,
    )
    httpx_mock.add_response(
        method="POST",
        url="https://graph.facebook.com/v22.0/1002/photos",
        json={"id": "photo_2_0"},
        status_code=200,
    )
    return httpx_mock
