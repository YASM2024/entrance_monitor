import socket, time, os, gc, _thread
from logger import list_log_files, resolve_log_path
import http_admin, config

_DEF_MAX = 20480
stop_flag = False
reboot_requested = False
last_access = 0
_AUTH = "/storage/auth.cfg"


def max_req_size():
    try:
        size = int(getattr(config, "HTTP_MAX_REQ_SIZE", _DEF_MAX))
    except (TypeError, ValueError):
        size = _DEF_MAX
    return 1024 if size < 1024 else size


def request_reboot():
    global reboot_requested
    reboot_requested = True


def reboot_pending():
    return reboot_requested


def _recv_request(cl):
    mx = max_req_size()
    gc.collect()
    first = cl.recv(512)
    if not first:
        return b"", False
    buf = first
    while b"\r\n\r\n" not in buf and len(buf) < mx:
        chunk = cl.recv(256)
        if not chunk:
            break
        buf += chunk
    he = buf.find(b"\r\n\r\n")
    if he < 0:
        return buf, len(buf) >= mx
    clen = 0
    for line in buf[:he].split(b"\r\n"):
        if line.lower().startswith(b"content-length:"):
            try:
                clen = int(line.split(b":", 1)[1].strip())
            except ValueError:
                clen = 0
            break
    total = he + 4 + clen
    if clen < 0 or total > mx:
        return buf, True
    if clen == 0:
        return buf, False
    out = bytearray(total)
    n = len(buf) if len(buf) < total else total
    out[:n] = buf[:n]
    del buf
    filled = n
    gc.collect()
    while filled < total:
        need = total - filled
        chunk = cl.recv(512 if need > 512 else need)
        if not chunk:
            break
        out[filled:filled + len(chunk)] = chunk
        filled += len(chunk)
    if filled < total:
        return out[:filled], False
    return out, False


def _hdr(hb, name):
    p = name.lower() + b":"
    for line in hb.split(b"\r\n"):
        if line.lower().startswith(p):
            return line.split(b":", 1)[1].strip().decode()
    return ""


def _send_all(cl, data):
    if isinstance(data, str):
        data = data.encode("utf-8")
    mv = memoryview(data)
    while mv:
        n = cl.send(mv)
        if not n:
            raise OSError("send failed")
        mv = mv[n:]


def _send_text(cl, status, ctype, text):
    body = text.encode("utf-8") if isinstance(text, str) else text
    _send_all(
        cl,
        "{}\r\nContent-Type: {}\r\nContent-Length: {}\r\nConnection: close\r\n\r\n".format(
            status, ctype, len(body)
        ),
    )
    _send_all(cl, body)


def _plain(cl, code, msg):
    _send_all(cl, "HTTP/1.0 {}\r\nConnection: close\r\n\r\n{}".format(code, msg))


