from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import os
import logging


class KeepAliveHandler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Bot is alive and running!")

    def log_message(self, format, *args):
        # Suppress standard logging from the http server to avoid spamming logs
        pass


def run():
    # Many Pterodactyl panels allocate a specific port in the PORT environment variable
    # If not present, we default to 8080
    try:
        port = int(os.environ.get("PORT", 8080))
        server_address = ("", port)
        httpd = HTTPServer(server_address, KeepAliveHandler)
        logging.info(f"Starting keep-alive server on port {port}")
        httpd.serve_forever()
    except Exception as e:
        logging.warning(f"Keep-alive server could not bind or run: {e}")


def keep_alive():
    t = threading.Thread(target=run, daemon=True)
    t.start()
