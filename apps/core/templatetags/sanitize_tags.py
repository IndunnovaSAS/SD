"""
Template tags for HTML sanitization to prevent XSS vulnerabilities.

This module provides template filters to safely render user-generated HTML content
by sanitizing it with bleach, which removes or escapes potentially dangerous HTML.

Usage:
    {% load sanitize_tags %}
    {{ content|sanitize_html }}
    {{ icon|sanitize_svg }}
"""

import json
import re

from django import template
from django.utils.safestring import mark_safe

import bleach

register = template.Library()

# Allowed HTML tags for rich text content (e.g., lesson content, talk templates)
ALLOWED_TAGS = [
    # Text formatting
    "p",
    "br",
    "hr",
    "strong",
    "b",
    "em",
    "i",
    "u",
    "s",
    "strike",
    "del",
    "ins",
    "sub",
    "sup",
    "mark",
    "small",
    "abbr",
    "cite",
    "code",
    "pre",
    "blockquote",
    "q",
    # Headings
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    # Lists
    "ul",
    "ol",
    "li",
    "dl",
    "dt",
    "dd",
    # Tables
    "table",
    "thead",
    "tbody",
    "tfoot",
    "tr",
    "th",
    "td",
    "caption",
    "colgroup",
    "col",
    # Links and media (controlled)
    "a",
    "img",
    # Semantic elements
    "article",
    "section",
    "aside",
    "header",
    "footer",
    "nav",
    "main",
    "figure",
    "figcaption",
    "details",
    "summary",
    # Containers
    "div",
    "span",
]

# Allowed attributes for each tag
ALLOWED_ATTRIBUTES = {
    "*": ["class", "id", "title", "lang", "dir"],
    "a": ["href", "target", "rel", "title"],
    "img": ["src", "alt", "title", "width", "height", "loading"],
    "abbr": ["title"],
    "td": ["colspan", "rowspan", "headers"],
    "th": ["colspan", "rowspan", "headers", "scope"],
    "col": ["span"],
    "colgroup": ["span"],
    "ol": ["start", "type", "reversed"],
    "ul": ["type"],
    "li": ["value"],
    "blockquote": ["cite"],
    "q": ["cite"],
    "time": ["datetime"],
    "details": ["open"],
}

# Allowed protocols for URLs
ALLOWED_PROTOCOLS = ["http", "https", "mailto", "tel"]

# Allowed SVG tags (minimal set for icons)
ALLOWED_SVG_TAGS = [
    "svg",
    "path",
    "circle",
    "ellipse",
    "line",
    "polygon",
    "polyline",
    "rect",
    "g",
    "defs",
    "clipPath",
    "use",
    "symbol",
    "title",
    "desc",
]

# Allowed SVG attributes
ALLOWED_SVG_ATTRIBUTES = {
    "*": ["class", "id"],
    "svg": [
        "viewBox",
        "width",
        "height",
        "fill",
        "stroke",
        "xmlns",
        "preserveAspectRatio",
        "role",
        "aria-hidden",
        "aria-label",
        "focusable",
        "style",
    ],
    "path": [
        "d",
        "fill",
        "stroke",
        "stroke-width",
        "stroke-linecap",
        "stroke-linejoin",
        "fill-rule",
        "clip-rule",
        "transform",
        "opacity",
        "stroke-opacity",
        "fill-opacity",
    ],
    "circle": ["cx", "cy", "r", "fill", "stroke", "stroke-width", "transform", "opacity"],
    "ellipse": ["cx", "cy", "rx", "ry", "fill", "stroke", "stroke-width", "transform", "opacity"],
    "line": ["x1", "y1", "x2", "y2", "stroke", "stroke-width", "transform", "opacity"],
    "polygon": ["points", "fill", "stroke", "stroke-width", "transform", "opacity"],
    "polyline": ["points", "fill", "stroke", "stroke-width", "transform", "opacity"],
    "rect": [
        "x",
        "y",
        "width",
        "height",
        "rx",
        "ry",
        "fill",
        "stroke",
        "stroke-width",
        "transform",
        "opacity",
    ],
    "g": ["fill", "stroke", "stroke-width", "transform", "opacity", "clip-path"],
    "defs": [],
    "clipPath": ["id"],
    "use": ["href", "xlink:href", "x", "y", "width", "height", "transform"],
    "symbol": ["id", "viewBox", "preserveAspectRatio"],
    "title": [],
    "desc": [],
}