def _auth_ok(user, password):
    try:
        with open(_AUTH, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line[0] == "#" or ":" not in line:
                    continue
                u, p = line.split(":", 1)
                if u == user and p == password:
                    return True
    except OSError:
        pass
    return False


def _akey():
    return ("?key=" + config.SECRET_KEY) if config.ENABLE_TOKEN_CHECK else ""


def _handle_client(cl, remote):
    global last_access
    gc.collect()
    if config.ENABLE_IP_FILTER and remote[0] != config.ALLOWED_IP:
        return
    if config.ENABLE_RATE_LIMIT:
        now = time.time()
        if now - last_access < config.HTTP_RATE_LIMIT_SEC:
            return
        last_access = now
    if config.ENABLE_TIMEOUT:
        cl.settimeout(config.HTTP_TIMEOUT_SEC)
    try:
        req, too_large = _recv_request(cl)
    except OSError:
        return
    if not req:
        return
    if too_large:
        code = "413 Too Large" if config.ENABLE_REQ_SIZE_LIMIT else "400 Bad Request"
        _plain(cl, code, "too large max=%d" % max_req_size())
        return

    he = req.find(b"\r\n\r\n")
    if he < 0:
        hb, body = req, b""
    else:
        hb, body = req[:he], memoryview(req)[he + 4:]
    try:
        parts = hb.split(b"\r\n", 1)[0].decode().split(" ")
        method = parts[0] if parts else "GET"
        raw = parts[1] if len(parts) > 1 else "/"
        path, query = (raw.split("?", 1) + [""])[:2] if "?" in raw else (raw, "")
    except Exception:
        method, path, query = "GET", "/", ""

    if config.ENABLE_TOKEN_CHECK and path != "/":
        if (b"key=" + config.SECRET_KEY.encode()) not in req:
            _plain(cl, "403 Forbidden", "Forbidden")
            return

    ct = _hdr(hb, b"content-type")

    if path.startswith("/admin"):
        gc.collect()
        if isinstance(body, memoryview):
            body = bytes(body)
        try:
            del req
            del hb
        except NameError:
            pass
        gc.collect()
        try:
            result = http_admin.dispatch(method, path, body, ct, query)
        except MemoryError:
            gc.collect()
            _plain(cl, "500 Internal Server Error", "OOM")
            return
        except Exception as e:
            _plain(cl, "500 Internal Server Error", "Error: %s" % e)
            return
        try:
            del body
        except NameError:
            pass
        gc.collect()
        if result is not None:
            if not isinstance(result, (list, tuple)) or len(result) != 2:
                _plain(cl, "500 Internal Server Error", "bad")
                return
            html, do_rb = result
            if not isinstance(html, str):
                if isinstance(html, (list, tuple)) and html and isinstance(html[0], str):
                    html, do_rb = html[0], bool(html[1]) if len(html) > 1 else do_rb
                else:
                    _plain(cl, "500 Internal Server Error", "bad")
                    return
            _send_text(cl, "HTTP/1.0 200 OK", "text/html; charset=utf-8", html)
            if do_rb:
                request_reboot()
            return

    if path == "/":
        if method == "POST":
            p = http_admin._parse_form(body)
            if _auth_ok(p.get("u", ""), p.get("p", "")):
                dest = "/admin?key=" + config.SECRET_KEY
                html = (
                    "<html><head><meta charset=utf-8>"
                    "<meta http-equiv=refresh content='0;url=%s'></head>"
                    "<body>OK <a href='%s'>admin</a></body></html>" % (dest, dest)
                )
            else:
                html = "<html><body>NG <a href='/'>back</a></body></html>"
            _send_text(cl, "HTTP/1.0 200 OK", "text/html; charset=utf-8", html)
            return
        html = (
            "<html><head><meta charset=utf-8>"
            "<meta name=viewport content='width=device-width,initial-scale=1'>"
            "</head><body><h2>Login</h2><form method=POST action=/>"
            "<p>u <input name=u></p><p>p <input name=p type=password></p>"
            "<p><button>login</button></p></form></body></html>"
        )
        _send_text(cl, "HTTP/1.0 200 OK", "text/html; charset=utf-8", html)
        return

    if path in ("/logs", "/logs/"):
        k = _akey()
        h = ["<html><body><h2>logs</h2><p><a href='/admin%s'>menu</a></p><ul>" % k]
        for f in list_log_files():
            h.append("<li><a href='/storage/%s%s'>%s</a></li>" % (f, k, f))
        h.append("</ul></body></html>")
        _send_text(cl, "HTTP/1.0 200 OK", "text/html; charset=utf-8", "".join(h))
        return

    if path.startswith("/storage/"):
        fn = path.split("?")[0].rstrip("/").split("/")[-1]
        fp = resolve_log_path(fn)
        try:
            size = os.stat(fp)[6]
        except OSError:
            _plain(cl, "404 Not Found", "missing")
            return
        _send_all(
            cl,
            'HTTP/1.0 200 OK\r\nContent-Type: text/plain; charset=utf-8\r\n'
            'Content-Disposition: attachment; filename="%s"\r\n'
            "Content-Length: %d\r\nConnection: close\r\n\r\n" % (fn, size),
        )
        with open(fp, "rb") as f:
            while True:
                chunk = f.read(512)
                if not chunk:
                    break
                _send_all(cl, chunk)
        return

    _plain(cl, "404 Not Found", "Not found")


def server():
    global stop_flag
    try:
        addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
        s = socket.socket()
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(addr)
        s.listen(1)
        print("HTTP on :80")
    except Exception as e:
        print("server fail:", e)
        return
    while not stop_flag:
        try:
            s.settimeout(1.0)
            cl, remote = s.accept()
        except Exception:
            continue
        try:
            _handle_client(cl, remote)
        except MemoryError:
            try:
                gc.collect()
                _plain(cl, "500 Internal Server Error", "OOM")
            except Exception:
                pass
        except Exception as e:
            print("HTTP err:", e)
            try:
                _plain(cl, "500 Internal Server Error", "Error")
            except Exception:
                pass
        finally:
            try:
                cl.close()
            except Exception:
                pass
            gc.collect()
    try:
        s.close()
    except Exception:
        pass
    print("HTTP stop")


def start_http_server():
    global stop_flag
    stop_flag = False
    try:
        _thread.start_new_thread(server, ())
        print("HTTP start")
    except Exception as e:
        print("thread fail:", e)


def stop_http_server():
    global stop_flag
    stop_flag = True
    print("HTTP stopping")
