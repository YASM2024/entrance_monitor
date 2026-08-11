# maintain: keep under ~6KB so Pico can import
import os,gc
import http_util as A
E=8192
EX=(".py",".cfg",".txt",".csv")
BD=("/","/lib","/fonts","/storage","/storage/logs","/storage/tmp")
UD=(("/","/"),("/lib/","/lib/"),("/fonts/","/fonts/"))

def dispatch(m,p,body,ct,q):
 gc.collect()
 if p in("/admin/maintain","/admin/maintain/"):
  return _list(q)if m=="GET"else A._method_not_allowed()
 if p=="/admin/maintain/upload":
  return _ug(q)if m=="GET"else(_up(body,ct)if m=="POST"else A._method_not_allowed())
 if p=="/admin/maintain/logs":
  return _lg()if m=="GET"else(_lp(body)if m=="POST"else A._method_not_allowed())
 if p=="/admin/maintain/edit":
  return _eg(q)if m=="GET"else A._method_not_allowed()
 if p=="/admin/maintain/save":
  return _ep(body)if m=="POST"else A._method_not_allowed()
 if p=="/admin/maintain/delete":
  return _dg(q)if m=="GET"else(_dp(body)if m=="POST"else A._method_not_allowed())
 if p=="/admin/maintain/overwrite":
  return _pg(q)if m=="GET"else(_pp(body,ct)if m=="POST"else A._method_not_allowed())
 return None

def _n(r):
 if r is None:return None
 s=str(r).replace("\\","/").strip()or"/"
 if s[0]!="/":s="/"+s
 a=[]
 for x in s.split("/"):
  if x in("","."):continue
  if x=="..":return None
  a.append(x)
 return"/"+"/".join(a)if a else"/"

def _par(p):
 p=_n(p)
 if not p or p=="/":return"/"
 a=p.strip("/").split("/")
 return"/"if len(a)<=1 else"/"+"/".join(a[:-1])

def _id(p):
 try:return(os.stat(p)[0]&0x4000)!=0
 except OSError:return False

def _sz(p):
 try:return os.stat(p)[6]
 except OSError:return -1

def _ed(p):
 pl=p.lower()
 for e in EX:
  if pl.endswith(e):return True
 return False

def _esc(t):
 return str(t).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")

def _base(n):
 if not n:return""
 n=n.replace("\\","/").split("/")[-1].strip()
 return""if(not n or n in("..",".")or"/"in n or"\\"in n)else n

def _ok(fn):
 import config
 al=getattr(config,"HTTP_UPLOAD_ALLOWED_EXT",(".py",".cfg",".txt"))
 fl=fn.lower()
 for e in al:
  if fl.endswith(e.lower()):return True
 return False

def _ud(v):
 r=(v or"/").replace("\\","/").strip()
 if not r.startswith("/"):r="/"+r
 if r!="/"and not r.endswith("/"):r+="/"
 for p,_ in UD:
  if r==p or r.rstrip("/")==p.rstrip("/"):return p
 return"/"

def _md(path):
 if path in("/",""):return
 d=path.rstrip("/")
 try:os.listdir(d)
 except OSError:os.mkdir(d)

def _okw(path,n,rb,back):
 msg="wrote %s (%dB)"%(_esc(path),n)
 if rb:return A._page("ok","<p>%s. rebooting...</p>"%msg),True
 return A._msg_page("ok",msg,back)

def _ws(body,a,b,path,rb,back):
 try:n=A._write_span(body,a,b,path)
 except OSError as e:return A._msg_page("Error",str(e),back)
 gc.collect();return _okw(path,n,rb,back)

