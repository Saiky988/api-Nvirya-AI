import pytest
from app.core.errors import InvalidRequestError
from app.search.extractor import extract_readable_text
from app.search.fetcher import WebFetcher
from app.search.providers import clean_url
from app.search.security import validate_url_security

def test_ssrf_blocking_local_and_private_ips():
    # Loopback
    with pytest.raises(InvalidRequestError):
        validate_url_security("http://127.0.0.1/secret")

    # Localhost
    with pytest.raises(InvalidRequestError):
        validate_url_security("http://localhost:8000/api")

    # Cloud metadata
    with pytest.raises(InvalidRequestError):
        validate_url_security("http://169.254.169.254/latest/meta-data/")

    # Private Class A / B / C
    with pytest.raises(InvalidRequestError):
        validate_url_security("http://10.0.0.1/")
    with pytest.raises(InvalidRequestError):
        validate_url_security("http://172.16.0.5/")
    with pytest.raises(InvalidRequestError):
        validate_url_security("http://192.168.1.1/")

    # Forbidden protocols
    with pytest.raises(InvalidRequestError):
        validate_url_security("file:///etc/passwd")
    with pytest.raises(InvalidRequestError):
        validate_url_security("gopher://127.0.0.1/")

def test_url_tracking_parameter_cleanup():
    url = "https://example.com/article?utm_source=twitter&utm_medium=social&id=123"
    cleaned = clean_url(url)
    assert "utm_source" not in cleaned
    assert "id=123" in cleaned

def test_html_readable_text_extraction():
    sample_html = """
    <html>
        <head><title>Test Page Title</title></head>
        <body>
            <nav><a href="/">Home</a></nav>
            <script>alert('malicious')</script>
            <style>body { color: red; }</style>
            <article>
                <h1>Article Heading</h1>
                <p>This is the important content of the article.</p>
            </article>
            <footer>Copyright 2026</footer>
        </body>
    </html>
    """
    extracted = extract_readable_text(sample_html, source_url="https://example.com/test")
    assert extracted["title"] == "Test Page Title"
    assert "This is the important content of the article." in extracted["text"]
    assert "alert('malicious')" not in extracted["text"]
    assert "Copyright 2026" not in extracted["text"]
