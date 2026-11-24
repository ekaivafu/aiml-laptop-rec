from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple, Optional
import requests

class BaseCollector(ABC):
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        })

    @abstractmethod
    def discover_urls(self, limit: int = 100) -> List[str]:
        """Discover product URLs up to the limit."""
        pass

    @abstractmethod
    def fetch_product(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Fetch the product page.
        Returns a tuple of (raw_html, raw_json) depending on the source.
        """
        pass

    @abstractmethod
    def extract_raw_fields(self, html: Optional[str], json_data: Optional[str]) -> Dict[str, Any]:
        """Extract raw facts from the fetched page without normalization."""
        pass
