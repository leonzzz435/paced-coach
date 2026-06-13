import nh3

_ALLOWED_TAGS = {
    "div", "span", "p", "br", "hr",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li",
    "table", "thead", "tbody", "tr", "th", "td",
    "strong", "em", "b", "i", "small", "blockquote",
    "label",
    "a",
}

_ALLOWED_ATTRIBUTES: dict[str, set[str]] = {
    "*": {"class", "id", "style"},
    "a": {"href", "target"},
    "td": {"rowspan", "colspan"},
    "th": {"rowspan", "colspan"},
}


def sanitize_html(input_html: str) -> str:
    return nh3.clean(
        input_html,
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRIBUTES,
        link_rel="noopener noreferrer",
        url_schemes={"http", "https"},
    )
