# app/utils/rate_limit.py
# In-memory IP-based limiter for /admin/login (MVP).
import time
from typing import Tuple, Dict

WINDOW_S = 600       # 10 minutes
MAX_ATTEMPTS = 5
LOCKOUT_S = 600      # 10 minutes

# ip -> { "wins": [ts...], "lock_until": ts }
_state: Dict[str, Dict] = {}

def _now() -> int:
    return int(time.time())

def check(ip: str) -> Tuple[bool, int]:
    s = _state.get(ip, {"wins": [], "lock_until": 0})
    now = _now()
    if s.get("lock_until", 0) > now:
        return False, s["lock_until"] - now
    # prune window
    s["wins"] = [t for t in s.get("wins", []) if now - t <= WINDOW_S]
    _state[ip] = s
    if len(s["wins"]) >= MAX_ATTEMPTS:
        s["lock_until"] = now + LOCKOUT_S
        _state[ip] = s
        return False, LOCKOUT_S
    return True, 0

def record_failure(ip: str) -> None:
    s = _state.get(ip, {"wins": [], "lock_until": 0})
    s["wins"].append(_now())
    _state[ip] = s

def record_success(ip: str) -> None:
    _state[ip] = {"wins": [], "lock_until": 0}