def _list(q):
 d=_n(q.get("dir","/"))
 if d is None:return A._msg_page("Error","bad",A._link("/admin/maintain"))
 if not _id(d):d="/"
 sc="|".join("<a href='%s'>%s</a>"%(A._link("/admin/maintain",{"dir":x}),x)for x in BD)
 h=["<p>%s</p><p><a href='%s'>new</a> <a href='%s'>logs</a> <a href='%s'>menu</a></p><b>%s</b><ul>"%(
  sc,A._link("/admin/maintain/upload",{"dir":d}),A._link("/admin/maintain/logs"),A._link("/admin"),_esc(d))]
 if d!="/":h.append("<li><a href='%s'>..</a></li>"%A._link("/admin/maintain",{"dir":_par(d)}))
 try:names=os.listdir(d)
 except OSError:names=[]
 names.sort();n=0
 for name in names:
  if name in("","..")or n>=25:break
  if name==".":continue
  full=("/"+name)if d=="/"else(d.rstrip("/")+"/"+name)
  if _id(full):
   h.append("<li><a href='%s'>%s/</a></li>"%(A._link("/admin/maintain",{"dir":full}),_esc(name)))
  else:
   a=[]
   if _ed(full):a.append("<a href='%s'>e</a>"%A._link("/admin/maintain/edit",{"path":full}))
   a.append("<a href='%s'>p</a>"%A._link("/admin/maintain/overwrite",{"path":full}))
   a.append("<a href='%s'>d</a>"%A._link("/admin/maintain/delete",{"path":full,"dir":d}))
   h.append("<li>%s %d %s</li>"%(_esc(name),_sz(full)," ".join(a)))
  n+=1
 h.append("</ul>");gc.collect()
 return A._page("m","".join(h)),False

def _ug(q):
 import config,http_server
 al=getattr(config,"HTTP_UPLOAD_ALLOWED_EXT",(".py",".cfg",".txt"))
 mx=http_server.max_req_size();sel=_ud(q.get("dir","/"))
 opts="".join('<option value="%s"%s>%s</option>'%(p," selected"if p==sel else"",lb)for p,lb in UD)
 return A._page("up","<p>%s max%dB</p><form method=POST action='%s' enctype=multipart/form-data>%s<p><input name=file type=file required></p><p><input name=save_as size=12></p><p><select name=dest_dir>%s</select></p><p><label><input name=reboot type=checkbox value=1 checked>rb</label></p><p><button>go</button></p></form><p><a href='%s'>back</a></p>"%(",".join(al),mx,A._link("/admin/maintain/upload"),A._hidden_input(),opts,A._link("/admin/maintain",{"dir":sel.rstrip("/")or"/"}))),False

def _up(body,ct):
 gc.collect();f,s=A._multipart_parse(body,ct);back=A._link("/admin/maintain/upload")
 if"file"not in s:return A._msg_page("Error","nofile",back)
 o,a,b=s["file"];name=_base(f.get("save_as",""))or _base(o)
 if not name:return A._msg_page("Error","name",back)
 if not _ok(name):return A._msg_page("Error","ext",back)
 dd=_ud(f.get("dest_dir","/"));dest=("/"+name)if dd=="/"else(dd.rstrip("/")+"/"+name)
 try:_md(dd)
 except OSError as e:return A._msg_page("Error",str(e),back)
 return _ws(body,a,b,dest,f.get("reboot")=="1",A._link("/admin/maintain",{"dir":dd.rstrip("/")or"/"}))

def _lg():
 from logger import list_log_files
 files=list_log_files();h=["<p><a href='%s'>files</a> <a href='%s'>menu</a></p>"%(A._link("/admin/maintain"),A._link("/admin"))]
 if not files:h.append("<p>-</p>");return A._page("logs","".join(h)),False
 h.append("<form method=POST action='%s'>%s<ul>"%(A._link("/admin/maintain/logs"),A._hidden_input()))
 for f in files:h.append("<li><label><input type=checkbox name=log value='%s'>%s</label></li>"%(_esc(f),_esc(f)))
 h.append("</ul><p><button>del</button></p></form>");gc.collect()
 return A._page("logs","".join(h)),False

def _lp(body):
 from logger import delete_log_file
 names=A._parse_form_list(body,"log")
 if not names:return A._msg_page("Error","none",A._link("/admin/maintain/logs"))
 ok=ng=0
 for name in names:
  s,_,_=delete_log_file(name)
  if s:ok+=1
  else:ng+=1
 return A._msg_page("logs","ok=%d ng=%d"%(ok,ng),A._link("/admin/maintain/logs"))

