#!/usr/bin/env python3
"""Tiny preview + download server for the worksheet.

/                     -> landing page (index.html)
/download             -> PDF sent as attachment (one-click save)
/view                 -> PDF rendered inline
/worksheet.pdf        -> same as /download
"""
import os
import http.server
import socketserver
import urllib.parse

PORT = int(os.environ.get("PORT", "8099"))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF = "Creative-Ideation-Worksheet-Astro-Smart-Attendance.pdf"


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def _pdf(self, attachment):
        path = os.path.join(ROOT, PDF)
        if not os.path.exists(path):
            self.send_error(404)
            return
        size = os.path.getsize(path)
        self.send_response(200)
        self.send_header("Content-Type", "application/pdf")
        self.send_header("Content-Length", str(size))
        disp = "attachment" if attachment else "inline"
        self.send_header("Content-Disposition", f'{disp}; filename="{PDF}"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        with open(path, "rb") as f:
            self.wfile.write(f.read())

    def do_GET(self):
        route = urllib.parse.urlparse(self.path).path
        if route in ("/download", "/worksheet.pdf", "/" + PDF):
            return self._pdf(True)
        if route == "/view":
            return self._pdf(False)
        if route == "/":
            self.path = "/index.html"
        return super().do_GET()

    def do_HEAD(self):
        route = urllib.parse.urlparse(self.path).path
        if route in ("/download", "/worksheet.pdf", "/" + PDF, "/view"):
            size = os.path.getsize(os.path.join(ROOT, PDF))
            self.send_response(200)
            self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Length", str(size))
            self.end_headers()
            return
        return super().do_HEAD()

    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args), flush=True)


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    with Server(("0.0.0.0", PORT), Handler) as httpd:
        print(f"serving {ROOT} on http://0.0.0.0:{PORT}", flush=True)
        httpd.serve_forever()
