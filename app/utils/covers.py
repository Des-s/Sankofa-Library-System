"""Cover image fetcher (FLASK-ADAPT).

Hardened with a 10s request timeout, Content-Type validation, a 5 MB
response size cap, and specific exception handling. Uses the `requests`
library so callers can rely on consistent timeout/size semantics.

Mirrors src/app/api/librarian/books/route.ts which defaults the cover to
the Open Library covers endpoint when the librarian does not upload one.
"""
import os

import requests
from flask import current_app
from werkzeug.utils import secure_filename


OPEN_LIBRARY_COVER_URL = 'https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg'
# Open Library returns a tiny placeholder image for unknown ISBNs — skip it.
MIN_VALID_COVER_BYTES = 1000


def fetch_cover_by_isbn(isbn):
    """Try to download a cover image for the given ISBN.

    Returns the saved filename, or ``None`` if the fetch failed for any
    reason (network error, non-image response, oversized response, etc.).
    (FLASK-ADAPT)
    """
    if not isbn:
        return None

    url = OPEN_LIBRARY_COVER_URL.format(isbn=isbn)
    timeout = current_app.config.get('COVER_REQUEST_TIMEOUT', 10)
    max_bytes = current_app.config.get('MAX_COVER_BYTES', 5 * 1024 * 1024)

    try:
        # stream=True so we can bail out the moment the body exceeds the cap.
        response = requests.get(
            url,
            headers={'User-Agent': 'SankofaLibrary/1.0'},
            timeout=timeout,
            stream=True,
            allow_redirects=True,
        )
        response.raise_for_status()
    except requests.exceptions.Timeout as exc:
        current_app.logger.warning(
            'fetch_cover_by_isbn: timeout for %s: %s', url, exc
        )
        return None
    except requests.exceptions.HTTPError as exc:
        current_app.logger.warning(
            'fetch_cover_by_isbn: HTTPError for %s: %s', url, exc
        )
        return None
    except requests.exceptions.ConnectionError as exc:
        current_app.logger.warning(
            'fetch_cover_by_isbn: connection error for %s: %s', url, exc
        )
        return None
    except requests.exceptions.RequestException as exc:
        current_app.logger.warning(
            'fetch_cover_by_isbn: request failed for %s: %s', url, exc
        )
        return None
    except OSError as exc:  # pragma: no cover - safety net
        current_app.logger.warning(
            'fetch_cover_by_isbn: OS error for %s: %s', url, exc
        )
        return None

    # Content-Type must be image/*.
    content_type = response.headers.get('Content-Type', '') or ''
    if not content_type.lower().startswith('image/'):
        current_app.logger.warning(
            'fetch_cover_by_isbn: %s returned non-image Content-Type %r',
            url, content_type,
        )
        response.close()
        return None

    # Stream-read with a hard size cap to avoid runaway downloads.
    chunks = []
    total = 0
    try:
        for chunk in response.iter_content(chunk_size=64 * 1024):
            if not chunk:
                continue
            total += len(chunk)
            if total > max_bytes:
                current_app.logger.warning(
                    'fetch_cover_by_isbn: %s exceeded %d-byte limit',
                    url, max_bytes,
                )
                response.close()
                return None
            chunks.append(chunk)
    finally:
        response.close()

    data = b''.join(chunks)
    if len(data) < MIN_VALID_COVER_BYTES:
        return None

    covers_folder = os.path.join(current_app.root_path, 'static', 'covers')
    os.makedirs(covers_folder, exist_ok=True)
    filename = secure_filename(f'cover_{isbn}.jpg')
    try:
        with open(os.path.join(covers_folder, filename), 'wb') as f:
            f.write(data)
    except OSError as exc:
        current_app.logger.error(
            'fetch_cover_by_isbn: could not write cover file: %s', exc
        )
        return None
    return filename
