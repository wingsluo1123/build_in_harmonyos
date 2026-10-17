#!/usr/bin/env python3
"""wdfs 端到端测试用的最小 WebDAV stub server。

wdfs 启动时会先向目标 WebDAV 资源发一次真实 HTTP OPTIONS 请求
（src/webdav.c: setup_webdav_session -> ne_options）。本 stub 回应
OPTIONS/PROPFIND/GET 并把收到的请求行写入日志，供 test.sh 断言
"wdfs 确实完成了 WebDAV 握手"。

用法: python3 webdav_stub.py <port> <logfile>
"""
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

LOG = ""


def _record(handler, verb):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"{verb} {handler.path}\n")


class DavStubHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "wdfs-stub/1.0"

    def _respond(self, body=b""):
        self.send_response(200)
        self.send_header("DAV", "1,2")
        self.send_header(
            "Allow", "OPTIONS, GET, PUT, DELETE, PROPFIND, MKCOL, MOVE, COPY")
        self.send_header("Content-Type", "text/xml; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_OPTIONS(self):
        _record(self, "OPTIONS")
        self._respond()

    def do_PROPFIND(self):
        _record(self, "PROPFIND")
        self._respond(b'<?xml version="1.0" encoding="utf-8"?>'
                      b'<D:multistatus xmlns:D="DAV:"></D:multistatus>')

    def do_GET(self):
        _record(self, "GET")
        self._respond()

    def do_HEAD(self):
        _record(self, "HEAD")
        self._respond()

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    port = int(sys.argv[1])
    LOG = sys.argv[2]
    with open(LOG, "w", encoding="utf-8"):
        pass
    HTTPServer(("127.0.0.1", port), DavStubHandler).serve_forever()
