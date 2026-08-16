from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from playwright.sync_api import Page, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / ".runtime" / "qa-kitten"
BACKEND_LOG = RUNTIME / "backend.log"
RESULTS_JSON = RUNTIME / "results.json"
DASHBOARD_PNG = RUNTIME / "dashboard.png"
AFTER_READY_PNG = RUNTIME / "after-ready.png"
AFTER_TITLE_PNG = RUNTIME / "after-title-macro.png"
DEFAULT_BASE_URL = "http://127.0.0.1:8787"


@dataclass(frozen=True)
class QaResult:
    name: str
    ok: bool
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "ok": self.ok, "payload": self.payload}


class QaRun:
    def __init__(self, *, base_url: str, headed: bool, run_emulator: bool) -> None:
        self.base_url = base_url.rstrip("/")
        self.headed = headed
        self.run_emulator = run_emulator
        self.results: list[QaResult] = []
        self.backend: subprocess.Popen[str] | None = None

    def run(self) -> int:
        RUNTIME.mkdir(parents=True, exist_ok=True)
        self._kill_port(8787)
        self._start_backend()
        try:
            self._wait_health()
            self._api_smoke()
            self._browser_smoke()
            if self.run_emulator:
                self._emulator_flow()
        finally:
            self._check_backend_log_clean()
            self._write_results()
            self._stop_backend()
        return 0 if all(result.ok for result in self.results) else 1

    def _start_backend(self) -> None:
        log = BACKEND_LOG.open("w", encoding="utf-8")
        env = os.environ.copy()
        env.setdefault("PYTHONUNBUFFERED", "1")
        self.backend = subprocess.Popen(
            ["uv", "run", "rld", "serve", "--host", "127.0.0.1", "--port", "8787"],
            cwd=ROOT,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
        )
        self.results.append(QaResult("backend.start", True, {"pid": self.backend.pid, "log": str(BACKEND_LOG)}))

    def _wait_health(self) -> None:
        deadline = time.time() + 30
        last_error = "not attempted"
        while time.time() < deadline:
            try:
                response = httpx.get(f"{self.base_url}/health", timeout=2)
                if response.status_code == 200:
                    self.results.append(QaResult("backend.health", True, response.json()))
                    return
                last_error = f"HTTP {response.status_code}: {response.text[:200]}"
            except httpx.HTTPError as exc:
                last_error = str(exc)
            time.sleep(0.5)
        self.results.append(QaResult("backend.health", False, {"error": last_error, "log": _tail(BACKEND_LOG)}))
        raise RuntimeError(f"backend health failed: {last_error}")

    def _api_smoke(self) -> None:
        for path in ["/", "/api/emulator/controls", "/health/providers"]:
            try:
                response = httpx.get(f"{self.base_url}{path}", timeout=5)
                ok = response.status_code < 500
                payload: dict[str, Any] = {"status_code": response.status_code}
                if "application/json" in response.headers.get("content-type", ""):
                    payload["json"] = response.json()
                else:
                    payload["text_prefix"] = response.text[:200]
                self.results.append(QaResult(f"api.get.{path}", ok, payload))
            except httpx.HTTPError as exc:
                self.results.append(QaResult(f"api.get.{path}", False, {"error": str(exc)}))

    def _browser_smoke(self) -> None:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=not self.headed, slow_mo=50 if self.headed else 0)
            try:
                page = browser.new_page(viewport={"width": 1440, "height": 1000})
                page.goto(self.base_url, wait_until="networkidle", timeout=30_000)
                title_text = page.locator("body").inner_text(timeout=10_000)
                ok = "PokedexCompleter" in title_text or "Emulator Control" in title_text
                page.screenshot(path=str(DASHBOARD_PNG), full_page=True)
                self.results.append(
                    QaResult(
                        "browser.dashboard",
                        ok,
                        {"screenshot": str(DASHBOARD_PNG), "text_prefix": title_text[:500]},
                    )
                )
            finally:
                for page in browser.contexts[0].pages if browser.contexts else []:
                    page.close()
                browser.close()

    def _emulator_flow(self) -> None:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=not self.headed, slow_mo=80 if self.headed else 0)
            try:
                page = browser.new_page(viewport={"width": 1440, "height": 1000})
                page.goto(self.base_url, wait_until="networkidle", timeout=30_000)
                self._click_and_capture_json(
                    page,
                    "text=Ensure Ready",
                    "emulator.ensure_ready",
                    AFTER_READY_PNG,
                    timeout=90_000,
                    expected_kind="ensure-ready",
                )
                self._click_and_capture_json(
                    page,
                    "text=Title → Continue Save",
                    "emulator.title_resume",
                    AFTER_TITLE_PNG,
                    timeout=180_000,
                    expected_kind="title-resume",
                )
            finally:
                for page in browser.contexts[0].pages if browser.contexts else []:
                    page.close()
                browser.close()

    def _click_and_capture_json(
        self,
        page: Page,
        selector: str,
        name: str,
        screenshot_path: Path,
        *,
        timeout: int,
        expected_kind: str,
    ) -> None:
        output = page.locator("#emulatorOutput")
        previous = output.inner_text(timeout=5_000).strip() if output.is_visible() else ""
        page.locator(selector).click(timeout=10_000)
        output.wait_for(state="visible", timeout=timeout)
        deadline = time.time() + (timeout / 1000)
        parsed: dict[str, Any] | None = None
        raw = ""
        while time.time() < deadline:
            raw = output.inner_text(timeout=5_000).strip()
            if raw == previous:
                time.sleep(0.5)
                continue
            try:
                parsed = json.loads(raw)
                break
            except json.JSONDecodeError:
                time.sleep(0.5)
        page.screenshot(path=str(screenshot_path), full_page=True)
        ok, expectation = _matches_expected_kind(parsed, expected_kind)
        self.results.append(
            QaResult(
                name,
                ok,
                {
                    "expectation": expectation,
                    "json": parsed,
                    "raw_prefix": raw[:500],
                    "screenshot": str(screenshot_path),
                },
            )
        )

    def _check_backend_log_clean(self) -> None:
        tail = _tail(BACKEND_LOG, chars=20_000)
        dirty = "Traceback" in tail or "ERROR:" in tail
        self.results.append(QaResult("backend.log_clean", not dirty, {"dirty": dirty, "tail": tail[-4000:]}))

    def _stop_backend(self) -> None:
        if self.backend is None or self.backend.poll() is not None:
            return
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(self.backend.pid), "/T", "/F"], check=False, capture_output=True)
        else:
            self.backend.send_signal(signal.SIGTERM)
            try:
                self.backend.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.backend.kill()

    def _kill_port(self, port: int) -> None:
        if os.name != "nt":
            return
        command = (
            f"$pids=(Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue).OwningProcess "
            "| Sort -Unique; $pids | % { Stop-Process -Id $_ -Force }"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.results.append(
            QaResult(
                "backend.kill_port",
                result.returncode == 0,
                {"port": port, "stdout": result.stdout.strip(), "stderr": result.stderr.strip()},
            )
        )

    def _write_results(self) -> None:
        payload = {
            "ok": all(result.ok for result in self.results),
            "results": [result.to_dict() for result in self.results],
            "backend_log_tail": _tail(BACKEND_LOG),
        }
        RESULTS_JSON.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        print(json.dumps(payload, indent=2, default=str))


def _matches_expected_kind(parsed: dict[str, Any] | None, expected_kind: str) -> tuple[bool, str]:
    if parsed is None:
        return False, "response was not valid JSON"
    if expected_kind == "ensure-ready":
        return parsed.get("ok") is True, "expected ensure-ready response with ok=true"
    if expected_kind == "title-resume":
        macro_name = parsed.get("macro_name")
        status = parsed.get("status")
        ok = macro_name == "resume_saved_game_from_title" and status in {"candidate-overworld", "needs-human"}
        return ok, "expected title resume macro response"
    return parsed.get("ok", True) is not False, "expected generic non-error response"


def _tail(path: Path, *, chars: int = 4000) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[-chars:]


def main() -> int:
    parser = argparse.ArgumentParser(description="Headed Playwright QA runner for the local dashboard.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--headless", action="store_true", help="Run Chromium headless instead of headed.")
    parser.add_argument("--emulator", action="store_true", help="Run emulator Ensure Ready + title resume UI flow.")
    args = parser.parse_args()
    return QaRun(base_url=args.base_url, headed=not args.headless, run_emulator=args.emulator).run()


if __name__ == "__main__":
    raise SystemExit(main())
