import socket
import time
import os
import _thread

from logger import list_log_files, resolve_log_path
import http_admin
import config


# =========================
# リクエスト読み取り
# =========================
def _recv_request(cl):
    if config.ENABLE_REQ_SIZE_LIMIT:
        max_size = config.HTTP_MAX_REQ_SIZE
    else:
        max_size = 2048

    chunks = [cl.recv(1024)]
    if not chunks[0]:
        return ""

    data = chunks[0]
    while len(data) < max_size:
        header_end = data.find(b"\r\n\r\n")
        if header_end < 0:
            chunk = cl.recv(256)
            if not chunk:
                break
            data += chunk
            continue

        header = data[:header_end].decode()
        content_length = 0
        for line in header.split("\r\n"):
            if line.lower().startswith("content-length:"):
                try:
                    content_length = int(line.split(":", 1)[1].strip())
                except ValueError:
                    content_length = 0
                break

        body_len = len(data) - (header_end + 4)
        if content_length <= 0 or body_len >= content_length:
            break

        chunk = cl.recv(min(256, content_length - body_len))
        if not chunk:
            break
        data += chunk

    try:
        return data.decode()
    except UnicodeError:
        return ""


# =========================
# 送信（部分送信対策）
# =========================
def _send_all(cl, data):
    if isinstance(data, str):
        data = data.encode("utf-8")
    mv = memoryview(data)
    while mv:
        n = cl.send(mv)
        if not n:
            raise OSError("send failed")
        mv = mv[n:]


# =========================
# 停止・再起動フラグ
# =========================
stop_flag = False
reboot_requested = False
last_access = 0


def request_reboot():
    global reboot_requested
    reboot_requested = True


def reboot_pending():
    return reboot_requested


def server():
    global last_access, stop_flag
    try:
        addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
        s = socket.socket()
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(addr)
        s.listen(1)
        print("HTTP server started on port 80")
    except Exception as e:
        print("server() crashed:", e)
        
    # ====== メインループ ======
    while not stop_flag:
        try:
            s.settimeout(1.0)  # 1秒ごとに stop_flag を確認
            cl, remote = s.accept()
        except:
            continue  # タイムアウト → stop_flag チェックへ戻る

        client_ip = remote[0]

        # ====== IP フィルタ ======
        if config.ENABLE_IP_FILTER:
            if client_ip != config.ALLOWED_IP:
                cl.close()
                continue

        # ====== Rate Limit ======
        if config.ENABLE_RATE_LIMIT:
            now = time.time()
            if now - last_access < config.HTTP_RATE_LIMIT_SEC:
                cl.close()
                continue
            last_access = now

        # ====== タイムアウト ======
        if config.ENABLE_TIMEOUT:
            cl.settimeout(config.HTTP_TIMEOUT_SEC)

        # ====== リクエスト読み取り ======
        try:
            req_text = _recv_request(cl)
        except OSError:
            cl.close()
            continue

        # ====== トークン認証 ======
        if config.ENABLE_TOKEN_CHECK:
            if f"key={config.SECRET_KEY}" not in req_text:
                _send_all(cl, "HTTP/1.0 403 Forbidden\r\n\r\nForbidden")
                cl.close()
                continue

        # ====== リクエスト解析 ======
        try:
            request_line = req_text.split("\n")[0]
            parts = request_line.split(" ")
            method = parts[0] if parts else "GET"
            path = parts[1].split("?")[0] if len(parts) > 1 else "/"
        except Exception:
            method = "GET"
            path = "/"

        body_text = ""
        if "\r\n\r\n" in req_text:
            body_text = req_text.split("\r\n\r\n", 1)[1]

        # ====== 管理メニュー ======
        if path.startswith("/admin"):
            result = http_admin.dispatch(method, path, body_text)
            if result is not None:
                html, do_reboot = result
                body = html.encode("utf-8")
                header = (
                    "HTTP/1.0 200 OK\r\n"
                    "Content-Type: text/html; charset=utf-8\r\n"
                    "Content-Length: {}\r\n\r\n".format(len(body))
                )
                _send_all(cl, header)
                _send_all(cl, body)
                cl.close()
                if do_reboot:
                    request_reboot()
                continue

        # ====== ルート：ログ一覧 ======
        if path == "/" or path.startswith("/?"):
            files = list_log_files()

            admin_link = "/admin"
            if config.ENABLE_TOKEN_CHECK:
                admin_link += "?key=" + config.SECRET_KEY

            html = (
                "<!DOCTYPE html><html><head>"
                '<meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width,initial-scale=1">'
                "<title>Log Files</title></head><body>"
                "<h2>Log Files</h2>"
                "<p><a href='{}'>管理メニュー</a></p><ul>"
            ).format(admin_link)
            for f in files:
                if config.ENABLE_TOKEN_CHECK:
                    html += f'<li><a href="/storage/{f}?key={config.SECRET_KEY}">{f}</a></li>'
                else:
                    html += f'<li><a href="/storage/{f}">{f}</a></li>'
            html += "</ul></body></html>"

            body = html.encode("utf-8")
            header = (
                "HTTP/1.0 200 OK\r\n"
                "Content-Type: text/html; charset=utf-8\r\n"
                "Content-Length: {}\r\n\r\n".format(len(body))
            )
            _send_all(cl, header)
            _send_all(cl, body)
            cl.close()
            continue

        # ====== CSV ファイル返却 ======
        if path.startswith("/storage/"):
            filename = path.split("?")[0].lstrip("/").split("/")[-1]
            filepath = resolve_log_path(filename)

            try:
                size = os.stat(filepath)[6]
            except OSError:
                _send_all(cl, "HTTP/1.0 404 Not Found\r\n\r\nFile not found")
                cl.close()
                continue

            header = (
                "HTTP/1.0 200 OK\r\n"
                "Content-Type: text/plain; charset=utf-8\r\n"
                "Content-Disposition: attachment; filename=\"{}\"\r\n"
                "Content-Length: {}\r\n\r\n".format(filename, size)
            )
            _send_all(cl, header)

            with open(filepath, "rb") as f:
                while True:
                    chunk = f.read(1024)
                    if not chunk:
                        break
                    _send_all(cl, chunk)

            cl.close()
            continue

        # ====== その他 ======
        _send_all(cl, "HTTP/1.0 404 Not Found\r\n\r\nNot found")
        cl.close()

    # ====== 停止処理 ======
    try:
        s.close()
    except:
        pass

    print("HTTP server stopped")


def start_http_server():
    global stop_flag
    stop_flag = False
    try:
        _thread.start_new_thread(server, ())
        print("HTTP server started")
    except Exception as e:
        print("thread start failed:", e)

def stop_http_server():
    global stop_flag
    stop_flag = True
    print("HTTP server stopping...")

