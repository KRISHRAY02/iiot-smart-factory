import csv
import io

_FORMULA_PREFIXES = ("=", "+", "-", "@")


def safe_cell(value) -> str:
    """Stringify a CSV cell and defuse formula injection: a leading
    =, +, -, or @ makes some spreadsheet apps execute the cell as a
    formula, so prefix those with a single quote."""
    if value is None:
        return ""
    text = str(value)
    if text and text[0] in _FORMULA_PREFIXES:
        return "'" + text
    return text


def csv_row(cells) -> str:
    """Encodes one row via the stdlib csv module, so commas/quotes/newlines
    in values (e.g. resolution notes) are escaped correctly."""
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\r\n").writerow([safe_cell(c) for c in cells])
    return buf.getvalue()
