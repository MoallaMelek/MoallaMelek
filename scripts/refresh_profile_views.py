"""Save a daily profile-view snapshot; retain the last good badge on failure.

Komarev increments only requests from GitHub Camo. This script deliberately
uses its own User-Agent so refreshing the snapshot does not add a view.
The README's one-pixel image continues recording profile requests.
"""

import os
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "assets" / "profile-views.svg"


def read_count(svg):
    root = ET.fromstring(svg)
    if root.tag != "{http://www.w3.org/2000/svg}svg":
        raise ValueError("Expected an SVG badge")
    title = root.find("{http://www.w3.org/2000/svg}title")
    match = re.fullmatch(r"PROFILE VIEWS: ([0-9]+)", title.text or "") if title is not None else None
    if match is None:
        raise ValueError("Counter did not return a numeric view count")
    return int(match.group(1))


def render_badge(count):
    right_width = max(44, len(str(count)) * 8 + 20)
    width = 113 + right_width
    center = 113 + right_width / 2
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="28" role="img" aria-label="PROFILE VIEWS: {count}">
  <title>PROFILE VIEWS: {count}</title>
  <g shape-rendering="crispEdges">
    <rect width="113" height="28" fill="#555"/>
    <rect x="113" width="{right_width}" height="28" fill="#2563EB"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="10" letter-spacing="1.1">
    <text x="56.5" y="17.5">PROFILE VIEWS</text>
    <text x="{center:g}" y="17.5" font-weight="bold">{count}</text>
  </g>
</svg>
'''


def refresh(out=OUT):
    query = urllib.parse.urlencode({
        "username": os.environ.get("GH_USER", "MoallaMelek"),
        "style": "for-the-badge", "color": "2563EB", "label": "PROFILE VIEWS",
    })
    request = urllib.request.Request(
        "https://komarev.com/ghpvc/?" + query,
        headers={"User-Agent": "profile-views-snapshot/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            svg = response.read(32769)
        if len(svg) > 32768:
            raise ValueError("Unexpectedly large badge response")
        count = read_count(svg)
        if out.exists():
            previous = read_count(out.read_bytes())
            if count < previous:
                raise ValueError("Counter decreased; keeping the previous snapshot")
        out.parent.mkdir(parents=True, exist_ok=True)
        temporary = out.with_suffix(".svg.tmp")
        temporary.write_text(render_badge(count), encoding="utf-8")
        temporary.replace(out)
        print(f"Saved profile views snapshot: {count}")
        return True
    except Exception as error:
        if not out.exists():
            raise
        print(f"::warning::Keeping last good profile views badge: {error}")
        return False


if __name__ == "__main__":
    refresh()
