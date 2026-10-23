"""Loopback-only app: JSON + NDJSON progress, no credentials in browser."""
import argparse
import json
import queue
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from .core import RetrievalStore
from .chatbot import Chatbot
from .gms import GMSClientError
from .settings import GMSSettings
from .availability import TopicUnavailableError


def create_server(repo, runtime, port=8765, *, settings_loader=None, store_factory=None, bot_factory=None):
    repo=Path(repo);runtime=Path(runtime)
    settings_loader=settings_loader or GMSSettings.load
    store_factory=store_factory or RetrievalStore
    bot_factory=bot_factory or Chatbot
    worker=ThreadPoolExecutor(max_workers=1);lock=threading.Lock()
    def setup():
        try:
            config=json.loads((repo/'config/retrieval.json').read_text(encoding='utf-8-sig'))
            store=store_factory(repo,runtime,runtime/'models',config);store.check_index()
            return store,bot_factory(store),None
        except Exception:return None,None,'index_not_ready'
    store,bot,start_error=worker.submit(setup).result()
    def health():
        configured=settings_loader(repo).status()['ready']
        return {'ready':not start_error and configured,'error':start_error or (None if configured else 'settings_not_ready'), 'topics':len(bot.topic_listing()['topics']) if bot else 0,'topic_drafts':len(bot.topic_listing()['unsupported_topics']) if bot else 0,'total_topics':len(store.topics) if store else 0,'chunks':len(store.parents) if store else 0,'pipeline':'retrieve → generate'}
    def safe_error(exc):
        if isinstance(exc,TopicUnavailableError):return {'error':'topic_unavailable'}
        if isinstance(exc,GMSClientError):return {'error':exc.code,'http_status':exc.status_code}
        if isinstance(exc,(ValueError,TypeError,KeyError)):return {'error':'validation_failed'}
        return {'error':'internal_error'}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def headers_out(self,status,kind,length=None):
            self.send_response(status);self.send_header('Content-Type',kind)
            if length is not None:self.send_header('Content-Length',str(length))
            self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'")
            self.end_headers()
        def send(self,status,data,kind='application/json; charset=utf-8'):
            raw=data if isinstance(data,bytes) else json.dumps(data,ensure_ascii=False).encode()
            self.headers_out(status,kind,len(raw));self.wfile.write(raw)
        def event(self,data):
            self.wfile.write((json.dumps(data,ensure_ascii=False)+'\n').encode());self.wfile.flush()
        def trusted(self):
            expected='127.0.0.1:'+str(self.server.server_port)
            return self.headers.get('Host')==expected and self.headers.get('Origin') in {None,'http://'+expected}
        def do_GET(self):
            if not self.trusted():return self.send(403,{'error':'origin_rejected'})
            if self.path=='/':return self.send(200,(repo/'web/index.html').read_bytes(),'text/html; charset=utf-8')
            if self.path in {'/app.js','/app.css'}:
                kind='application/javascript; charset=utf-8' if self.path.endswith('.js') else 'text/css; charset=utf-8'
                return self.send(200,(repo/'web'/self.path[1:]).read_bytes(),kind)
            if self.path=='/api/health':return self.send(200,health())
            if self.path=='/api/topics':return self.send(200,bot.topic_listing() if bot else {'topics':[],'unsupported_topics':[]})
            self.send(404,{'error':'not_found'})
        def do_POST(self):
            if self.path not in {'/api/chat','/api/chat/stream','/api/explore'}:return self.send(404,{'error':'not_found'})
            if not self.trusted():return self.send(403,{'error':'origin_rejected'})
            if self.headers.get('Content-Type','').split(';')[0]!='application/json':return self.send(415,{'error':'json_required'})
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=100000:return self.send(413,{'error':'request_too_large'})
                data=json.loads(self.rfile.read(length))
                if not isinstance(data,dict):raise ValueError()
            except (ValueError,TypeError):return self.send(400,{'error':'invalid_request'})
            status=health()
            if not status['ready']:return self.send(503,{'error':status['error']})
            if not lock.acquire(blocking=False):return self.send(429,{'error':'busy'})
            stream=self.path=='/api/chat/stream'
            try:
                if self.path=='/api/explore':return self.send(200,worker.submit(bot.explore,data.get('question')).result())
                kwargs={'selected_ids':data.get('selected_ids'),'external_requested':data.get('external_requested',False)}
                if not stream:return self.send(200,worker.submit(bot.answer,data.get('question'),data.get('history'),**kwargs).result())
                events=queue.Queue();kwargs['progress']=lambda stage:events.put({'type':'progress','stage':stage})
                future=worker.submit(bot.answer,data.get('question'),data.get('history'),**kwargs)
                self.headers_out(200,'application/x-ndjson; charset=utf-8')
                connected=True
                while not future.done() or not events.empty():
                    try:event=events.get(timeout=0.5)
                    except queue.Empty:continue
                    if connected:
                        try:self.event(event)
                        except (BrokenPipeError,ConnectionResetError,OSError):connected=False
                # Wait until work finishes even if browser disconnects, so the shared bot remains serialized.
                try:event={'type':'result','result':future.result()}
                except Exception as exc:event={'type':'error',**safe_error(exc)}
                if connected:
                    try:self.event(event)
                    except (BrokenPipeError,ConnectionResetError,OSError):pass
            except Exception as exc:
                if not stream:self.send(502 if isinstance(exc,GMSClientError) else 422,safe_error(exc))
            finally:lock.release()
    class AppServer(ThreadingHTTPServer):
        daemon_threads=True
        def server_close(self):
            super().server_close()
            worker.shutdown(wait=True)
    try:return AppServer(('127.0.0.1',port),Handler)
    except Exception:
        worker.shutdown(wait=True)
        raise


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument('--runtime',type=Path)
    args=parser.parse_args()
    server=create_server(args.repo,args.runtime or args.repo/'.runtime',args.port)
    print('Local: http://127.0.0.1:'+str(server.server_port),flush=True)
    try:server.serve_forever()
    finally:server.server_close()

if __name__=='__main__':main()
