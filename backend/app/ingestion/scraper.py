from __future__ import annotations

from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup


@dataclass
class ScrapedDocument:
    title: str
    url: str
    summary: str


class RBIScraper:
    def scrape_listing(self, url: str) -> list[ScrapedDocument]:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        results: list[ScrapedDocument] = []
        for link in soup.select("a[href]"):
            title = link.get_text(" ", strip=True)
            href = link.get("href")
            if not title or not href:
                continue
            if "rbi" not in href.lower() and not href.startswith("/"):
                continue
            results.append(ScrapedDocument(title=title, url=href, summary=title))
        return results[:50]

