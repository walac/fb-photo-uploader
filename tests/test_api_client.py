"""White-box tests for API client retry logic."""

import pytest
import responses
from pathlib import Path

from fb_photo_uploader.api_client import (
    FacebookAPIClient,
    FacebookAPIError,
    RateLimitError,
    ServerError,
)


@pytest.mark.asyncio
class TestFacebookAPIClient:
    """Test Facebook API client functionality."""

    async def test_create_album_success(self, access_token: str) -> None:
        """Test successful album creation."""
        async with FacebookAPIClient(access_token) as client:
            with responses.RequestsMock() as rsps:
                rsps.add(
                    responses.POST,
                    "https://graph.facebook.com/v2.12/me/albums",
                    json={"id": "album_123"},
                    status=200,
                )

                album_id = await client.create_album("Test Album")

                assert album_id == "album_123"
                assert len(rsps.calls) == 1

    async def test_upload_photo_success(
        self, access_token: str, tmp_path: Path
    ) -> None:
        """Test successful photo upload."""
        # Create a test photo file
        photo_path = tmp_path / "test.jpg"
        photo_path.write_bytes(b"fake image data")

        async with FacebookAPIClient(access_token) as client:
            with responses.RequestsMock() as rsps:
                rsps.add(
                    responses.POST,
                    "https://graph.facebook.com/v2.12/album_123/photos",
                    json={"id": "photo_456"},
                    status=200,
                )

                photo_id = await client.upload_photo("album_123", photo_path)

                assert photo_id == "photo_456"
                assert len(rsps.calls) == 1

    async def test_upload_photo_file_not_found(
        self, access_token: str, tmp_path: Path
    ) -> None:
        """Test photo upload with non-existent file."""
        photo_path = tmp_path / "nonexistent.jpg"

        async with FacebookAPIClient(access_token) as client:
            with pytest.raises(FileNotFoundError):
                await client.upload_photo("album_123", photo_path)

    async def test_rate_limit_retry(self, access_token: str) -> None:
        """Test retry mechanism for rate limit errors."""
        async with FacebookAPIClient(access_token) as client:
            with responses.RequestsMock() as rsps:
                # First two calls return rate limit error, third succeeds
                rsps.add(
                    responses.POST,
                    "https://graph.facebook.com/v2.12/me/albums",
                    json={"error": {"message": "rate limit", "code": 4}},
                    status=400,
                )
                rsps.add(
                    responses.POST,
                    "https://graph.facebook.com/v2.12/me/albums",
                    json={"error": {"message": "rate limit", "code": 4}},
                    status=400,
                )
                rsps.add(
                    responses.POST,
                    "https://graph.facebook.com/v2.12/me/albums",
                    json={"id": "album_123"},
                    status=200,
                )

                album_id = await client.create_album("Test Album")

                assert album_id == "album_123"
                assert len(rsps.calls) == 3

    async def test_server_error_retry(self, access_token: str) -> None:
        """Test retry mechanism for server errors."""
        async with FacebookAPIClient(access_token) as client:
            with responses.RequestsMock() as rsps:
                # First call returns 500, second succeeds
                rsps.add(
                    responses.POST,
                    "https://graph.facebook.com/v2.12/me/albums",
                    json={"error": {"message": "server error", "code": 500}},
                    status=500,
                )
                rsps.add(
                    responses.POST,
                    "https://graph.facebook.com/v2.12/me/albums",
                    json={"id": "album_123"},
                    status=200,
                )

                album_id = await client.create_album("Test Album")

                assert album_id == "album_123"
                assert len(rsps.calls) == 2

    async def test_max_retries_exceeded(self, access_token: str) -> None:
        """Test that retries stop after max attempts."""
        async with FacebookAPIClient(access_token) as client:
            with responses.RequestsMock() as rsps:
                # Always return rate limit error - only need 5 (initial + 4 retries)
                for _ in range(5):
                    rsps.add(
                        responses.POST,
                        "https://graph.facebook.com/v2.12/me/albums",
                        json={"error": {"message": "rate limit", "code": 4}},
                        status=400,
                    )

                with pytest.raises(RateLimitError):
                    await client.create_album("Test Album")

                # Should attempt 5 times (initial + 4 retries)
                assert len(rsps.calls) == 5

    async def test_permanent_error_no_retry(self, access_token: str) -> None:
        """Test that permanent errors (4xx except rate limit) don't retry."""
        async with FacebookAPIClient(access_token) as client:
            with responses.RequestsMock() as rsps:
                rsps.add(
                    responses.POST,
                    "https://graph.facebook.com/v2.12/me/albums",
                    json={"error": {"message": "bad request", "code": 100}},
                    status=400,
                )

                with pytest.raises(FacebookAPIError):
                    await client.create_album("Test Album")

                # Should only attempt once (no retry for non-rate-limit 400)
                assert len(rsps.calls) == 1

    async def test_client_context_manager_error(self, access_token: str) -> None:
        """Test that client raises error when used outside context manager."""
        client = FacebookAPIClient(access_token)

        with pytest.raises(RuntimeError, match="async context manager"):
            await client.create_album("Test Album")
