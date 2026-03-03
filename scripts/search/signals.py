"""
Product presence detection — check if a name has existing product/service web presence.
"""

from search.providers import do_search

PRODUCT_SIGNALS = [
    "app", "software", "platform", "saas", "tool", "service",
    "download", "pricing", "sign up", "login", "api", "sdk",
    "startup", "inc", "ltd", "gmbh", "solutions", "technologies",
    ".io", ".ai", ".app",
    "product", "features", "demo", "get started", "free trial",
    "enterprise", "cloud",
]


def check_product_presence(provider: str, env_vals: dict, name: str) -> dict:
    """Check if a name has existing product/service web presence.

    Returns dict with:
        name, has_product, signals, top_results, verdict (CLEAR/CAUTION/BUMPED)
    """
    result = {"name": name, "has_product": False, "signals": [], "top_results": []}

    results = do_search(provider, env_vals, name)

    for r in results:
        title = r.get("title", "").lower()
        desc = r.get("description", "").lower()
        url = r.get("url", "").lower()
        combined = f"{title} {desc} {url}"

        result["top_results"].append({
            "title": r.get("title", "")[:80],
            "url": r.get("url", "")[:80],
        })

        for signal in PRODUCT_SIGNALS:
            if signal in combined:
                result["signals"].append(signal)

    unique_signals = set(result["signals"])
    if len(unique_signals) >= 2:
        result["has_product"] = True
        result["verdict"] = "BUMPED"
    elif len(unique_signals) == 1:
        result["verdict"] = "CAUTION"
    else:
        result["verdict"] = "CLEAR"

    return result
