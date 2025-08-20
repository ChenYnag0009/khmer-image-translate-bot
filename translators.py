import os
import requests
from typing import Literal

TargetLang = Literal["km"]

class TranslatorBase:
    def translate(self, text: str, target: TargetLang = "km") -> str:
        raise NotImplementedError

class LibreTranslate(TranslatorBase):
    def __init__(self):
        self.url = os.getenv("LIBRETRANSLATE_URL", "https://libretranslate.com").rstrip("/")
        self.api_key = os.getenv("LIBRETRANSLATE_API_KEY", "")
        # Map source guess: let API auto-detect (source='auto')
    def translate(self, text: str, target: TargetLang = "km") -> str:
        if not text.strip():
            return text
        payload = {"q": text, "source": "auto", "target": target, "format": "text"}
        if self.api_key:
            payload["api_key"] = self.api_key
        r = requests.post(f"{self.url}/translate", json=payload, timeout=30)
        r.raise_for_status()
        data = r.json()
        return data.get("translatedText", "")

def get_translator() -> TranslatorBase:
    # For now default to LibreTranslate; can extend to Google later
    return LibreTranslate()
