"""
keep_alive.py
-------------
Some platforms (e.g. Render's free "Web Service" type, as opposed to
"Background Worker") require the process to bind to $PORT and answer HTTP
requests, or they'll kill/restart it. This spins up a trivial HTTP server
in a background thread that just says "OK". Not needed on platforms that
run bots as background workers - disable with ENABLE_KEEPALIVE=false.
"""

import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import config


class _PingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is alive.")

    def log_message(self, format, *args):
        pass  # silence default request logging


def start():
    if not config.ENABLE_KEEPALIVE:
        return

    def _run():
        server = HTTPServer(("0.0.0.0", config.PORT), _PingHandler)
        server.serve_forever()

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
