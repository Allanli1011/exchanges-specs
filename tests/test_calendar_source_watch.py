from src.calendar_source_watch import (
    check_sources,
    fingerprint,
    normalize_html_text,
)


def test_html_fingerprint_ignores_script_content_and_whitespace():
    a = b"<html><body><h1>Holiday Hours</h1><p>Closed</p><script>1</script></body></html>"
    b = b"<html><body> <h1>Holiday Hours</h1> <p>Closed</p> <script>2</script></body></html>"

    assert normalize_html_text(a) == normalize_html_text(b)
    assert fingerprint(a, "html_text")[0] == fingerprint(b, "html_text")[0]


def test_binary_fingerprint_changes_with_bytes():
    assert fingerprint(b"abc", "binary")[0] != fingerprint(b"abd", "binary")[0]
