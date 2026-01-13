"""Facebook API client with retry logic using httpx for async HTTP calls."""

import logging
import mimetypes
from pathlib import Path
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

# Facebook Graph API base URL
GRAPH_API_BASE_URL = "https://graph.facebook.com"


class FacebookAPIError(Exception):
    """Base exception for Facebook API errors."""

    pass


class RateLimitError(FacebookAPIError):
    """Exception raised when hitting rate limits."""

    pass


class ServerError(FacebookAPIError):
    """Exception raised for 5xx server errors."""

    pass


class FacebookAPIClient:
    """Client for interacting with Facebook Graph API using httpx."""

    def __init__(self, access_token: str, api_version: str = "22.0") -> None:
        """Initialize Facebook API client.

        Args:
            access_token: Facebook API access token
            api_version: Graph API version to use (e.g., "22.0")
        """
        self.access_token = access_token
        self.api_version = api_version
        self._client: httpx.AsyncClient | None = None

    @property
    def base_url(self) -> str:
        """Get the base URL for API requests."""
        return f"{GRAPH_API_BASE_URL}/v{self.api_version}"

    async def __aenter__(self) -> "FacebookAPIClient":
        """Async context manager entry."""
        self._client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
        self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get the httpx AsyncClient instance.

        Returns:
            The httpx.AsyncClient instance

        Raises:
            RuntimeError: If client is used outside of async context manager
        """
        if self._client is None:
            raise RuntimeError("Client must be used within async context manager")
        return self._client

    @retry(
        retry=retry_if_exception_type((RateLimitError, ServerError)),
        wait=wait_exponential(multiplier=1, min=1, max=60),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    async def create_album(self, title: str) -> str:
        """Create a new Facebook album.

        Args:
            title: Album title

        Returns:
            Album ID

        Raises:
            FacebookAPIError: If album creation fails
            RateLimitError: If rate limit is exceeded
            ServerError: If server error occurs
        """
        url = f"{self.base_url}/me/albums"
        data = {
            "name": title,
            "access_token": self.access_token,
        }

        try:
            response = await self.client.post(url, data=data)
            result = self._parse_json_response(response, f"creating album '{title}'")

            if response.status_code >= 400:
                self._handle_error_response(response.status_code, result, f"creating album '{title}'")

            album_id = result["id"]
            logger.info(f"Created album '{title}' with ID: {album_id}")
            return album_id
        except httpx.RequestError as e:
            logger.warning(f"Network error while creating album '{title}', will retry: {e}")
            raise ServerError(f"Network error: {e}") from e

    @retry(
        retry=retry_if_exception_type((RateLimitError, ServerError)),
        wait=wait_exponential(multiplier=1, min=1, max=60),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    async def upload_photo(self, album_id: str, photo_path: Path) -> str:
        """Upload a photo to a Facebook album.

        Args:
            album_id: Album ID to upload to
            photo_path: Path to the photo file

        Returns:
            Photo ID

        Raises:
            FacebookAPIError: If photo upload fails
            RateLimitError: If rate limit is exceeded
            ServerError: If server error occurs
            FileNotFoundError: If photo file doesn't exist
        """
        if not photo_path.exists():
            raise FileNotFoundError(f"Photo file not found: {photo_path}")

        url = f"{self.base_url}/{album_id}/photos"

        try:
            # Detect MIME type from file extension
            mime_type = mimetypes.guess_type(photo_path)[0] or "application/octet-stream"
            # Read file into memory to avoid blocking the event loop during async upload
            content = photo_path.read_bytes()
            files = {"source": (photo_path.name, content, mime_type)}
            data = {"access_token": self.access_token}
            response = await self.client.post(url, data=data, files=files)

            result = self._parse_json_response(response, f"uploading {photo_path.name}")

            if response.status_code >= 400:
                self._handle_error_response(response.status_code, result, f"uploading {photo_path.name}")

            photo_id = result["id"]
            logger.debug(
                f"Uploaded {photo_path.name} to album {album_id}, photo ID: {photo_id}"
            )
            return photo_id
        except httpx.RequestError as e:
            logger.warning(f"Network error while uploading {photo_path.name}, will retry: {e}")
            raise ServerError(f"Network error: {e}") from e

    def _parse_json_response(
        self, response: httpx.Response, context: str
    ) -> dict[str, Any]:
        """Parse JSON response, handling non-JSON responses gracefully.

        Args:
            response: The httpx Response object
            context: Description of what operation was attempted

        Returns:
            Parsed JSON as a dictionary

        Raises:
            ServerError: If response is 5xx with non-JSON body
            FacebookAPIError: If response has invalid JSON for non-5xx status
        """
        try:
            return response.json()
        except ValueError:
            # Non-JSON response (e.g., HTML error page during outages)
            if response.status_code >= 500:
                logger.warning(f"Server returned non-JSON response while {context}, will retry")
                raise ServerError(
                    f"Server error {response.status_code}: {response.text[:200]}"
                )
            raise FacebookAPIError(
                f"Invalid API response while {context}: {response.text[:200]}"
            )

    def _handle_error_response(
        self, status_code: int, result: dict[str, Any], context: str
    ) -> None:
        """Handle error responses from the Graph API.

        Args:
            status_code: HTTP status code
            result: Response JSON body
            context: Description of what operation failed

        Raises:
            RateLimitError: If rate limit is exceeded
            ServerError: If server error occurs
            FacebookAPIError: For other API errors
        """
        error = result.get("error", {})
        error_code = error.get("code")
        error_message = error.get("message", str(result))

        # Check for rate limiting (various Facebook rate limit error codes)
        if error_code in [1, 2, 4, 17, 32, 613] or "rate limit" in error_message.lower():
            logger.warning(f"Rate limit exceeded while {context}, will retry")
            raise RateLimitError(f"Facebook API rate limit exceeded: {error_message}")

        # Check for server errors (5xx)
        if status_code >= 500 or "server error" in error_message.lower():
            logger.warning(f"Server error while {context}, will retry")
            raise ServerError(f"Facebook API server error: {error_message}")

        # Other errors - don't retry
        error_msg = f"Facebook API error while {context}: {error_message}"
        logger.error(error_msg)
        raise FacebookAPIError(error_msg)
