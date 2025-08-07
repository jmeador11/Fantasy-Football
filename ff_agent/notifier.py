from __future__ import annotations

import json
from typing import Iterable, Optional
from urllib.request import Request, urlopen


def notify_console(title: str, lines: Iterable[str]) -> None:
    print(f"==== {title} ====")
    for line in lines:
        print(f"- {line}")


def notify_slack(webhook_url: Optional[str], title: str, lines: Iterable[str]) -> None:
    if not webhook_url:
        return
    text = f"*{title}*\n" + "\n".join(f"• {line}" for line in lines)
    payload = json.dumps({"text": text}).encode("utf-8")
    try:
        req = Request(webhook_url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        with urlopen(req, timeout=10) as resp:
            _ = resp.read()
    except Exception:
        pass