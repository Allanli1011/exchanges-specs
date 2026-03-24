from typing import List, Dict, Optional
from bs4 import BeautifulSoup, Tag


def parse_table(html: str, table_index: int = 0, header_row: int = 0) -> List[Dict[str, str]]:
    """Extract an HTML table into a list of dicts keyed by header text."""
    soup = BeautifulSoup(html, "lxml")
    tables = soup.find_all("table")
    if not tables or table_index >= len(tables):
        return []

    table = tables[table_index]
    rows = table.find_all("tr")
    if len(rows) <= header_row:
        return []

    headers = [_cell_text(th) for th in rows[header_row].find_all(["th", "td"])]
    results = []
    for row in rows[header_row + 1:]:
        cells = [_cell_text(td) for td in row.find_all(["td", "th"])]
        if len(cells) == len(headers):
            results.append(dict(zip(headers, cells)))
        elif len(cells) > 0:
            padded = cells + [""] * (len(headers) - len(cells))
            results.append(dict(zip(headers, padded[:len(headers)])))
    return results


def parse_spec_table(html: str, css_selector: Optional[str] = None) -> Dict[str, str]:
    """Parse a two-column spec table (label: value) into a dict."""
    soup = BeautifulSoup(html, "lxml")
    if css_selector:
        container = soup.select_one(css_selector)
        if container is None:
            return {}
    else:
        container = soup

    result = {}
    for row in container.find_all("tr"):
        cells = row.find_all(["td", "th"])
        if len(cells) >= 2:
            key = _cell_text(cells[0])
            val = _cell_text(cells[1])
            if key:
                result[key] = val
    return result


def find_tables_with_header(html: str, header_text: str) -> List[Tag]:
    """Find all tables containing a specific header text."""
    soup = BeautifulSoup(html, "lxml")
    matches = []
    for table in soup.find_all("table"):
        first_row = table.find("tr")
        if first_row and header_text.lower() in first_row.get_text().lower():
            matches.append(table)
    return matches


def _cell_text(cell: Tag) -> str:
    """Extract clean text from a table cell."""
    return cell.get_text(separator=" ", strip=True)
