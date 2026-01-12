"""Facebook API client with retry logic using official SDK."""

import asyncio
import logging
from pathlib import Path
from typing import Any

import facebook
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


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
    """Client for interacting with Facebook Graph API using official SDK."""

    def __init__(self, access_token: str, api_version: str = "2.12") -> None:
        """Initialize Facebook API client.

        Args:
            access_token: Facebook API access token
            api_version: Graph API version to use (format: X.Y where X is 1-9, e.g., "2.12")
        """
        self.access_token = access_token
        self.api_version = api_version
        self._graph: facebook.GraphAPI | None = None

    async def __aenter__(self) -> "FacebookAPIClient":
        """Async context manager entry."""
        self._graph = facebook.GraphAPI(
            access_token=self.access_token, version=self.api_version
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        self._graph = None

    @property
    def graph(self) -> facebook.GraphAPI:
        """Get the GraphAPI instance.

        Returns:
            The facebook.GraphAPI instance

        Raises:
            RuntimeError: If client is used outside of async context manager
        """
        if self._graph is None:
            raise RuntimeError("Client must be used within async context manager")
        return self._graph

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

        def _blocking_create() -> dict[str, Any]:
            return self.graph.put_object(
                parent_object="me", connection_name="albums", name=title
            )

        try:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, _blocking_create)
            album_id = result["id"]
            logger.info(f"Created album '{title}' with ID: {album_id}")
            return album_id
        except facebook.GraphAPIError as e:
            self._handle_graph_error(e, f"creating album '{title}'")
            raise  # Never reached, but helps type checker

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

        def _blocking_upload() -> dict[str, Any]:
            with photo_path.open("rb") as photo_file:
                return self.graph.put_photo(
                    image=photo_file, album_path=f"{album_id}/photos"
                )

        try:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, _blocking_upload)
            photo_id = result["id"]
            logger.debug(
                f"Uploaded {photo_path.name} to album {album_id}, photo ID: {photo_id}"
            )
            return photo_id
        except facebook.GraphAPIError as e:
            self._handle_graph_error(e, f"uploading {photo_path.name}")
            raise  # Never reached, but helps type checker

    def _handle_graph_error(self, error: facebook.GraphAPIError, context: str) -> None:
        """Handle Graph API errors and convert to appropriate exceptions.

        Args:
            error: The GraphAPIError to handle
            context: Description of what operation failed

        Raises:
            RateLimitError: If rate limit is exceeded
            ServerError: If server error occurs
            FacebookAPIError: For other API errors
        """
        error_code = getattr(error, "code", None)
        error_message = str(error)

        # Check for rate limiting
        if (
            error_code in [1, 2, 4, 17, 32, 613]
            or "rate limit" in error_message.lower()
        ):
            logger.warning(f"Rate limit exceeded while {context}, will retry")
            raise RateLimitError(f"Facebook API rate limit exceeded: {error_message}")

        # Check for server errors
        if (
            error_code is not None and error_code >= 500
        ) or "server error" in error_message.lower():
            logger.warning(f"Server error while {context}, will retry")
            raise ServerError(f"Facebook API server error: {error_message}")

        # Other errors - don't retry
        error_msg = f"Facebook API error while {context}: {error_message}"
        logger.error(error_msg)
        raise FacebookAPIError(error_msg) from error
