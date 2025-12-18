"""Data models for the Facebook photo uploader."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Album:
    """Represents a Facebook album with photos to upload."""

    title: str
    photos: list[Path]

    def __post_init__(self) -> None:
        """Validate album data."""
        if not self.title:
            raise ValueError("Album title cannot be empty")
        if not self.photos:
            raise ValueError("Album must contain at least one photo")


@dataclass(frozen=True)
class UploadResult:
    """Result of a photo upload operation."""

    photo_path: Path
    album_title: str
    success: bool
    photo_id: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        """Validate upload result."""
        if self.success and not self.photo_id:
            raise ValueError("Successful upload must have a photo_id")
        if not self.success and not self.error_message:
            raise ValueError("Failed upload must have an error_message")
