"""Simple health-check HTTP server for Uptime Kuma.

Runs on a background thread so it won't interfere with python-telegram-bot's
event loop. Reports 200 if the APScheduler is running, 503 otherwise.
"""
import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import scheduler as scheduler_mod

logger = logging.getLogger(__name__)


class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 (stdlib signature)
        if self.path != "/health":
            self.send_response(404)
            self.end_headers()
            return

        sched = scheduler_mod.scheduler
        is_running = bool(sched and sched.running)

        status_code = 200 if is_running else 503
        body = json.dumps({
            "status": "ok" if is_running else "degraded",
            "scheduler_running": is_running,
        }).encode("utf-8")

        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):  # noqa: A002 - silence default stderr spam
        return


def start(port: int = 8080) -> None:
    def _serve():
        server = HTTPServer(("0.0.0.0", port), _HealthHandler)
        logger.info("Health server listening on 0.0.0.0:%d/health", port)
        server.serve_forever()

    t = threading.Thread(target=_serve, name="health-server", daemon=True)
    t.start()
