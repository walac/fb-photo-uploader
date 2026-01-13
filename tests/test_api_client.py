"""White-box tests for API client retry logic."""

import pytest
from pathlib import Path
from pytest_httpx import HTTPXMock

from fb_photo_uploader.api_client import (
    FacebookAPIClient,
    FacebookAPIError,
    RateLimitError,
    ServerError,
)


@pytest.mark.asyncio
class TestFacebookAPIClient:
    """Test Facebook API client functionality."""

    async def test_create_album_success(
        self, access_token: str, httpx_mock: HTTPXMock
    ) -> None:
        """Test successful album creation."""
        httpx_mock.add_response(
            method="POST",
            url="https://graph.facebook.com/v22.0/me/albums",
            json={"id": "album_123"},
            status_code=200,
        )

        async with FacebookAPIClient(access_token) as client:
            album_id = await client.create_album("Test Album")

        assert album_id == "album_123"
        assert len(httpx_mock.get_requests()) == 1

    async def test_upload_photo_success(
        self, access_token: str, tmp_path: Path, httpx_mock: HTTPXMock
    ) -> None:
        """Test successful photo upload."""
        # Create a test photo file
        photo_path = tmp_path / "test.jpg"
        photo_path.write_bytes(b"fake image data")

        httpx_mock.add_response(
            method="POST",
            url="https://graph.facebook.com/v22.0/album_123/photos",
            json={"id": "photo_456"},
            status_code=200,
        )

        async with FacebookAPIClient(access_token) as client:
            photo_id = await client.upload_photo("album_123", photo_path)

        assert photo_id == "photo_456"
        assert len(httpx_mock.get_requests()) == 1

    async def test_upload_photo_file_not_found(
        self, access_token: str, tmp_path: Path
    ) -> None:
        """Test photo upload with non-existent file."""
        photo_path = tmp_path / "nonexistent.jpg"

        async with FacebookAPIClient(access_token) as client:
            with pytest.raises(FileNotFoundError):
                await client.upload_photo("album_123", photo_path)

    async def test_rate_limit_retry(
        self, access_token: str, httpx_mock: HTTPXMock
    ) -> None:
        """Test retry mechanism for rate limit errors."""
        # First two calls return rate limit error, third succeeds
        httpx_mock.add_response(
            method="POST",
            url="https://graph.facebook.com/v22.0/me/albums",
            json={"error": {"message": "rate limit", "code": 4}},
            status_code=400,
        )
        httpx_mock.add_response(
            method="POST",
            url="https://graph.facebook.com/v22.0/me/albums",
            json={"error": {"message": "rate limit", "code": 4}},
            status_code=400,
        )
        httpx_mock.add_response(
            method="POST",
            url="https://graph.facebook.com/v22.0/me/albums",
            json={"id": "album_123"},
            status_code=200,
        )

        async with FacebookAPIClient(access_token) as client:
            album_id = await client.create_album("Test Album")

        assert album_id == "album_123"
        assert len(httpx_mock.get_requests()) == 3

    async def test_server_error_retry(
        self, access_token: str, httpx_mock: HTTPXMock
    ) -> None:
        """Test retry mechanism for server errors."""
        # First call returns 500, second succeeds
        httpx_mock.add_response(
            method="POST",
            url="https://graph.facebook.com/v22.0/me/albums",
            json={"error": {"message": "server error", "code": 500}},
            status_code=500,
        )
        httpx_mock.add_response(
            method="POST",
            url="https://graph.facebook.com/v22.0/me/albums",
            json={"id": "album_123"},
            status_code=200,
        )

        async with FacebookAPIClient(access_token) as client:
            album_id = await client.create_album("Test Album")

        assert album_id == "album_123"
        assert len(httpx_mock.get_requests()) == 2

    async def test_max_retries_exceeded(
        self, access_token: str, httpx_mock: HTTPXMock
    ) -> None:
        """Test that retries stop after max attempts."""
        # Always return rate limit error - only need 5 (initial + 4 retries)
        for _ in range(5):
            httpx_mock.add_response(
                method="POST",
                url="https://graph.facebook.com/v22.0/me/albums",
                json={"error": {"message": "rate limit", "code": 4}},
                status_code=400,
            )

        async with FacebookAPIClient(access_token) as client:
            with pytest.raises(RateLimitError):
                await client.create_album("Test Album")

        # Should attempt 5 times (initial + 4 retries)
        assert len(httpx_mock.get_requests()) == 5

    async def test_permanent_error_no_retry(
        self, access_token: str, httpx_mock: HTTPXMock
    ) -> None:
        """Test that permanent errors (4xx except rate limit) don't retry."""
        httpx_mock.add_response(
            method="POST",
            url="https://graph.facebook.com/v22.0/me/albums",
            json={"error": {"message": "bad request", "code": 100}},
            status_code=400,
        )

        async with FacebookAPIClient(access_token) as client:
            with pytest.raises(FacebookAPIError):
                await client.create_album("Test Album")

        # Should only attempt once (no retry for non-rate-limit 400)
        assert len(httpx_mock.get_requests()) == 1

    async def test_client_context_manager_error(self, access_token: str) -> None:
        """Test that client raises error when used outside context manager."""
        client = FacebookAPIClient(access_token)

        with pytest.raises(RuntimeError, match="async context manager"):
            await client.create_album("Test Album")
