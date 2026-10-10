# scripts/card.py
from calendar import monthrange
from dataclasses import dataclass
from datetime import date
from xml.sax.saxutils import escape

LINE_WIDTH = 64
STATS_HALF_WIDTH = 34
STATS_SEPARATOR = " | "
FONT_SIZE = 16
LINE_HEIGHT = 20
CHAR_WIDTH = FONT_SIZE * 0.62
PADDING = 20
CORNER_RADIUS = 12
MONTHS_PER_YEAR = 12

Segment = tuple[str, str]
Line = list[Segment]


@dataclass(frozen=True)
class Theme:
    background: str
    text: str
    key: str
    value: str
    dots: str
    added: str
    removed: str


DARK_THEME = Theme("#161b22", "#c9d1d9", "#ffa657", "#a5d6ff", "#616e7f", "#3fb950", "#f85149")
LIGHT_THEME = Theme("#f6f8fa", "#24292f", "#953800", "#0a3069", "#c2cfde", "#1a7f37", "#cf222e")


def leader(key: str, value: Line, width: int, prefix: str = ". ") -> Line:
    value_length = sum(len(text) for text, _ in value)
    fill = max(1, width - len(prefix) - len(key) - len(":") - value_length - 2)
    return [(prefix, "dots"), (f"{key}:", "key"), (" " + "." * fill + " ", "dots"), *value]


def text_row(key: str, value: str) -> Line:
    return leader(key, [(value, "value")], LINE_WIDTH)


def title_rule(title: str) -> Line:
    return [(f"{title} ", "text"), ("-" * (LINE_WIDTH - len(title) - 1), "dots")]


def section_rule(title: str) -> Line:
    label = f"- {title} "
    return [(label, "text"), ("-" * (LINE_WIDTH - len(label)), "dots")]


def pair_row(left_key: str, left: Line, right_key: str, right: Line) -> Line:
    right_width = LINE_WIDTH - STATS_HALF_WIDTH - len(STATS_SEPARATOR)
    return [
        *leader(left_key, left, STATS_HALF_WIDTH),
        (STATS_SEPARATOR, "text"),
        *leader(right_key, right, right_width, prefix=""),
    ]


def format_uptime(since: date, today: date) -> str:
    total_months = (today.year - since.year) * MONTHS_PER_YEAR + today.month - since.month
    if add_months(since, total_months) > today:
        total_months -= 1
    days = (today - add_months(since, total_months)).days
    years, months = divmod(total_months, MONTHS_PER_YEAR)
    return f"{plural(years, 'year')}, {plural(months, 'month')}, {plural(days, 'day')}"


def add_months(start: date, months: int) -> date:
    year, month_index = divmod(start.month - 1 + months, MONTHS_PER_YEAR)
    target_year, target_month = start.year + year, month_index + 1
    return date(target_year, target_month, min(start.day, monthrange(target_year, target_month)[1]))


def plural(count: int, unit: str) -> str:
    return f"{count} {unit}" if count == 1 else f"{count} {unit}s"


def render_svg(lines: list[Line], theme: Theme) -> str:
    width = round(PADDING * 2 + LINE_WIDTH * CHAR_WIDTH)
    height = PADDING * 2 + LINE_HEIGHT * len(lines)
    body = "\n".join(render_line(line, index) for index, line in enumerate(lines))
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace" font-size="{FONT_SIZE}px">
<style>
.text {{ fill: {theme.text}; }}
.key {{ fill: {theme.key}; }}
.value {{ fill: {theme.value}; }}
.dots {{ fill: {theme.dots}; }}
.added {{ fill: {theme.added}; }}
.removed {{ fill: {theme.removed}; }}
</style>
<rect width="{width}" height="{height}" rx="{CORNER_RADIUS}" fill="{theme.background}"/>
<text x="{PADDING}" y="{PADDING}" xml:space="preserve" class="text">
{body}
</text>
</svg>
"""


def render_line(line: Line, index: int) -> str:
    spans = "".join(f'<tspan class="{css}">{escape(text)}</tspan>' for text, css in line)
    dy = LINE_HEIGHT if index else LINE_HEIGHT - 4
    return f'<tspan x="{PADDING}" dy="{dy}">{spans}</tspan>'
