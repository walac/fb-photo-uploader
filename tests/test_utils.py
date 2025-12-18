"""Tests for utility functions."""

import pytest
from pathlib import Path

from fb_photo_uploader.utils import is_image_file, scan_albums
from fb_photo_uploader.models import Album


class TestIsImageFile:
    """Test image file detection."""

    def test_supported_image_formats(self, tmp_path: Path) -> None:
        """Test that supported image formats are recognized."""
        supported = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".heic"]

        for ext in supported:
            photo = tmp_path / f"test{ext}"
            photo.write_text("fake image")
            assert is_image_file(photo)

    def test_case_insensitive(self, tmp_path: Path) -> None:
        """Test that extension matching is case-insensitive."""
        photo = tmp_path / "test.JPG"
        photo.write_text("fake image")
        assert is_image_file(photo)

    def test_unsupported_formats(self, tmp_path: Path) -> None:
        """Test that unsupported formats are not recognized."""
        unsupported = [".txt", ".pdf", ".doc", ".mp4"]

        for ext in unsupported:
            file = tmp_path / f"test{ext}"
            file.write_text("fake content")
            assert not is_image_file(file)

    def test_directory_not_image(self, tmp_path: Path) -> None:
        """Test that directories are not considered image files."""
        dir_path = tmp_path / "test.jpg"
        dir_path.mkdir()
        assert not is_image_file(dir_path)


class TestScanAlbums:
    """Test album scanning functionality."""

    def test_scan_albums_success(self, temp_photos_dir: Path) -> None:
        """Test successful album scanning."""
        albums = scan_albums(temp_photos_dir)

        assert len(albums) == 2  # album1 and album2, empty_album is skipped

        # Check album1
        album1 = next(a for a in albums if a.title == "album1")
        assert len(album1.photos) == 2
        assert any(p.name == "photo1.jpg" for p in album1.photos)
        assert any(p.name == "photo2.png" for p in album1.photos)

        # Check album2
        album2 = next(a for a in albums if a.title == "album2")
        assert len(album2.photos) == 1
        assert album2.photos[0].name == "photo3.jpg"

    def test_scan_albums_empty_directory(self, tmp_path: Path) -> None:
        """Test scanning an empty directory."""
        albums = scan_albums(tmp_path)
        assert len(albums) == 0

    def test_scan_albums_no_subdirectories(self, tmp_path: Path) -> None:
        """Test scanning directory with only files, no subdirectories."""
        (tmp_path / "photo1.jpg").write_text("fake image")
        (tmp_path / "photo2.png").write_text("fake image")

        albums = scan_albums(tmp_path)
        assert len(albums) == 0

    def test_scan_albums_nonexistent_directory(self, tmp_path: Path) -> None:
        """Test scanning non-existent directory."""
        nonexistent = tmp_path / "nonexistent"

        with pytest.raises(FileNotFoundError):
            scan_albums(nonexistent)

    def test_scan_albums_file_instead_of_directory(self, tmp_path: Path) -> None:
        """Test scanning a file instead of directory."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("not a directory")

        with pytest.raises(NotADirectoryError):
            scan_albums(file_path)

    def test_scan_albums_skips_empty_albums(self, temp_photos_dir: Path) -> None:
        """Test that empty album directories are skipped."""
        albums = scan_albums(temp_photos_dir)

        # empty_album directory exists but should be skipped
        assert not any(a.title == "empty_album" for a in albums)

    def test_scan_albums_sorted_output(self, tmp_path: Path) -> None:
        """Test that albums and photos are sorted."""
        # Create albums in non-alphabetical order
        for album_name in ["zebra", "alpha", "mike"]:
            album_dir = tmp_path / album_name
            album_dir.mkdir()
            (album_dir / "photo1.jpg").write_text("fake")

        albums = scan_albums(tmp_path)

        # Albums should be sorted by title
        assert [a.title for a in albums] == ["alpha", "mike", "zebra"]


class TestAlbumModel:
    """Test Album data model."""

    def test_album_creation(self, tmp_path: Path) -> None:
        """Test creating a valid album."""
        photo = tmp_path / "photo.jpg"
        photo.write_text("fake")

        album = Album(title="Test Album", photos=[photo])

        assert album.title == "Test Album"
        assert len(album.photos) == 1
        assert album.photos[0] == photo

    def test_album_empty_title(self, tmp_path: Path) -> None:
        """Test that empty album title raises error."""
        photo = tmp_path / "photo.jpg"
        photo.write_text("fake")

        with pytest.raises(ValueError, match="title cannot be empty"):
            Album(title="", photos=[photo])

    def test_album_no_photos(self) -> None:
        """Test that album with no photos raises error."""
        with pytest.raises(ValueError, match="at least one photo"):
            Album(title="Test Album", photos=[])
