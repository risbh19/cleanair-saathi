"""Bound requests on expensive endpoints without retaining raw client addresses."""
from collections import OrderedDict, deque
from hashlib import blake2s
from secrets import token_bytes
from threading import Lock
from time import monotonic

from fastapi import Request
from fastapi.responses import JSONResponse


class RequestLimits:
    def __init__(self, maximum=60, interval=60, capacity=2048):
        self.maximum, self.interval, self.capacity = maximum, interval, capacity
        self.salt = token_bytes(16)
        self.clients = OrderedDict()
        self.lock = Lock()

    def allow(self, address, now):
        key = blake2s(address.encode(), key=self.salt, digest_size=16).digest()
        with self.lock:
            while self.clients:
                first = next(iter(self.clients.values()))
                if first[-1] > now - self.interval:
                    break
                self.clients.popitem(last=False)
            times = self.clients.get(key)
            if times is None:
                if len(self.clients) >= self.capacity:
                    return False
                times = self.clients[key] = deque()
            while times and times[0] <= now - self.interval:
                times.popleft()
            if len(times) >= self.maximum:
                return False
            times.append(now)
            self.clients.move_to_end(key)
            return True


limits = RequestLimits()


async def limit_expensive_routes(request: Request, call_next):
    if request.url.path in {"/plan/today", "/chat"} and request.method in {"GET", "POST"}:
        if not limits.allow(request.client.host if request.client else "unknown", monotonic()):
            return JSONResponse({"detail": "Please try again in a minute"}, status_code=429,
                                headers={"Retry-After": "60", "Cache-Control": "no-store"})
    return await call_next(request)
