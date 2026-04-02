from __future__ import annotations

import requests

from app.core.config import settings


class LLMClient:
    def __init__(self) -> None:
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.model = settings.ollama_model
        self.timeout = settings.request_timeout_seconds

    def generate_response(self, prompt: str) -> str:
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False},
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
            text = str(payload.get("response") or "").strip()
            if text:
                return text
        except requests.RequestException:
            pass

        return (
            "Hi there - based on your recent growth focus, we can help your revenue team prioritize "
            "high-intent deals and reduce avoidable churn with actionable intelligence."
        )
