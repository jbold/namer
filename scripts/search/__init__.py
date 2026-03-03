"""Search package — environment detection, provider implementations, product signal analysis."""

from search.detect import detect_environment
from search.providers import PROVIDERS, discover_provider, do_search
from search.signals import PRODUCT_SIGNALS, check_product_presence

__all__ = [
    "detect_environment",
    "PROVIDERS",
    "discover_provider",
    "do_search",
    "PRODUCT_SIGNALS",
    "check_product_presence",
]
