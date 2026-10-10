# tests/test_card.py
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from card import DARK_THEME, LINE_WIDTH, format_uptime, pair_row, render_svg, section_rule, text_row  # noqa: E402
from stats import sum_author_weeks  # noqa: E402


def line_length(line: list[tuple[str, str]]) -> int:
    return sum(len(text) for text, _ in line)


class FormatUptimeTest(unittest.TestCase):
    def test_counts_full_years_months_and_days(self) -> None:
        self.assertEqual(format_uptime(date(2022, 4, 8), date(2026, 10, 11)), "4 years, 6 months, 3 days")

    def test_borrows_days_from_previous_month(self) -> None:
        self.assertEqual(format_uptime(date(2024, 1, 31), date(2024, 3, 1)), "0 years, 1 month, 1 day")

    def test_same_day_is_zero(self) -> None:
        self.assertEqual(format_uptime(date(2025, 5, 5), date(2025, 5, 5)), "0 years, 0 months, 0 days")


class LayoutTest(unittest.TestCase):
    def test_rows_fill_exact_width(self) -> None:
        self.assertEqual(line_length(text_row("OS", "macOS")), LINE_WIDTH)
        self.assertEqual(line_length(section_rule("Contact")), LINE_WIDTH)

    def test_pair_row_fills_exact_width(self) -> None:
        row = pair_row("Repos", [("11", "value")], "Stars", [("2", "value")])
        self.assertEqual(line_length(row), LINE_WIDTH)

    def test_long_value_keeps_at_least_one_dot(self) -> None:
        row = text_row("Key", "x" * LINE_WIDTH)
        self.assertIn(" . ", "".join(text for text, _ in row))


class RenderSvgTest(unittest.TestCase):
    def test_escapes_xml_characters(self) -> None:
        svg = render_svg([text_row("Mail", "<a&b>")], DARK_THEME)
        self.assertIn("&lt;a&amp;b&gt;", svg)


class SumAuthorWeeksTest(unittest.TestCase):
    def test_sums_matching_author_case_insensitively(self) -> None:
        contributors = [{"author": {"login": "Pepito2T"}, "weeks": [{"a": 10, "d": 2}, {"a": 5, "d": 1}]}]
        self.assertEqual(sum_author_weeks(contributors, "pepito2t"), (15, 3))

    def test_returns_zero_for_unexpected_payload(self) -> None:
        self.assertEqual(sum_author_weeks({}, "pepito2t"), (0, 0))


if __name__ == "__main__":
    unittest.main()
