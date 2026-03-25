from __future__ import annotations

import asyncio
from collections import deque
from datetime import datetime, timedelta, timezone


class ProxyManager:
    def __init__(self, proxy_list: list[str]):
        self._all = [p for p in proxy_list if p]
        self._active = deque(self._all)
        self._failed_until: dict[str, datetime] = {}
        self._lock = asyncio.Lock()

    async def get_proxy(self) -> str:
        async with self._lock:
            await self.health_check()
            if not self._active:
                return ""
            proxy = self._active[0]
            self._active.rotate(-1)
            return proxy

    async def mark_failed(self, proxy: str) -> None:
        if not proxy:
            return
        async with self._lock:
            self._failed_until[proxy] = datetime.now(timezone.utc) + timedelta(minutes=5)
            self._active = deque([p for p in self._active if p != proxy])

    async def health_check(self) -> None:
        now = datetime.now(timezone.utc)
        recovered = [proxy for proxy, until in self._failed_until.items() if until <= now]
        for proxy in recovered:
            self._failed_until.pop(proxy, None)
            if proxy in self._all and proxy not in self._active:
                self._active.append(proxy)
