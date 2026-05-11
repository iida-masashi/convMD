import logging
import re
import urllib.parse
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx

logger = logging.getLogger(__name__)

def fetch_html(url: str) -> str | None:
    """Fetches HTML content from a given URL safely using httpx."""
    parsed = urllib.parse.urlparse(url)
    unquoted_path = urllib.parse.unquote(parsed.path)
    encoded_path = urllib.parse.quote(unquoted_path)
    encoded_url = parsed._replace(path=encoded_path).geturl()

    try:
        # httpx handles connection pooling and timeouts natively better than urllib
        with httpx.Client(follow_redirects=True, timeout=10.0, verify=False) as client:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            response = client.get(encoded_url, headers=headers)
            response.raise_for_status()
            # fallback to utf-8 if encoding is not detected
            charset = response.encoding or 'utf-8'
            return response.content.decode(charset, errors='replace')
    except httpx.RequestError as e:
        logger.error(f"Failed to request {url}: {e}")
        return None
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error {e.response.status_code} for {url}")
        return None

def process_images(md_content: str, base_url: str, output_dir: Path) -> str:
    """
    Finds Markdown image links, downloads the images locally,
    and replaces the links with relative local paths.
    """
    image_dir = output_dir / "images"
    image_dir.mkdir(parents=True, exist_ok=True)

    img_pattern = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')

    def replace_img(match: re.Match) -> str:
        alt_text = match.group(1)
        img_url = match.group(2)

        if img_url.startswith("data:"):
            return str(match.group(0))

        if not img_url.startswith("http"):
            img_url = urljoin(base_url, img_url)

        try:
            parsed_url = urlparse(img_url)
            filename = Path(urllib.parse.unquote(parsed_url.path)).name
            if not filename or '.' not in filename:
                filename = f"image_{hash(img_url) % 100000000:08d}.jpg"

            # Sanitize filename
            filename = re.sub(r'[\\/*?:"<>|]', "", filename)
            local_img_path = image_dir / filename

            # URL encode path
            unquoted_path = urllib.parse.unquote(parsed_url.path)
            encoded_path = urllib.parse.quote(unquoted_path)
            safe_img_url = parsed_url._replace(path=encoded_path).geturl()

            if not local_img_path.exists():
                with httpx.Client(follow_redirects=True, timeout=10.0, verify=False) as client:
                    response = client.get(safe_img_url, headers={'User-Agent': 'Mozilla/5.0'})
                    response.raise_for_status()
                    local_img_path.write_bytes(response.content)

            # Return relative path starting from output_dir
            return f"![{alt_text}](images/{filename})"

        except Exception as e:
            logger.warning(f"Failed to download image {img_url}: {e}")
            return str(match.group(0))

    return img_pattern.sub(replace_img, md_content)
