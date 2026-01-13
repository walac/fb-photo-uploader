"""White-box tests for uploader concurrency control."""

import asyncio
import pytest
from pathlib import Path
from unittest.mock import patch
from pytest_httpx import HTTPXMock

from fb_photo_uploader.api_client import FacebookAPIClient
from fb_photo_uploader.uploader import PhotoUploader
from fb_photo_uploader.models import Album


@pytest.mark.asyncio
class TestPhotoUploader:
    """Test photo uploader functionality."""

    async def test_concurrent_upload_limit(
        self, access_token: str, temp_photos_dir: Path, httpx_mock: HTTPXMock
    ) -> None:
        """Test that concurrent uploads respect the semaphore limit."""
        # Track concurrent executions
        max_concurrent = 0
        current_concurrent = 0
        lock = asyncio.Lock()

        async def mock_upload(*args, **kwargs):
            nonlocal max_concurrent, current_concurrent
            async with lock:
                current_concurrent += 1
                max_concurrent = max(max_concurrent, current_concurrent)

            # Simulate upload delay
            await asyncio.sleep(0.01)

            async with lock:
                current_concurrent -= 1

            return "photo_123"

        # Create album with many photos
        photos = [temp_photos_dir / "album1" / f"photo{i}.jpg" for i in range(20)]
        for photo in photos:
            photo.write_bytes(b"fake image")

        album = Album(title="Test Album", photos=photos)

        # Mock album creation
        httpx_mock.add_response(
            method="POST",
            url="https://graph.facebook.com/v22.0/me/albums",
            json={"id": "album_123"},
            status_code=200,
        )

        async with FacebookAPIClient(access_token) as client:
            uploader = PhotoUploader(client, max_concurrent_uploads=5)

            # Patch the upload method to track concurrency
            with patch.object(client, "upload_photo", side_effect=mock_upload):
                await uploader.upload_albums([album])

        # Verify that we never exceeded the limit
        assert max_concurrent <= 5
        # Verify that we actually had concurrent uploads
        assert max_concurrent > 1

    async def test_upload_albums_success(
        self, access_token: str, temp_photos_dir: Path, httpx_mock: HTTPXMock
    ) -> None:
        """Test successful upload of multiple albums."""
        # Get albums from temp directory
        from fb_photo_uploader.utils import scan_albums

        albums = scan_albums(temp_photos_dir)

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

        # Mock photo uploads for album_1 (2 photos)
        for i in range(2):
            httpx_mock.add_response(
                method="POST",
                url="https://graph.facebook.com/v22.0/album_1/photos",
                json={"id": f"photo_1_{i}"},
                status_code=200,
            )

        # Mock photo uploads for album_2 (1 photo)
        httpx_mock.add_response(
            method="POST",
            url="https://graph.facebook.com/v22.0/album_2/photos",
            json={"id": "photo_2_0"},
            status_code=200,
        )

        async with FacebookAPIClient(access_token) as client:
            uploader = PhotoUploader(client, max_concurrent_uploads=10)
            results = await uploader.upload_albums(albums)

        # Should have uploaded 3 photos total (2 from album1, 1 from album2)
        assert len(results) == 3
        assert all(r.success for r in results)

    async def test_upload_album_creation_failure(
        self, access_token: str, temp_photos_dir: Path, httpx_mock: HTTPXMock
    ) -> None:
        """Test handling of album creation failure."""
        from fb_photo_uploader.utils import scan_albums

        albums = scan_albums(temp_photos_dir)

        # Mock album creation failure for both albums
        httpx_mock.add_response(
            method="POST",
            url="https://graph.facebook.com/v22.0/me/albums",
            json={"error": {"message": "bad request", "code": 100}},
            status_code=400,
        )
        httpx_mock.add_response(
            method="POST",
            url="https://graph.facebook.com/v22.0/me/albums",
            json={"error": {"message": "bad request", "code": 100}},
            status_code=400,
        )

        async with FacebookAPIClient(access_token) as client:
            uploader = PhotoUploader(client)
            results = await uploader.upload_albums(albums)

        # All uploads should fail due to album creation failure
        assert all(not r.success for r in results)
        assert all(
            "Album creation failed" in r.error_message
            for r in results
            if r.error_message is not None
        )

    async def test_upload_photo_failure(
        self, access_token: str, temp_photos_dir: Path, httpx_mock: HTTPXMock
    ) -> None:
        """Test handling of individual photo upload failures."""
        from fb_photo_uploader.utils import scan_albums

        albums = scan_albums(temp_photos_dir)[:1]  # Just first album

        # Mock successful album creation
        httpx_mock.add_response(
            method="POST",
            url="https://graph.facebook.com/v22.0/me/albums",
            json={"id": "album_123"},
            status_code=200,
        )

        # Mock photo upload failures
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

        async with FacebookAPIClient(access_token) as client:
            uploader = PhotoUploader(client)
            results = await uploader.upload_albums(albums)

        # All photo uploads should fail
        assert all(not r.success for r in results)
        assert len(results) == 2  # album1 has 2 photos

    async def test_dry_run_mode(
        self, access_token: str, temp_photos_dir: Path, httpx_mock: HTTPXMock
    ) -> None:
        """Test dry-run mode doesn't make API calls."""
        from fb_photo_uploader.utils import scan_albums

        albums = scan_albums(temp_photos_dir)

        async with FacebookAPIClient(access_token) as client:
            uploader = PhotoUploader(client, dry_run=True)
            results = await uploader.upload_albums(albums)

            # No API calls should have been made
            assert len(httpx_mock.get_requests()) == 0

        # All results should be successful (simulated)
        assert all(r.success for r in results)
        assert all(r.photo_id == "dry_run_photo_id" for r in results)
