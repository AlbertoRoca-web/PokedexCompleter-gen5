from __future__ import annotations

import argparse
import json
import threading
import time
import webbrowser

import httpx
import uvicorn

from pokedex_completer_gen5.server.local_connection import discover_local_connections


def main() -> int:
    parser = argparse.ArgumentParser(description="Local browser/MCP/BizHawk companion for PokedexCompleter Gen 5.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--scan-only", action="store_true")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    if args.scan_only:
        print(json.dumps(discover_local_connections(args.host), indent=2))
        return 0

    url = f"http://{args.host}:{args.port}"
    if _api_reachable(url):
        if not args.no_browser:
            webbrowser.open(url)
        print(json.dumps({"ok": True, "status": "already-running", "url": url}, indent=2))
        return 0

    if not args.no_browser:
        threading.Thread(target=_open_when_ready, args=(url,), daemon=True).start()
    uvicorn.run(
        "pokedex_completer_gen5.server.rest:app",
        host=args.host,
        port=args.port,
        log_level="info",
    )
    return 0


def _api_reachable(url: str) -> bool:
    try:
        return httpx.get(f"{url}/api/local/discover", timeout=1).status_code == 200
    except httpx.HTTPError:
        return False


def _open_when_ready(url: str) -> None:
    for _ in range(60):
        if _api_reachable(url):
            webbrowser.open(url)
            return
        time.sleep(0.25)


if __name__ == "__main__":
    raise SystemExit(main())
