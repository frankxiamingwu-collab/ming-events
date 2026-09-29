#!/usr/bin/env python3
"""本地预览服务器：python3 serve.py [端口]，默认 8686，然后访问 http://127.0.0.1:8686/（服务 ming-events/ 站点根）"""
import http.server, os, socketserver, sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8686
BASE = os.path.dirname(os.path.abspath(__file__))   # 站点根：ming-events/（index.html 所在）


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=BASE, **kw)


with socketserver.TCPServer(("127.0.0.1", PORT), Handler) as httpd:
    print(f"serving {BASE} at http://127.0.0.1:{PORT}/  (Ctrl+C 退出)")
    httpd.serve_forever()
