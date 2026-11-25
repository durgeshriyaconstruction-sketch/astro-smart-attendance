#!/usr/bin/env python3
"""Tiny preview + download server for the worksheet.

/                     -> landing page (index.html)
/download             -> PDF sent as attachment (one-click save)
/view                 -> PDF rendered inline
/worksheet.pdf        -> same as /download
/check, /check.pdf    -> format compliance check, as attachment
/view-check           -> compliance check, inline
"""
import os
import http.server
import socketserver
import urllib.parse

PORT = int(os.environ.get("PORT", "8099"))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF = "Creative-Ideation-Worksheet-Astro-Smart-Attendance.pdf"
CHECK = "Format-Compliance-Check.pdf"
SERVED = {"/download": PDF, "/worksheet.pdf": PDF, "/" + PDF: PDF,
          "/check": CHECK, "/check.pdf": CHECK, "/" + CHECK: CHECK,
          "/view": PDF, "/view-check": CHECK}


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def _pdf(self, attachment, name=PDF):
        path = os.path.join(ROOT, name)
        if not os.path.exists(path):
            self.send_error(404)
            return
        size = os.path.getsize(path)
        self.send_response(200)
        self.send_header("Content-Type", "application/pdf")
        self.send_header("Content-Length", str(size))
        disp = "attachment" if attachment else "inline"
        self.send_header("Content-Disposition", f'{disp}; filename="{name}"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        with open(path, "rb") as f:
            self.wfile.write(f.read())

    def do_GET(self):
        route = urllib.parse.urlparse(self.path).path
        if route in SERVED:
            attachment = route not in ("/view", "/view-check")
            return self._pdf(attachment, SERVED[route])
        if route == "/":
            self.path = "/index.html"
        return super().do_GET()

    def do_HEAD(self):
        route = urllib.parse.urlparse(self.path).path
        if route in SERVED:
            size = os.path.getsize(os.path.join(ROOT, SERVED[route]))
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