def _eg(q):
 path=_n(q.get("path",""))
 if not path or path=="/"or _id(path)or not _ed(path):return A._msg_page("Error","bad",A._link("/admin/maintain"))
 size=_sz(path)
 if size<0:return A._msg_page("Error","miss",A._link("/admin/maintain"))
 if size>E:return A._msg_page("Error","big",A._link("/admin/maintain",{"dir":_par(path)}))
 try:
  with open(path,"rb")as f:raw=f.read()
  try:text=raw.decode("utf-8")
  except UnicodeError:text=raw.decode("latin-1")
 except OSError as e:return A._msg_page("Error",str(e),A._link("/admin/maintain"))
 del raw;gc.collect();c=_esc(text);del text;gc.collect()
 return A._page("edit","<p>%s %dB</p><form method=POST action='%s'>%s<input type=hidden name=path value='%s'><textarea name=content rows=14 style='width:95%%;font-family:monospace'>%s</textarea><p><label><input name=reboot type=checkbox value=1>rb</label></p><p><button>save</button></p></form><p><a href='%s'>back</a></p>"%(_esc(path),size,A._link("/admin/maintain/save"),A._hidden_input(),_esc(path),c,A._link("/admin/maintain",{"dir":_par(path)}))),False

def _ep(body):
 gc.collect()
 try:
  p=A._parse_form(body);path=_n(p.get("path",""))
  if not path or path=="/"or not _ed(path):return A._msg_page("Error","bad",A._link("/admin/maintain"))
  data=p.get("content","").encode("utf-8")
  if len(data)>E:return A._msg_page("Error","big",A._link("/admin/maintain/edit",{"path":path}))
  rb=p.get("reboot")=="1"
  with open(path,"wb")as f:f.write(data)
  n=len(data);del data;del p;del body;gc.collect()
  return _okw(path,n,rb,A._link("/admin/maintain",{"dir":_par(path)}))
 except MemoryError:
  gc.collect();return A._msg_page("Error","OOM",A._link("/admin/maintain"))
 except Exception as e:
  return A._msg_page("Error",str(e),A._link("/admin/maintain"))

def _dg(q):
 path=_n(q.get("path",""));d=_n(q.get("dir","/"))or"/"
 if not path or path=="/"or _id(path):return A._msg_page("Error","bad",A._link("/admin/maintain"))
 return A._page("del","<p>del %s?</p><form method=POST action='%s'>%s<input type=hidden name=path value='%s'><input type=hidden name=dir value='%s'><p><button>DEL</button></p></form><p><a href='%s'>no</a></p>"%(_esc(path),A._link("/admin/maintain/delete"),A._hidden_input(),_esc(path),_esc(d),A._link("/admin/maintain",{"dir":d}))),False

def _dp(body):
 p=A._parse_form(body);path=_n(p.get("path",""));d=_n(p.get("dir","/"))or"/"
 if not path or path=="/"or _id(path):return A._msg_page("Error","bad",A._link("/admin/maintain"))
 try:os.remove(path)
 except OSError as e:return A._msg_page("Error",str(e),A._link("/admin/maintain",{"dir":d}))
 return A._msg_page("ok","deleted "+_esc(path),A._link("/admin/maintain",{"dir":d}))

def _pg(q):
 import http_server
 path=_n(q.get("path",""))
 if not path or path=="/"or _id(path):return A._msg_page("Error","bad",A._link("/admin/maintain"))
 return A._page("put","<p>put %s %dB max%d</p><form method=POST action='%s' enctype=multipart/form-data>%s<input type=hidden name=path value='%s'><p><input name=file type=file required></p><p><label><input name=reboot type=checkbox value=1>rb</label></p><p><button>go</button></p></form><p><a href='%s'>back</a></p>"%(_esc(path),_sz(path),http_server.max_req_size(),A._link("/admin/maintain/overwrite"),A._hidden_input(),_esc(path),A._link("/admin/maintain",{"dir":_par(path)}))),False

def _pp(body,ct):
 gc.collect();f,s=A._multipart_parse(body,ct);path=_n(f.get("path",""))
 if not path or path=="/":return A._msg_page("Error","bad",A._link("/admin/maintain"))
 back=A._link("/admin/maintain/overwrite",{"path":path})
 if"file"not in s:return A._msg_page("Error","nofile",back)
 _,a,b=s["file"];parent=_par(path)
 if parent!="/"and not _id(parent):return A._msg_page("Error","nopar",A._link("/admin/maintain"))
 return _ws(body,a,b,path,f.get("reboot")=="1",A._link("/admin/maintain",{"dir":parent}))
