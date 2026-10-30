"""Production regressions from independent lexical-parser review."""

import pytest

from desk.public_capture_policy import extract_static_text
from desk.store import DomainError


@pytest.mark.parametrize("tail", ["<!-->not approved-->", "<!--->not approved-->", "<!--foo--!>"])
@pytest.mark.parametrize("prefix", ["visible", "x" * 1019])
def test_malformed_comment_never_becomes_successful_partial_source(tail, prefix):
    with pytest.raises(DomainError, match="CAPTURE_HTML_MALFORMED"):
        extract_static_text((prefix + tail).encode(), "text/html")


@pytest.mark.parametrize("comment", ["<!--foo>bar-->", "<!--foo--->", "<!---->"])
def test_valid_comments_keep_visible_text_only(comment):
    result = extract_static_text(("visible" + comment).encode(), "text/html")
    assert result.body == b"visible\n"
