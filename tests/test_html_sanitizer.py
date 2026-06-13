import pytest

from api.services.html_sanitizer import sanitize_html as api_sanitize
from services.ai.langgraph.schemas.html_sanitizer import sanitize_html as ai_sanitize


@pytest.fixture(params=["api", "ai"])
def sanitize(request):
    return api_sanitize if request.param == "api" else ai_sanitize


def test_strips_script_tags(sanitize):
    raw = "<div>hello</div><script>alert(1)</script>"
    result = sanitize(raw)
    assert "<script" not in result.lower()
    assert "alert" not in result


def test_strips_event_handlers(sanitize):
    raw = '<div onclick="alert(1)">x</div>'
    result = sanitize(raw)
    assert "onclick" not in result.lower()
    assert "alert" not in result


def test_strips_style_tags(sanitize):
    raw = "<style>body{display:none}</style><p>hello</p>"
    result = sanitize(raw)
    assert "<style" not in result.lower()
    assert "<p>hello</p>" in result


def test_strips_javascript_urls(sanitize):
    raw = '<a href="javascript:alert(1)">click</a>'
    result = sanitize(raw)
    assert "javascript" not in result.lower()


def test_strips_iframe(sanitize):
    raw = '<iframe src="https://evil.com"></iframe><p>safe</p>'
    result = sanitize(raw)
    assert "<iframe" not in result.lower()
    assert "safe" in result


def test_strips_object_and_embed(sanitize):
    raw = '<object data="evil.swf"></object><embed src="evil.swf"><p>ok</p>'
    result = sanitize(raw)
    assert "<object" not in result.lower()
    assert "<embed" not in result.lower()
    assert "ok" in result


def test_strips_data_uri(sanitize):
    raw = '<a href="data:text/html,<script>alert(1)</script>">click</a>'
    result = sanitize(raw)
    assert "data:" not in result


def test_preserves_allowed_tags(sanitize):
    raw = '<div class="card"><strong>Title</strong><ul><li>item</li></ul></div>'
    result = sanitize(raw)
    assert '<div class="card">' in result
    assert "<strong>Title</strong>" in result
    assert "<ul>" in result
    assert "<li>item</li>" in result


def test_preserves_table_structure(sanitize):
    raw = '<table class="table"><thead><tr><th>H</th></tr></thead><tbody><tr><td>V</td></tr></tbody></table>'
    result = sanitize(raw)
    assert '<table class="table">' in result
    assert "<thead>" in result
    assert "<tbody>" in result


def test_preserves_callout_classes(sanitize):
    raw = '<div class="callout-warning"><strong>Note:</strong> be careful</div>'
    result = sanitize(raw)
    assert "callout-warning" in result
    assert "<strong>Note:</strong>" in result


def test_preserves_workout_structure(sanitize):
    raw = (
        '<div class="workout">'
        '<div class="workout-title">Easy Run</div>'
        '<div class="workout-meta">run . 50min</div>'
        '</div>'
    )
    result = sanitize(raw)
    assert "workout-title" in result
    assert "workout-meta" in result


def test_strips_checkbox_input(sanitize):
    raw = '<label><input type="checkbox" id="2026-03-02--0"> warm up</label>'
    result = sanitize(raw)
    assert "<input" not in result.lower()
    assert "warm up" in result


def test_preserves_inline_styles(sanitize):
    raw = '<span style="font-size:.7rem;color:#64748b">detail</span>'
    result = sanitize(raw)
    assert "font-size:.7rem" in result


def test_preserves_rowspan_colspan(sanitize):
    raw = '<table><tr><td rowspan="3">cell</td><th colspan="2">head</th></tr></table>'
    result = sanitize(raw)
    assert 'rowspan="3"' in result
    assert 'colspan="2"' in result
