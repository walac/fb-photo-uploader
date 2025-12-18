"""Photo uploader with concurrency control."""

import asyncio
import logging
from pathlib import Path

from fb_photo_uploader.api_client import FacebookAPIClient
from fb_photo_uploader.models import Album, UploadResult

logger = logging.getLogger(__name__)


class PhotoUploader:
    """Manages concurrent photo uploads to Facebook."""

    def __init__(
        self,
        api_client: FacebookAPIClient,
        max_concurrent_uploads: int = 10,
        dry_run: bool = False,
    ) -> None:
        """Initialize photo uploader.

        Args:
            api_client: Facebook API client instance
            max_concurrent_uploads: Maximum number of concurrent uploads
            dry_run: If True, simulate uploads without making API calls
        """
        self.api_client = api_client
        self.max_concurrent_uploads = max_concurrent_uploads
        self.dry_run = dry_run
        self._semaphore = asyncio.Semaphore(max_concurrent_uploads)

    async def upload_albums(self, albums: list[Album]) -> list[UploadResult]:
        """Upload all albums with their photos.

        Args:
            albums: List of albums to upload

        Returns:
            List of upload results for all photos
        """
        results: list[UploadResult] = []

        for album in albums:
            logger.info(
                f"Processing album '{album.title}' with {len(album.photos)} photo(s)"
            )
            album_results = await self._upload_album(album)
            results.extend(album_results)

        return results

    async def _upload_album(self, album: Album) -> list[UploadResult]:
        """Upload a single album with concurrent photo uploads.

        Args:
            album: Album to upload

        Returns:
            List of upload results for the album's photos
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Would create album: {album.title}")
            album_id = "dry_run_album_id"
        else:
            try:
                album_id = await self.api_client.create_album(album.title)
            except Exception as e:
                logger.error(f"Failed to create album '{album.title}': {e}")
                # Return failed results for all photos in this album
                return [
                    UploadResult(
                        photo_path=photo,
                        album_title=album.title,
                        success=False,
                        error_message=f"Album creation failed: {e}",
                    )
                    for photo in album.photos
                ]

        # Upload photos concurrently
        tasks = [
            self._upload_photo_with_semaphore(album_id, album.title, photo)
            for photo in album.photos
        ]
        results = await asyncio.gather(*tasks)
        return list(results)

    async def _upload_photo_with_semaphore(
        self, album_id: str, album_title: str, photo_path: Path
    ) -> UploadResult:
        """Upload a single photo with semaphore-based concurrency control.

        Args:
            album_id: Album ID to upload to
            album_title: Album title (for result tracking)
            photo_path: Path to the photo file

        Returns:
            Upload result
        """
        async with self._semaphore:
            return await self._upload_photo(album_id, album_title, photo_path)

    async def _upload_photo(
        self, album_id: str, album_title: str, photo_path: Path
    ) -> UploadResult:
        """Upload a single photo to Facebook.

        Args:
            album_id: Album ID to upload to
            album_title: Album title (for result tracking)
            photo_path: Path to the photo file

        Returns:
            Upload result
        """
        if self.dry_run:
            logger.info(
                f"[DRY RUN] Would upload {photo_path.name} to album '{album_title}'"
            )
            return UploadResult(
                photo_path=photo_path,
                album_title=album_title,
                success=True,
                photo_id="dry_run_photo_id",
            )

        try:
            photo_id = await self.api_client.upload_photo(album_id, photo_path)
            logger.info(f"Successfully uploaded {photo_path.name} to '{album_title}'")
            return UploadResult(
                photo_path=photo_path,
                album_title=album_title,
                success=True,
                photo_id=photo_id,
            )
        except Exception as e:
            logger.error(f"Failed to upload {photo_path.name}: {e}")
            return UploadResult(
                photo_path=photo_path,
                album_title=album_title,
                success=False,
                error_message=str(e),
            )