@register.filter(name="sanitize_html")
def sanitize_html(value):
    """
    Sanitize HTML content to prevent XSS attacks.

    Allows a safe subset of HTML tags and attributes commonly used in
    rich text content like lessons and talk templates.

    Usage:
        {{ lesson.content|sanitize_html }}

    Args:
        value: HTML string to sanitize

    Returns:
        Sanitized HTML marked as safe for rendering
    """
    if not value:
        return ""

    # Clean the HTML using bleach
    cleaned = bleach.clean(
        str(value),
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )

    # Add rel="noopener noreferrer" to links with target="_blank" for security
    cleaned = bleach.linkify(
        cleaned,
        callbacks=[_add_noopener_to_blank_links],
        skip_tags=["pre", "code"],
        parse_email=False,
    )

    return mark_safe(cleaned)


def _add_noopener_to_blank_links(attrs, new=False):
    """
    Callback for bleach.linkify to add rel="noopener noreferrer" to links
    that open in a new tab for security.
    """
    if attrs is None:
        return attrs

    # Check if link opens in new tab
    target = attrs.get((None, "target"), "")
    if target == "_blank":
        # Add noopener noreferrer for security
        rel = attrs.get((None, "rel"), "")
        if "noopener" not in rel:
            attrs[(None, "rel")] = "noopener noreferrer"

    return attrs


@register.filter(name="sanitize_svg")
def sanitize_svg(value):
    """
    Sanitize SVG content to prevent XSS attacks while allowing valid SVG icons.

    Only allows a minimal set of SVG elements and attributes needed for icons.

    Usage:
        {{ stat.icon|sanitize_svg }}

    Args:
        value: SVG string to sanitize

    Returns:
        Sanitized SVG marked as safe for rendering
    """
    if not value:
        return ""

    value_str = str(value).strip()

    # Verify it starts with an SVG tag
    if not re.match(r"^\s*<svg[\s>]", value_str, re.IGNORECASE):
        # Not an SVG, escape and return
        return bleach.clean(value_str, tags=[], strip=True)

    # Clean the SVG using bleach with SVG-specific allowed tags/attributes
    cleaned = bleach.clean(
        value_str,
        tags=ALLOWED_SVG_TAGS,
        attributes=ALLOWED_SVG_ATTRIBUTES,
        protocols=[],  # No protocols allowed in SVG
        strip=True,
    )

    # Remove any event handlers that might have slipped through
    # (extra safety measure)
    cleaned = re.sub(r'\s+on\w+\s*=\s*["\'][^"\']*["\']', "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+on\w+\s*=\s*[^\s>]+", "", cleaned, flags=re.IGNORECASE)

    return mark_safe(cleaned)


@register.filter(name="json_safe")
def json_safe(value):
    """
    Safely serialize a Python object to JSON for use in JavaScript.

    This filter ensures proper JSON encoding and prevents XSS by escaping
    special characters. Use this instead of |safe for JSON data.

    Usage:
        const data = {{ my_data|json_safe }};

    Note: For better security, prefer using Django's built-in json_script tag:
        {{ my_data|json_script:"data-id" }}
        <script>const data = JSON.parse(document.getElementById('data-id').textContent);</script>

    Args:
        value: Python object to serialize

    Returns:
        JSON string safe for embedding in HTML/JavaScript
    """
    if value is None:
        return "null"

    # Serialize to JSON with proper escaping
    json_str = json.dumps(value, ensure_ascii=False)

    # Escape characters that could break out of script context
    # See: https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html
    # Only escape < and > to prevent script tag injection
    # JSON already properly escapes quotes and backslashes
    json_str = json_str.replace("<", "\\u003c")
    json_str = json_str.replace(">", "\\u003e")
    json_str = json_str.replace("&", "\\u0026")

    return mark_safe(json_str)
