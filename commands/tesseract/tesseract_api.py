import requests
from urllib.parse import urljoin

class TesseractAPI:
    def __init__(self, settings: dict, business_unit: str):
        self._validate_settings(settings)
        self.tesseract_url = self._get_url_by_business_unit(settings, business_unit)

    def fetch_data(self, model: str) -> dict:
        url = urljoin(self.tesseract_url, model)
        response = requests.get(url)
        response.raise_for_status()
        return response.json()

    def _get_url_by_business_unit(self, settings: dict, business_unit: str) -> str:
        if business_unit == "fisia":
            return settings.get("tesseract_fisia_url")
        elif business_unit == "centauro":
            return settings.get("tesseract_centauro_url")
        raise ValueError(f"Unsupported business unit: {business_unit}")

    def _validate_settings(self, settings: dict):
        if "tesseract_centauro_url" in settings:
            return
        if "tesseract_fisia_url" in settings:
            return
        raise ValueError("Missing required setting: tesseract_fisia_url or tesseract_centauro_url")
