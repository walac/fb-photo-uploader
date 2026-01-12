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

### Prerequisites

Install uv if you haven't already:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Or on macOS/Linux:

```bash
pip install uv
```

### For Regular Use

If you only want to use the tool (not develop it):

```bash
# Clone the repository
git clone <repository-url>
cd fb-photo-uploader

# Install dependencies (without dev dependencies)
uv sync

# Install the CLI tool
uv pip install -e .
```

### For Development

If you want to contribute or run tests:

```bash
# Clone the repository
git clone <repository-url>
cd fb-photo-uploader

# Install the package with dev dependencies
# This installs: pytest, pytest-asyncio, responses, pytest-cov
uv pip install -e ".[dev]"

# Or alternatively, sync and install extras separately
uv sync --all-extras
uv pip install -e .
```

The `[dev]` extra installs optional development dependencies from `pyproject.toml`:
- **pytest** - Testing framework
- **pytest-asyncio** - Async test support
- **responses** - HTTP request mocking for tests
- **pytest-cov** - Code coverage reporting

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

To use this tool, you need a Facebook Graph API access token with photo upload permissions.

### Step 1: Create a Facebook App

1. Go to [Facebook Developers](https://developers.facebook.com/)
2. Click **My Apps** in the top menu
3. Click **Create App**
4. Select **Business** as the app type (or **Consumer** for personal use)
5. Fill in the app details:
   - **App Name**: Choose a name (e.g., "Photo Uploader")
   - **App Contact Email**: Your email address
6. Click **Create App**

### Step 2: Configure App Permissions

1. In your app dashboard, go to **App Settings** → **Basic**
2. Note your **App ID** and **App Secret** (you'll need these later)
3. Add a platform:
   - Scroll down to **Add Platform**
   - Select **Website**
   - Enter a Site URL (can be `http://localhost` for testing)

### Step 3: Add Required Products

1. In the left sidebar, find **Add Product**
2. Add **Facebook Login** by clicking **Set Up**
3. Configure Facebook Login settings:
   - Go to **Facebook Login** → **Settings**
   - Add `http://localhost` to **Valid OAuth Redirect URIs**

### Step 4: Generate an Access Token

#### Option A: Using Graph API Explorer (Recommended for Testing)

1. Go to [Graph API Explorer](https://developers.facebook.com/tools/explorer/)
2. In the top-right, select your app from the **Application** dropdown
3. Click **Generate Access Token**
4. In the permissions dialog, select:
   - `user_photos` - Required to upload photos
   - `user_videos` - Optional, if you plan to upload videos
5. Click **Generate Access Token** and authorize the app
6. Copy the generated access token

**Important**: Tokens from Graph API Explorer are short-lived (1-2 hours). For production use, see Option B.

#### Option B: Generate Long-Lived Token (Production Use)

Short-lived tokens expire quickly. To get a long-lived token (60 days):

```bash
curl -G \
  -d "grant_type=fb_exchange_token" \
  -d "client_id=YOUR_APP_ID" \
  -d "client_secret=YOUR_APP_SECRET" \
  -d "fb_exchange_token=YOUR_SHORT_LIVED_TOKEN" \
  "https://graph.facebook.com/v3.1/oauth/access_token"
```

Replace:
- `YOUR_APP_ID` - Your app ID from Step 2
- `YOUR_APP_SECRET` - Your app secret from Step 2
- `YOUR_SHORT_LIVED_TOKEN` - The token from Graph API Explorer

The response will contain a `access_token` field with your long-lived token.

#### Option C: Get a User Access Token via Login Flow

For a more permanent solution, implement the OAuth login flow:

1. Direct users to:
   ```
   https://www.facebook.com/v3.1/dialog/oauth?
     client_id=YOUR_APP_ID&
     redirect_uri=YOUR_REDIRECT_URI&
     scope=user_photos
   ```

2. After authorization, Facebook redirects to your URI with a `code` parameter

3. Exchange the code for an access token:
   ```bash
   curl -X GET "https://graph.facebook.com/v3.1/oauth/access_token?
     client_id=YOUR_APP_ID&
     redirect_uri=YOUR_REDIRECT_URI&
     client_secret=YOUR_APP_SECRET&
     code=CODE_FROM_STEP_2"
   ```

### Step 5: Verify Your Token

Test your token with:

```bash
curl -G \
  -d "access_token=YOUR_TOKEN" \
  "https://graph.facebook.com/v3.1/me"
```

If successful, you'll see your Facebook user information.

### Step 6: Use the Token

Set the token as an environment variable:

```bash
export FB_ACCESS_TOKEN=YOUR_ACCESS_TOKEN
fb-photo-uploader upload /path/to/photos
```

Or pass it directly:

```bash
fb-photo-uploader upload /path/to/photos --access-token YOUR_ACCESS_TOKEN
```

### Important Notes

- **Token Security**: Never commit access tokens to version control. Use environment variables or secure secret management.
- **Token Expiration**: Access tokens expire. Short-lived tokens last 1-2 hours, long-lived tokens last about 60 days. Monitor expiration and refresh as needed.
- **Permissions**: Ensure your token has `user_photos` permission. You can check permissions at [Access Token Debugger](https://developers.facebook.com/tools/debug/accesstoken/).
- **App Review**: For production apps that access other users' data, you may need Facebook's app review. Personal use with your own account doesn't require review.
- **Rate Limits**: Facebook enforces rate limits. This tool implements automatic retry with exponential backoff to handle rate limiting gracefully.

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
