"""Decorative pictograms for the loan application."""

from base64 import b64encode

_STACK = (
    '<path d="M3 14c0-2 4-4 9-4s9 2 9 4v9c0 2.5-4 4.5-9 4.5S3 25.5 3 23z"/>'
    '<g fill="none" stroke="#fff" stroke-width="1" opacity=".6">'
    '<ellipse cx="12" cy="14" rx="8" ry="3"/>'
    '<path d="M4 18q8 5.5 16 0M4 21.5q8 5.5 16 0"/></g>'
)
_ICONS = {
    "coins": (
        '<g transform="translate(10 -3) scale(.93)">' + _STACK + '</g>'
        '<g transform="translate(-1 5) scale(.93)">' + _STACK + '</g>'
    ),
    "coins-plus": _STACK + '<path d="M25 12h3v4h4v3h-4v4h-3v-4h-4v-3h4z"/>',
    "bank": (
        '<path d="M1.5 10.3 16 3l14.5 7.3v2H1.5zM4 24h24v2H4zM2 27h28v2.5H2z"/>'
        '<path d="M5 14h4.6v8H5zm8.7 0h4.6v8h-4.6zm8.7 0H27v8h-4.6z"/>'
        '<path d="M6.4 14v8M15.1 14v8m8.7-8v8" fill="none" stroke="#fff" opacity=".58"/>'
        '<circle cx="16" cy="8.8" r="1.5" fill="#26122c" opacity=".65"/>'
    ),
    "bag": (
        '<path d="m10 3 4 1 2-2 2 2 4-1-3.5 6h-5zM12 10h8v2h-8z'
        'm-.1 3h8.2c2.5 3.4 6.6 7.9 6.6 11.7 0 3.5-4.2 5-10.7 5s-10.7-1.5-10.7-5'
        'c0-3.8 4.1-8.3 6.6-11.7z"/>'
        '<path d="M18.4 18.8c-4.2-2.4-7.1 3.5-4.2 5.7 1.2.9 2.7.7 3.7 0M16.8 17l-1.7 9.3" '
        'fill="none" stroke="#fff" stroke-width="1.7" stroke-linecap="round" opacity=".83"/>'
    ),
    "percent": (
        '<path d="M5 12 12 5l11-1 5 5-1 11-9 8a3 3 0 0 1-4 0L5 19a5 5 0 0 1 0-7z"/>'
        '<g fill="none" stroke="#fff" stroke-width="1.6" opacity=".9">'
        '<path d="m12 21 8-10"/><circle cx="12.2" cy="12.8" r="1.8"/>'
        '<circle cx="19.7" cy="19.1" r="1.8"/></g>'
        '<circle cx="24" cy="8" r="1.1" fill="#fff" opacity=".7"/>'
    ),
}


def icon(name: str, color: str = "#73536e") -> str:
    # st.html sanitizes inline SVG, but keeps local image data URLs.
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" fill="{color}">'
        f'{_ICONS[name]}</svg>'
    )
    encoded = b64encode(svg.encode()).decode()
    return f'<img class="bank-draw-icon" src="data:image/svg+xml;base64,{encoded}" alt="">'
