#!/usr/bin/env python3
"""Show the native Xvfb framebuffer over a loopback-only HTTP connection."""
import argparse,hashlib,http.server,json,os,pathlib,socket,struct,subprocess,time,urllib.parse,zlib
subprocess._USE_POSIX_SPAWN=False
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--session',type=pathlib.Path,default=pathlib.Path('/storage/Users/currentUser/xmbmon-hdc-20261005-x205'))
parser.add_argument('--work',type=pathlib.Path,default=pathlib.Path('/data/storage/el2/base/haps/entry/files/xmbmon-x205'))
parser.add_argument('--duration',type=int,default=86400)
options=parser.parse_args()
if not 30<=options.duration<=86400:parser.error('duration must be 30..86400 seconds')
S=options.session;W=options.work
E=S/'evidence/local-gui';E.mkdir(exist_ok=True)

def readn(sock,n):
 data=bytearray()
 while len(data)<n:
  part=sock.recv(n-len(data))
  if not part:raise EOFError('X11 connection closed')
  data.extend(part)
 return bytes(data)

class XConnection:
 def __init__(self):
  self.s=socket.create_connection(('127.0.0.1',6205),3)
  self.s.sendall(struct.pack('<BBHHHHH',108,0,11,0,0,0,0))
  h=readn(self.s,8);body=readn(self.s,struct.unpack_from('<H',h,6)[0]*4)
  assert h[0]==1,(h,body)
  vendorlen=struct.unpack_from('<H',body,16)[0];formats=body[21]
  screen=32+((vendorlen+3)//4)*4+formats*8
  self.root=struct.unpack_from('<I',body,screen)[0]
 def reply(self,request):
  self.s.sendall(request)
  while True:
   h=readn(self.s,32)
   if h[0]==0:raise RuntimeError('X11 error '+h.hex())
   if h[0]==1:return h+readn(self.s,struct.unpack_from('<I',h,4)[0]*4)
 def geometry(self,window):
  r=self.reply(struct.pack('<BBHI',14,0,2,window))
  x,y,width,height,border=struct.unpack_from('<hhHHH',r,12)
  return dict(window=window,x=x,y=y,width=width,height=height,border=border)
 def window(self):
  r=self.reply(struct.pack('<BBHI',15,0,2,self.root));n=struct.unpack_from('<H',r,16)[0]
  for wid in struct.unpack_from('<'+'I'*n,r,32):
   g=self.geometry(wid)
   if g['width']>=300 and g['height']>=200:return wid
  raise RuntimeError('xmbmon window not mapped')
 def resize(self,w,h):
  wid=self.window();self.s.sendall(struct.pack('<BBHIHHII',12,0,5,wid,12,0,w,h))
  return self.geometry(wid)
 def expose(self):
  self.s.sendall(struct.pack('<BBHIhhHH',61,1,4,self.window(),0,0,0,0))
  return self.geometry(self.window())

def png():
 data=(W/'display/fb/Xvfb_screen0').read_bytes()
 h=struct.unpack_from('>25I',data);header,version,fmt,depth,width,height,_,order,_,_,_,bpp,stride,_,red,green,blue,_,_,colors,*_=h
 assert version==7 and fmt==2 and depth==24 and bpp==32 and order==0
 assert (red,green,blue)==(0xff0000,0xff00,0xff)
 offset=header+12*colors;rows=[]
 for y in range(height):
  bgra=data[offset+y*stride:offset+y*stride+width*4];row=bytearray(width*3)
  row[0::3]=bgra[2::4];row[1::3]=bgra[1::4];row[2::3]=bgra[0::4];rows.append(b'\0'+row)
 def chunk(kind,payload):return struct.pack('>I',len(payload))+kind+payload+struct.pack('>I',zlib.crc32(kind+payload)&0xffffffff)
 return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>2I5B',width,height,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b''.join(rows)))+chunk(b'IEND',b'')

PAGE='''<!doctype html><meta charset="utf-8"><title>xmbmon · HarmonyOS 本机显示</title>
<style>body{background:#18212b;color:#eef2f5;font:18px system-ui;margin:32px}button{padding:10px 18px;margin:0 12px 16px 0}img{border:1px solid #607080;max-width:100%;image-rendering:auto}p{color:#b6c5d2}</style>
<h1>xmbmon 2.05 · HarmonyOS 本机显示</h1><p>xmbmon、Xvfb 和显示服务均运行于当前鸿蒙设备。每秒刷新。</p>
<button onclick="resize(640,400)">640 × 400</button><button onclick="resize(800,500)">800 × 500</button><span id="status"></span><br><img id="frame" width="900" height="580">
<p>曲线为设备温度；风扇原始读数由独立命令读取。电压未接入。</p>
<script>async function update(){document.getElementById('frame').src='/frame.png?t='+Date.now();let s=await (await fetch('/state.json')).json();document.getElementById('status').textContent=s.geometry.width+' × '+s.geometry.height+' · '+new Date().toLocaleTimeString();}async function resize(w,h){await fetch('/resize?width='+w+'&height='+h);update()}setInterval(update,1000);update();</script>'''

def main():
 graph=json.loads((S/'evidence/conan-partial-graph.json').read_text())
 package=next(pathlib.Path(n['package_folder']) for n in graph['graph']['nodes'].values() if str(n.get('ref','')).startswith('xmbmon/'))
 libs=[str(pathlib.Path(n['package_folder'])/'lib') for n in graph['graph']['nodes'].values() if n.get('package_folder')]
 env=dict(os.environ,LD_LIBRARY_PATH=str(W/'display/lib')+':'+':'.join(libs)+':'+os.environ.get('LD_LIBRARY_PATH',''),DISPLAY='127.0.0.1:205')
 xe=dict(env,LD_PRELOAD=str(W/'display/lib/xvfb_local_paths.so'),X205_XKBCOMP=str(W/'display/bin/xkbcomp'))
 serverlog=(E/'xvfb.log').open('w');clientlog=(E/'xmbmon.log').open('w')
 xvfb=subprocess.Popen([str(W/'display/bin/Xvfb'),':205','-screen','0','900x580x24','-nolisten','local','-nolisten','unix','-listen','tcp','-ac','-noreset','-xkbdir',str(W/'display/share/X11/xkb'),'-fbdir',str(W/'display/fb')],env=xe,stdout=serverlog,stderr=subprocess.STDOUT)
 client=None;webserver=None;x=None
 try:
  deadline=time.monotonic()+10
  while time.monotonic()<deadline:
   if xvfb.poll() is not None:raise RuntimeError('Xvfb exited; see log')
   try:x=XConnection();break
   except OSError:time.sleep(.2)
  assert x
  command=[str(package/'bin/xmbmon'),'-display',env['DISPLAY'],'-geometry','640x400+0+0','-font','fixed','-labelfont','fixed','-sec','1','-count','1','-wsec','60','-tmax','45','-label','OHOS native xmbmon 2.05 - on-device Xvfb']
  client=subprocess.Popen(command,env=env,stdout=clientlog,stderr=subprocess.STDOUT)
  time.sleep(2);assert client.poll() is None
  checks=[]
  def check(name,passed,**detail):checks.append(dict(name=name,**{'pass':passed},**detail))
  g=x.geometry(x.window());check('native client maps 640x400',g['width']==640 and g['height']==400,geometry=g)
  first=png();(E/'01-initial.png').write_bytes(first);time.sleep(4)
  second=png();(E/'02-timer.png').write_bytes(second);check('timer repaints real graph',first!=second,first_sha256=hashlib.sha256(first).hexdigest(),second_sha256=hashlib.sha256(second).hexdigest())
  g=x.resize(800,500);time.sleep(2);(E/'03-resized.png').write_bytes(png());check('resize to 800x500',g['width']==800 and g['height']==500,geometry=g)
  g=x.expose();time.sleep(1);(E/'04-exposed.png').write_bytes(png());check('expose remains alive',client.poll() is None,geometry=g)
  record={'scope':'HarmonyOS-native xmbmon + native Xvfb + native loopback HTTP framebuffer viewer','uid':os.getuid(),'package':str(package),'executable_sha256':hashlib.sha256((package/'bin/xmbmon').read_bytes()).hexdigest(),'xvfb_pid':xvfb.pid,'xmbmon_pid':client.pid,'viewer_pid':os.getpid(),'checks':checks,'passed':sum(c['pass'] for c in checks),'total':len(checks),'browser_visual_review':'pending','arkui_native_window':False}
  (E/'checks.json').write_text(json.dumps(record,indent=2)+'\n');assert all(c['pass'] for c in checks)
  class Handler(http.server.BaseHTTPRequestHandler):
   def do_GET(self):
    path=urllib.parse.urlsplit(self.path)
    if path.path=='/':content=PAGE.encode();kind='text/html; charset=utf-8'
    elif path.path=='/frame.png':content=png();kind='image/png'
    elif path.path in ('/state.json','/resize'):
     if path.path=='/resize':
      q=urllib.parse.parse_qs(path.query);size=(int(q.get('width',['0'])[0]),int(q.get('height',['0'])[0]))
      if size not in ((640,400),(800,500)):self.send_error(400);return
      x.resize(*size)
     content=json.dumps({'geometry':x.geometry(x.window()),'client_alive':client.poll() is None,'timestamp':time.time()}).encode();kind='application/json'
    else:self.send_error(404);return
    self.send_response(200);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(content)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(content)
   def log_message(self,fmt,*args):print(fmt%args,flush=True)
  webserver=http.server.HTTPServer(('127.0.0.1',8205),Handler);webserver.timeout=1
  (E/'ready.json').write_text(json.dumps(record)+'\n');print('LOCAL_GUI_READY',flush=True)
  until=time.monotonic()+options.duration
  while time.monotonic()<until and client.poll() is None and not (S/'local-gui-stop').exists():webserver.handle_request()
 finally:
  if webserver:webserver.server_close()
  if x:x.s.close()
  for process in (client,xvfb):
   if process and process.poll() is None:process.terminate();process.wait(timeout=5)
  serverlog.close();clientlog.close()
  (E/'stopped.json').write_text(json.dumps({'time':time.time(),'viewer_pid':os.getpid()})+'\n')

if __name__=='__main__':main()
