import os
import urllib.error
import urllib.request

from flask import current_app
from werkzeug.utils import secure_filename

OPEN_LIBRARY_COVER_URL = 'https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg'
MIN_VALID_COVER_BYTES = 1000  # Open Library returns a tiny placeholder image for unknown ISBNs


def fetch_cover_by_isbn(isbn):
    """Try to download a cover image for the given ISBN. Returns the saved filename, or None."""
    url = OPEN_LIBRARY_COVER_URL.format(isbn=isbn)
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'SankofaLibrary/1.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = response.read()
    except (urllib.error.URLError, TimeoutError, OSError):
        return None

    if len(data) < MIN_VALID_COVER_BYTES:
        return None

    covers_folder = os.path.join(current_app.root_path, 'static', 'covers')
    os.makedirs(covers_folder, exist_ok=True)
    filename = secure_filename(f'cover_{isbn}.jpg')
    with open(os.path.join(covers_folder, filename), 'wb') as f:
        f.write(data)
    return filename
