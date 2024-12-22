from better_proxy import Proxy
from bot.config import settings
from typing import Optional


def get_proxy(raw_proxy: Optional[str]) -> Optional[str]:

    return Proxy.from_str(proxy=raw_proxy).as_url if raw_proxy else None


def get_proxies() -> list:

    if settings.USE_PROXY_FROM_FILE:
        with open("proxies.txt", encoding="utf-8-sig") as file:
            return [Proxy.from_str(row.strip()).as_url for row in file if row.strip()]

    return []
