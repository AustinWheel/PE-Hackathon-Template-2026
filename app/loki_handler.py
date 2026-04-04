"""
Custom logging handler that pushes JSON logs to Grafana Loki via HTTP.
Uses a background thread + queue to avoid blocking request handling.
"""

import json
import logging
import os
import queue
import threading
import time
import urllib.request


class LokiHandler(logging.Handler):
    """Pushes log entries to Loki in batches via a background thread."""

    def __init__(self, url, labels=None, batch_size=50, flush_interval=1.0):
        super().__init__()
        self.url = url.rstrip("/") + "/loki/api/v1/push"
        self.labels = labels or {}
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self._queue = queue.Queue(maxsize=10000)
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._flush_loop, daemon=True)
        self._thread.start()

    def emit(self, record):
        try:
            msg = self.format(record)
            ts = str(int(record.created * 1e9))  # nanosecond timestamp
            self._queue.put_nowait((ts, msg))
        except queue.Full:
            pass  # drop logs if queue is full rather than blocking

    def _flush_loop(self):
        while not self._stop_event.is_set():
            time.sleep(self.flush_interval)
            self._flush()

    def _flush(self):
        entries = []
        while len(entries) < self.batch_size:
            try:
                entries.append(self._queue.get_nowait())
            except queue.Empty:
                break

        if not entries:
            return

        payload = {
            "streams": [
                {
                    "stream": self.labels,
                    "values": [[ts, msg] for ts, msg in entries],
                }
            ]
        }

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=5)
        except Exception:
            pass  # silently drop — don't crash the app if Loki is down

    def close(self):
        self._stop_event.set()
        self._flush()  # final flush
        super().close()


def create_loki_handler(formatter=None):
    """Create a LokiHandler if LOKI_URL is configured, otherwise return None."""
    loki_url = os.environ.get("LOKI_URL")
    if not loki_url:
        return None

    labels = {
        "job": "flask-app",
        "region": os.environ.get("APP_REGION", "unknown"),
        "environment": os.environ.get("APP_ENVIRONMENT", "unknown"),
        "instance_id": os.environ.get("APP_INSTANCE_ID", "unknown"),
    }

    handler = LokiHandler(url=loki_url, labels=labels)
    if formatter:
        handler.setFormatter(formatter)
    return handler
