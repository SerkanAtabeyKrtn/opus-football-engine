import os, sys, subprocess, threading, webbrowser
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class H(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path=='/api/update':
            p=subprocess.run([sys.executable,str(ROOT/'app'/'update.py')],cwd=str(ROOT/'app'),capture_output=True,text=True,timeout=240)
            body=(p.stdout+'\n'+p.stderr).encode('utf-8')
            self.send_response(200 if p.returncode==0 else 500);self.send_header('Content-Type','text/plain; charset=utf-8');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body);return
        self.send_error(404)
    def log_message(self,format,*args): pass
if __name__=='__main__':
    os.chdir(ROOT); port=8765
    url=f'http://127.0.0.1:{port}/index.html'
    threading.Timer(1.0,lambda:webbrowser.open(url)).start()
    print('OPUS V1.1:',url); ThreadingHTTPServer(('127.0.0.1',port),H).serve_forever()
