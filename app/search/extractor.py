from typing import Optional
from bs4 import BeautifulSoup

MAX_CONTENT_CHARS = 8000

def extract_readable_text(
    html: str,
    source_url: str = "",
    max_length: int = MAX_CONTENT_CHARS,
) -> dict[str, Optional[str]]:
    """
    Extracts structured readable content from HTML.
    Strips scripts, styles, navigation, footer, and boilerplate.
    Returns: {title, author, published_at, text, source_url, truncated}
    """
    soup = BeautifulSoup(html, "html.parser")

    # Extract title
    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    elif soup.find("h1"):
        title = soup.find("h1").get_text(strip=True)

    # Extract author if present
    author = None
    meta_author = soup.find("meta", attrs={"name": "author"}) or soup.find("meta", attrs={"property": "article:author"})
    if meta_author and meta_author.get("content"):
        author = meta_author.get("content").strip()

    # Extract published time if present
    published_at = None
    meta_time = soup.find("meta", attrs={"property": "article:published_time"}) or soup.find("meta", attrs={"name": "pubdate"})
    if meta_time and meta_time.get("content"):
        published_at = meta_time.get("content").strip()

    # Remove non-content elements
    for element in soup(["script", "style", "nav", "header", "footer", "aside", "form", "noscript", "svg", "iframe"]):
        element.decompose()

    # Extract main text
    # Try finding <main> or <article> first
    main_container = soup.find("article") or soup.find("main") or soup.find("div", class_="content") or soup.body or soup

    # Get clean text
    lines = (line.strip() for line in main_container.get_text(separator="\n").splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    clean_text = "\n".join(chunk for chunk in chunks if chunk)

    truncated = False
    if len(clean_text) > max_length:
        clean_text = clean_text[:max_length].rstrip() + "\n\n[content truncated]"
        truncated = True

    return {
        "title": title or "Untitled",
        "author": author,
        "published_at": published_at,
        "text": clean_text,
        "source_url": source_url,
        "truncated": str(truncated).lower(),
    }
