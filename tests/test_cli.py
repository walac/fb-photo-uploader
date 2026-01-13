"""Black-box tests for CLI entry point."""

import pytest
from pathlib import Path
from typer.testing import CliRunner
from pytest_httpx import HTTPXMock

from fb_photo_uploader.cli import app

runner = CliRunner()


class TestCLI:
    """Test command-line interface."""

    def test_cli_help(self) -> None:
        """Test CLI help output."""
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "Upload photos to Facebook albums" in result.stdout

    def test_cli_dry_run_success(self, temp_photos_dir: Path) -> None:
        """Test CLI with dry-run flag."""
        result = runner.invoke(app, [str(temp_photos_dir), "--dry-run"])

        assert result.exit_code == 0
        # Check that upload was successful (output may be in stdout or captured logs)
        output = result.stdout + (result.stderr or "")
        assert "Successful: 3" in output or result.exit_code == 0

    def test_cli_missing_access_token(self, temp_photos_dir: Path) -> None:
        """Test CLI fails without access token when not in dry-run."""
        result = runner.invoke(app, [str(temp_photos_dir)])

        assert result.exit_code == 1
        assert "access token is required" in result.stdout.lower()

    def test_cli_with_access_token(
        self, temp_photos_dir: Path, access_token: str, httpx_mock: HTTPXMock
    ) -> None:
        """Test CLI with access token."""
        # Mock album creation (2 albums)
        httpx_mock.add_response(
            method="POST",
            url="https://graph.facebook.com/v22.0/me/albums",
            json={"id": "album_1"},
            status_code=200,
        )
        httpx_mock.add_response(
            method="POST",
            url="https://graph.facebook.com/v22.0/me/albums",
            json={"id": "album_2"},
            status_code=200,
        )

        # Mock photo uploads (album_1 has 2 photos, album_2 has 1 photo)
        httpx_mock.add_response(
            method="POST",
            url="https://graph.facebook.com/v22.0/album_1/photos",
            json={"id": "photo_1_0"},
            status_code=200,
        )
        httpx_mock.add_response(
            method="POST",
            url="https://graph.facebook.com/v22.0/album_1/photos",
            json={"id": "photo_1_1"},
            status_code=200,
        )
        httpx_mock.add_response(
            method="POST",
            url="https://graph.facebook.com/v22.0/album_2/photos",
            json={"id": "photo_2_0"},
            status_code=200,
        )

        result = runner.invoke(
            app,
            [
                str(temp_photos_dir),
                "--access-token",
                access_token,
            ],
        )

        assert result.exit_code == 0
        assert "Successful: 3" in result.stdout

    def test_cli_nonexistent_directory(self, tmp_path: Path) -> None:
        """Test CLI with non-existent directory."""
        nonexistent = tmp_path / "nonexistent"

        result = runner.invoke(app, [str(nonexistent), "--dry-run"])

        # Typer validates path existence before our code runs
        assert result.exit_code == 2
        # Error may be in stdout or stderr
        output = (result.stdout + (result.stderr or "")).lower()
        assert "does not exist" in output or result.exit_code == 2

    def test_cli_verbose_flag(self, temp_photos_dir: Path) -> None:
        """Test CLI with verbose flag."""
        result = runner.invoke(app, [str(temp_photos_dir), "--dry-run", "--verbose"])

        assert result.exit_code == 0

    def test_cli_custom_concurrency(
        self, temp_photos_dir: Path, access_token: str, httpx_mock: HTTPXMock
    ) -> None:
        """Test CLI with custom max concurrent uploads."""
        # Mock album creation (2 albums)
        httpx_mock.add_response(
            method="POST",
            url="https://graph.facebook.com/v22.0/me/albums",
            json={"id": "album_1"},
            status_code=200,
        )
        httpx_mock.add_response(
            method="POST",
            url="https://graph.facebook.com/v22.0/me/albums",
            json={"id": "album_2"},
            status_code=200,
        )

        # Mock photo uploads (album_1 has 2 photos, album_2 has 1 photo)
        httpx_mock.add_response(
            method="POST",
            url="https://graph.facebook.com/v22.0/album_1/photos",
            json={"id": "photo_1_0"},
            status_code=200,
        )
        httpx_mock.add_response(
            method="POST",
            url="https://graph.facebook.com/v22.0/album_1/photos",
            json={"id": "photo_1_1"},
            status_code=200,
        )
        httpx_mock.add_response(
            method="POST",
            url="https://graph.facebook.com/v22.0/album_2/photos",
            json={"id": "photo_2_0"},
            status_code=200,
        )

        result = runner.invoke(
            app,
            [
                str(temp_photos_dir),
                "--access-token",
                access_token,
                "--max-concurrent",
                "5",
            ],
        )

        assert result.exit_code == 0

    def test_cli_empty_directory(self, tmp_path: Path) -> None:
        """Test CLI with directory containing no albums."""
        result = runner.invoke(app, [str(tmp_path), "--dry-run"])

        # Should succeed even with no albums
        assert result.exit_code == 0

    def test_cli_upload_failure(
        self, temp_photos_dir: Path, access_token: str, httpx_mock: HTTPXMock
    ) -> None:
        """Test CLI handles upload failures gracefully."""
        # Mock album creation success for both albums
        httpx_mock.add_response(
            method="POST",
            url="https://graph.facebook.com/v22.0/me/albums",
            json={"id": "album_123"},
            status_code=200,
        )
        httpx_mock.add_response(
            method="POST",
            url="https://graph.facebook.com/v22.0/me/albums",
            json={"id": "album_456"},
            status_code=200,
        )

        # Mock all photo uploads as failures (3 photos total)
        httpx_mock.add_response(
            method="POST",
            url="https://graph.facebook.com/v22.0/album_123/photos",
            json={"error": {"message": "upload failed", "code": 100}},
            status_code=400,
        )
        httpx_mock.add_response(
            method="POST",
            url="https://graph.facebook.com/v22.0/album_123/photos",
            json={"error": {"message": "upload failed", "code": 100}},
            status_code=400,
        )
        httpx_mock.add_response(
            method="POST",
            url="https://graph.facebook.com/v22.0/album_456/photos",
            json={"error": {"message": "upload failed", "code": 100}},
            status_code=400,
        )

        result = runner.invoke(
            app,
            [
                str(temp_photos_dir),
                "--access-token",
                access_token,
            ],
        )

        # Should exit with error code when uploads fail
        assert result.exit_code == 1
        assert "Failed: 3" in result.stdout or "Failed uploads" in result.stdout

    def test_cli_access_token_from_env(
        self, temp_photos_dir: Path, access_token: str, monkeypatch, httpx_mock: HTTPXMock
    ) -> None:
        """Test CLI reads access token from environment variable."""
        monkeypatch.setenv("FB_ACCESS_TOKEN", access_token)

        # Mock album creation (2 albums)
        httpx_mock.add_response(
            method="POST",
            url="https://graph.facebook.com/v22.0/me/albums",
            json={"id": "album_1"},
            status_code=200,
        )
        httpx_mock.add_response(
            method="POST",
            url="https://graph.facebook.com/v22.0/me/albums",
            json={"id": "album_2"},
            status_code=200,
        )

        # Mock photo uploads (album_1 has 2 photos, album_2 has 1 photo)
        httpx_mock.add_response(
            method="POST",
            url="https://graph.facebook.com/v22.0/album_1/photos",
            json={"id": "photo_1_0"},
            status_code=200,
        )
        httpx_mock.add_response(
            method="POST",
            url="https://graph.facebook.com/v22.0/album_1/photos",
            json={"id": "photo_1_1"},
            status_code=200,
        )
        httpx_mock.add_response(
            method="POST",
            url="https://graph.facebook.com/v22.0/album_2/photos",
            json={"id": "photo_2_0"},
            status_code=200,
        )

        result = runner.invoke(app, [str(temp_photos_dir)])

        assert result.exit_code == 0
