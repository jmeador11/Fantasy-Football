from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class SleeperClient:
    BASE_V1 = "https://api.sleeper.app/v1"
    BASE = "https://api.sleeper.app"

    def __init__(self, request_timeout_sec: float = 15.0, max_retries: int = 2):
        self.timeout = request_timeout_sec
        self.max_retries = max_retries

    def _get(self, url: str, params: Optional[Dict[str, Any]] = None) -> Any:
        if params:
            url = f"{url}?{urlencode(params)}"
        last_exc: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                req = Request(url, headers={"User-Agent": "ff-agent/1.0"})
                with urlopen(req, timeout=self.timeout) as resp:
                    if resp.status != 200:
                        raise HTTPError(url, resp.status, "Non-200", hdrs=resp.headers, fp=None)
                    data = resp.read()
                    if not data:
                        return None
                    return json.loads(data.decode("utf-8"))
            except (HTTPError, URLError, TimeoutError) as exc:  # noqa: F821
                last_exc = exc
                time.sleep(0.5 * (attempt + 1))
        if last_exc:
            raise last_exc
        return None

    # Core documented endpoints
    def get_user(self, username_or_id: str) -> Dict[str, Any]:
        url = f"{self.BASE_V1}/user/{username_or_id}"
        return self._get(url)

    def get_state(self, sport: str = "nfl") -> Dict[str, Any]:
        url = f"{self.BASE_V1}/state/{sport}"
        return self._get(url)

    def get_user_leagues(self, user_id: str, season: int, sport: str = "nfl") -> List[Dict[str, Any]]:
        url = f"{self.BASE_V1}/user/{user_id}/leagues/{sport}/{season}"
        return self._get(url)

    def get_league(self, league_id: str) -> Dict[str, Any]:
        url = f"{self.BASE_V1}/league/{league_id}"
        return self._get(url)

    def get_league_users(self, league_id: str) -> List[Dict[str, Any]]:
        url = f"{self.BASE_V1}/league/{league_id}/users"
        return self._get(url)

    def get_rosters(self, league_id: str) -> List[Dict[str, Any]]:
        url = f"{self.BASE_V1}/league/{league_id}/rosters"
        return self._get(url)

    def get_matchups(self, league_id: str, week: int) -> List[Dict[str, Any]]:
        url = f"{self.BASE_V1}/league/{league_id}/matchups/{week}"
        return self._get(url)

    def get_transactions(self, league_id: str, week: int) -> List[Dict[str, Any]]:
        url = f"{self.BASE_V1}/league/{league_id}/transactions/{week}"
        return self._get(url)

    def get_traded_picks(self, league_id: str) -> List[Dict[str, Any]]:
        url = f"{self.BASE_V1}/league/{league_id}/traded_picks"
        return self._get(url)

    def get_all_players(self, sport: str = "nfl") -> Dict[str, Dict[str, Any]]:
        url = f"{self.BASE_V1}/players/{sport}"
        return self._get(url)

    def get_trending_players(self, sport: str = "nfl", trend_type: str = "add", hours: int = 24, limit: int = 50) -> List[Dict[str, Any]]:
        assert trend_type in ("add", "drop")
        url = f"{self.BASE_V1}/players/{sport}/trending/{trend_type}"
        params = {"hours": hours, "limit": limit}
        return self._get(url, params=params)

    # Best-effort projections. Sleeper has historically exposed these without /v1
    def get_projections(self, season: int, week: int, season_type: str = "regular", sport: str = "nfl") -> Optional[List[Dict[str, Any]]]:
        candidate_urls = [
            f"{self.BASE}/projections/{sport}/{season_type}/{season}/{week}",
            f"{self.BASE_V1}/projections/{sport}/{season_type}/{season}/{week}",
        ]
        for url in candidate_urls:
            try:
                data = self._get(url)
                if isinstance(data, list):
                    return data
            except Exception:
                continue
        return None