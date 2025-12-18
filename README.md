# Facebook Photo Uploader

A robust Command Line Interface (CLI) application for batch uploading photos to Facebook albums.

## Features

- **Batch Upload**: Automatically organize photos into albums based on directory structure
- **Concurrent Uploads**: Upload up to 10 photos simultaneously for faster processing
- **Resilient**: Implements exponential backoff for network failures, rate limits, and server errors
- **Dry Run Mode**: Preview operations without making actual API calls
- **Type-Safe**: Full type annotations using Python 3.13+ typing features
- **Well-Tested**: Comprehensive test suite with both white-box and black-box tests

## Installation

This project uses [uv](https://github.com/astral-sh/uv) for dependency management.

### Setup with uv

```bash
# Clone the repository
git clone <repository-url>
cd fb-photo-uploader

# Install dependencies
uv sync --dev

# Install the CLI tool
uv pip install -e .
```

## Usage

### Directory Structure

Organize your photos in the following structure:

```
photos/
├── Vacation 2024/
│   ├── photo1.jpg
│   ├── photo2.png
│   └── photo3.jpg
├── Family Reunion/
│   ├── img001.jpg
│   └── img002.jpg
└── Birthday Party/
    └── party.jpg
```

Each subdirectory becomes a Facebook album with the directory name as the album title.

### Basic Usage

```bash
# Upload photos (requires access token)
fb-photo-uploader upload /path/to/photos --access-token YOUR_TOKEN

# Or set token as environment variable
export FB_ACCESS_TOKEN=YOUR_TOKEN
fb-photo-uploader upload /path/to/photos
```

### Command Options

```bash
fb-photo-uploader upload [OPTIONS] ROOT_DIR

Arguments:
  ROOT_DIR  Root directory containing album subdirectories [required]

Options:
  -t, --access-token TEXT     Facebook API access token
                             (or set FB_ACCESS_TOKEN env var)
  --dry-run                  Simulate uploads without making API calls
  -c, --max-concurrent INT   Maximum concurrent uploads (1-50) [default: 10]
  -v, --verbose             Enable verbose logging
  --help                    Show this message and exit
```

### Examples

**Dry run to preview operations:**
```bash
fb-photo-uploader upload /path/to/photos --dry-run
```

**Upload with custom concurrency:**
```bash
fb-photo-uploader upload /path/to/photos --max-concurrent 5
```

**Verbose logging:**
```bash
fb-photo-uploader upload /path/to/photos --verbose
```

## Facebook API Setup

1. Go to [Facebook Developers](https://developers.facebook.com/)
2. Create a new app or use an existing one
3. Generate an access token with `user_photos` and `publish_actions` permissions
4. Use the token with the CLI

## Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov

# Run specific test file
uv run pytest tests/test_api_client.py

# Run specific test
uv run pytest tests/test_api_client.py::TestFacebookAPIClient::test_rate_limit_retry
```

### Project Structure

```
fb-photo-uploader/
├── src/
│   └── fb_photo_uploader/
│       ├── __init__.py       # Package initialization
│       ├── api_client.py     # Facebook API client with retry logic
│       ├── cli.py            # Command-line interface
│       ├── models.py         # Data models
│       ├── uploader.py       # Photo uploader with concurrency
│       └── utils.py          # Utility functions
├── tests/
│   ├── conftest.py           # Pytest fixtures
│   ├── test_api_client.py    # API client tests (white-box)
│   ├── test_cli.py           # CLI tests (black-box)
│   ├── test_uploader.py      # Uploader tests (white-box)
│   └── test_utils.py         # Utility tests
├── pyproject.toml            # Project configuration
└── README.md                 # This file
```

## Technical Details

### Retry Logic

The application implements exponential backoff for:
- Network failures (connection errors, timeouts)
- HTTP 5xx server errors
- HTTP 429 rate limit errors

Retry configuration:
- Maximum 5 attempts per request
- Exponential backoff: 1s, 2s, 4s, 8s, 16s (capped at 60s)

### Concurrency

- Uses asyncio with semaphore-based concurrency control
- Default: 10 concurrent uploads
- Configurable via `--max-concurrent` option

### Supported Image Formats

- JPEG (.jpg, .jpeg)
- PNG (.png)
- GIF (.gif)
- BMP (.bmp)
- WebP (.webp)
- HEIC (.heic)

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
