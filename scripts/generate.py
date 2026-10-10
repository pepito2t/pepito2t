# scripts/generate.py
import json
import logging
import os
import sys
from datetime import date
from pathlib import Path

from card import (
    DARK_THEME,
    LIGHT_THEME,
    LINE_WIDTH,
    Line,
    leader,
    format_uptime,
    pair_row,
    render_svg,
    section_rule,
    text_row,
    title_rule,
)
from stats import GitHubApiError, Stats, fetch_stats

ROOT = Path(__file__).resolve().parent.parent
PROFILE_PATH = ROOT / "profile.json"
OUTPUTS = {ROOT / "dark_mode.svg": DARK_THEME, ROOT / "light_mode.svg": LIGHT_THEME}

BLANK_LINE: Line = [(" ", "text")]

logger = logging.getLogger("generate")


def build_lines(profile: dict, stats: Stats, today: date) -> list[Line]:
    uptime = format_uptime(date.fromisoformat(profile["uptime_since"]), today)
    lines: list[Line] = [title_rule(profile["header"])]
    for index, section in enumerate(profile["sections"]):
        if index:
            lines.append(BLANK_LINE)
        if section["title"]:
            lines.append(section_rule(section["title"]))
        lines.extend(text_row(key, value.replace("{uptime}", uptime)) for key, value in section["rows"])
    lines.append(BLANK_LINE)
    lines.append(section_rule("GitHub Stats"))
    lines.extend(stats_lines(stats))
    return lines


def stats_lines(stats: Stats) -> list[Line]:
    return [
        pair_row(
            "Repos", [(f"{stats.repos:,}", "value"), (" {Contributed: ", "text"), (f"{stats.contributed:,}", "value"), ("}", "text")],
            "Stars", [(f"{stats.stars:,}", "value")],
        ),
        pair_row("Commits", [(f"{stats.commits:,}", "value")], "Followers", [(f"{stats.followers:,}", "value")]),
        lines_of_code_row(stats),
    ]


def lines_of_code_row(stats: Stats) -> Line:
    net = stats.additions - stats.deletions
    return leader(
        "Lines of Code on GitHub",
        [
            (f"{net:,}", "value"),
            (" ( ", "text"),
            (f"{stats.additions:,}++", "added"),
            (", ", "text"),
            (f"{stats.deletions:,}--", "removed"),
            (" )", "text"),
        ],
        LINE_WIDTH,
    )


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    token = os.environ.get("GH_TOKEN")
    if not token:
        logger.error("GH_TOKEN is not set")
        return 1
    profile = json.loads(PROFILE_PATH.read_text())
    try:
        stats = fetch_stats(token, profile["login"])
    except GitHubApiError as error:
        logger.error("Could not fetch GitHub stats: %s", error)
        return 1
    lines = build_lines(profile, stats, date.today())
    for path, theme in OUTPUTS.items():
        path.write_text(render_svg(lines, theme))
        logger.info("Wrote %s", path.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
