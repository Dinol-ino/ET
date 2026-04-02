from __future__ import annotations

import re

import requests

from app.core.config import settings


class ScraperClient:
    def __init__(self) -> None:
        self.timeout = settings.request_timeout_seconds

    def scrape_company_site(self, domain: str) -> str:
        domain = domain.strip().replace("https://", "").replace("http://", "").strip("/")
        if not domain:
            return "No website content available"

        for scheme in ("https://", "http://"):
            url = f"{scheme}{domain}"
            try:
                response = requests.get(url, timeout=self.timeout)
                response.raise_for_status()
                return self._extract_text(response.text)
            except requests.RequestException:
                continue

        return (
            f"{domain} appears to be a B2B business. Public website content could not be fetched, "
            "so this is a fallback profile generated for scoring continuity."
        )

    @staticmethod
    def _extract_text(html: str) -> str:
        text = re.sub(r"<script[\\s\\S]*?</script>", " ", html, flags=re.IGNORECASE)
        text = re.sub(r"<style[\\s\\S]*?</style>", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\\s+", " ", text).strip()
        return text[:2500] if text else "No readable content extracted"
