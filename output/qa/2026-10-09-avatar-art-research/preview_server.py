from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlsplit,unquote
root=Path(__file__).resolve().parents[3]
allowed=(root/'research/2026-10-10-avatar-art',root/'output/qa/2026-10-09-avatar-art-research')
class Handler(SimpleHTTPRequestHandler):
 def do_GET(self):
  p=(root/unquote(urlsplit(self.path).path).lstrip('/')).resolve()
  if not any(p.is_relative_to(base) for base in allowed):
   self.send_error(404);return
  super().do_GET()
 def translate_path(self,path):
  return str((root/unquote(urlsplit(path).path).lstrip('/')).resolve())
ThreadingHTTPServer(('127.0.0.1',5192),Handler).serve_forever()
