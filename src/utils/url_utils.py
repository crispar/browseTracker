"""
URL utilities for normalization and processing.
"""

from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
import re


def normalize_url(url: str, remove_tracking: bool = True) -> str:
    """Normalize a URL for deduplication.

    Args:
        url: The URL to normalize
        remove_tracking: Whether to remove tracking parameters

    Returns:
        Normalized URL string
    """
    if not url:
        return url

    try:
        # Parse the URL
        parsed = urlparse(url)

        # Normalize scheme to lowercase
        scheme = parsed.scheme.lower() if parsed.scheme else 'https'

        # Normalize hostname to lowercase
        netloc = parsed.netloc.lower() if parsed.netloc else ''

        # Remove default ports
        if ':80' in netloc and scheme == 'http':
            netloc = netloc.replace(':80', '')
        elif ':443' in netloc and scheme == 'https':
            netloc = netloc.replace(':443', '')

        # Normalize path (remove trailing slash unless it's root)
        path = parsed.path
        if path != '/' and path.endswith('/'):
            path = path[:-1]

        # Process query parameters
        if parsed.query and remove_tracking:
            # Common tracking parameters to remove
            tracking_params = {
                'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
                'fbclid', 'gclid', 'gclsrc', 'dclid', 'msclkid',
                '_ga', '_gid', '_gac', '_gl', '_x_tr_sl', '_x_tr_tl',
                'ref', 'ref_', 'referer', 'referrer', 'source',
                'mc_cid', 'mc_eid', 'mkt_tok'
            }

            # Parse and filter query parameters
            params = parse_qs(parsed.query, keep_blank_values=True)
            filtered_params = {
                key: value for key, value in params.items()
                if key.lower() not in tracking_params
            }

            # Rebuild query string with sorted parameters for consistency
            if filtered_params:
                query = urlencode(filtered_params, doseq=True)
            else:
                query = ''
        else:
            query = parsed.query

        # Remove fragment for comparison (anchors)
        fragment = ''

        # Reconstruct the URL
        normalized = urlunparse((scheme, netloc, path, parsed.params, query, fragment))

        return normalized

    except Exception:
        # If normalization fails, return original
        return url


def extract_domain(url: str) -> str:
    """Extract the domain from a URL.

    Args:
        url: The URL to extract domain from

    Returns:
        Domain string (e.g., 'example.com')
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # Remove www prefix
        if domain.startswith('www.'):
            domain = domain[4:]

        # Remove port if present
        if ':' in domain:
            domain = domain.split(':')[0]

        return domain
    except:
        return ''


def get_favicon_url(url: str) -> str:
    """Get the likely favicon URL for a given URL.

    Args:
        url: The page URL

    Returns:
        Favicon URL (using Google's favicon service)
    """
    domain = extract_domain(url)
    if domain:
        # Using Google's favicon service as it's reliable
        return f"https://www.google.com/s2/favicons?domain={domain}&sz=32"
    return ''


def truncate_url_for_display(url: str, max_length: int = 80) -> str:
    """Truncate URL for display purposes.

    Args:
        url: The URL to truncate
        max_length: Maximum display length

    Returns:
        Truncated URL with ellipsis if needed
    """
    if len(url) <= max_length:
        return url

    # Try to truncate at a sensible point
    parsed = urlparse(url)
    domain = parsed.netloc

    if len(domain) >= max_length - 3:
        # Even domain is too long
        return url[:max_length - 3] + '...'

    # Show domain and as much of the path as possible
    remaining = max_length - len(domain) - 6  # Account for scheme and ellipsis

    if parsed.path:
        if len(parsed.path) <= remaining:
            display_path = parsed.path
        else:
            display_path = parsed.path[:remaining] + '...'
        return f"{domain}{display_path}"
    else:
        return domain


def is_valid_url(url: str) -> bool:
    """Check if a string is a valid URL.

    Args:
        url: String to check

    Returns:
        True if valid URL, False otherwise
    """
    try:
        parsed = urlparse(url)
        return bool(parsed.scheme and parsed.netloc)
    except:
        return False


def clean_title(title: str) -> str:
    """Clean up a page title for display.

    Args:
        title: Raw page title

    Returns:
        Cleaned title
    """
    if not title:
        return ''

    # Remove excess whitespace
    title = ' '.join(title.split())

    # Remove common suffixes
    suffixes = [
        ' - Google Search',
        ' - Google 検索',
        ' - Bing',
        ' - YouTube',
        ' | Microsoft Learn',
        ' | MDN'
    ]

    for suffix in suffixes:
        if title.endswith(suffix):
            title = title[:-len(suffix)]
            break

    return title


if __name__ == "__main__":
    # Test URL utilities
    test_urls = [
        "https://www.example.com/page?utm_source=google&id=123",
        "http://example.com:80/path/",
        "https://www.youtube.com/watch?v=abc123&t=45s",
        "https://github.com/user/repo/issues/123#comment-456"
    ]

    print("URL Normalization Tests:\n")
    for url in test_urls:
        normalized = normalize_url(url)
        domain = extract_domain(url)
        print(f"Original:   {url}")
        print(f"Normalized: {normalized}")
        print(f"Domain:     {domain}")
        print(f"Truncated:  {truncate_url_for_display(url, 50)}")
        print()