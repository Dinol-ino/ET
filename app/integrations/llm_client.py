from __future__ import annotations

from typing import Any

import requests

from app.core.config import settings


class LLMClient:
    def __init__(self) -> None:
        self.base_url = settings.openrouter_base_url.rstrip("/")
        self.api_key = settings.openrouter_api_key
        self.model = settings.openrouter_model
        self.timeout = settings.request_timeout_seconds

    def generate_response(self, prompt: str) -> str:
        if not self.api_key:
            return self._fallback_response()

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": settings.openrouter_site_url,
            "X-Title": settings.openrouter_app_name,
        }
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a production sales intelligence reasoning assistant. "
                        "Give concise, actionable, evidence-grounded outputs."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            text = self._extract_content(data)
            if text:
                return text
        except requests.RequestException:
            pass

        return self._fallback_response()

    @staticmethod
    def _extract_content(payload: dict[str, Any]) -> str:
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            return ""
        first = choices[0] if isinstance(choices[0], dict) else {}
        message = first.get("message") if isinstance(first, dict) else {}
        if not isinstance(message, dict):
            return ""
        content = message.get("content")
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict) and isinstance(item.get("text"), str):
                    parts.append(item["text"].strip())
            return "\n".join([part for part in parts if part]).strip()
        return ""

    @staticmethod
    def _fallback_response() -> str:
        return (
            "Hi there - based on your recent growth focus, we can help your revenue team prioritize "
            "high-intent deals and reduce avoidable churn with actionable intelligence."
        )
