# admin hub: menu + maintain list. time/maintain are lazy-imported.
import http_util as U

# re-export for http_server / old callers
_parse_form = U._parse_form
_link = U._link
_page = U._page
_msg_page = U._msg_page
_hidden_input = U._hidden_input
_method_not_allowed = U._method_not_allowed


def dispatch(method, path, body, content_type="", query=""):
    q = U._parse_form(query) if query else {}
    if path in ("/admin", "/admin/"):
        return _menu() if method == "GET" else U._method_not_allowed()
    if path in ("/admin/time", "/admin/time/"):
        return _lazy_time(method, body)
    if path == "/admin/upload":
        dest = U._link("/admin/maintain/upload")
        return U._page("go", '<meta http-equiv=refresh content="0;url=%s"><a href="%s">up</a>' % (dest, dest)), False
    if path in ("/admin/maintain", "/admin/maintain/"):
        return _list(q) if method == "GET" else U._method_not_allowed()
    if path.startswith("/admin/maintain/"):
        return _lazy_maintain(method, path, body, content_type, q)
    return None


def _lazy_time(method, body):
    import gc
    gc.collect()
    try:
        import http_time
    except MemoryError:
        gc.collect()
        return U._page("Error", "<p>OOM</p><p><a href='%s'>menu</a></p>" % U._link("/admin")), False
    return http_time.dispatch(method, body)


def _lazy_maintain(method, path, body, ct, q):
    import gc
    gc.collect()
    try:
        if gc.mem_free() < 16000:
            return "<html><body>busy <a href='%s'>back</a></body></html>" % U._link("/admin/maintain"), False
    except Exception:
        pass
    gc.collect()
    try:
        import http_maintain
    except MemoryError:
        gc.collect()
        return U._page("Error", "<p>OOM</p><p><a href='%s'>back</a></p>" % U._link("/admin/maintain")), False
    return http_maintain.dispatch(method, path, body, ct, q)


def _menu():
    return U._page(
        "Menu",
        "<ul><li><a href='%s'>time</a></li><li><a href='%s'>maintain</a></li>"
        "<li><a href='%s'>logs</a></li></ul>"
        % (U._link("/admin/time"), U._link("/admin/maintain"), U._link("/logs")),
    ), False


def _list(qparams):
    """軽量一覧（http_maintain を import しない）。"""
    import os, gc
    gc.collect()
    try:
        if gc.mem_free() < 12000:
            return "<html><body>busy <a href='%s'>retry</a></body></html>" % U._link("/admin/maintain"), False
    except Exception:
        pass
    d = str(qparams.get("dir", "/") or "/").replace("\\", "/").strip() or "/"
    if ".." in d:
        d = "/"
    if d[0] != "/":
        d = "/" + d
    try:
        if (os.stat(d)[0] & 0x4000) == 0:
            d = "/"
    except OSError:
        d = "/"
    L = U._link
    h = ["<p>"]
    for x in ("/", "/lib", "/storage"):
        h.append("<a href='%s'>%s</a> " % (L("/admin/maintain", {"dir": x}), x))
    h.append(
        "</p><p><a href='%s'>up</a> <a href='%s'>logs</a> <a href='%s'>menu</a></p><b>%s</b><ul>"
        % (L("/admin/maintain/upload", {"dir": d}), L("/admin/maintain/logs"), L("/admin"), d)
    )
    if d != "/":
        parts = d.strip("/").split("/")
        parent = "/" if len(parts) <= 1 else "/" + "/".join(parts[:-1])
        h.append("<li><a href='%s'>..</a></li>" % L("/admin/maintain", {"dir": parent}))
    try:
        names = os.listdir(d)
    except OSError:
        names = []
    if len(names) <= 25:
        names.sort()
    n = 0
    for name in names:
        if name in (".", ".."):
            continue
        if n >= 25:
            h.append("<li>..</li>")
            break
        full = ("/" + name) if d == "/" else (d.rstrip("/") + "/" + name)
        try:
            is_dir = (os.stat(full)[0] & 0x4000) != 0
        except OSError:
            continue
        if is_dir:
            h.append("<li><a href='%s'>%s/</a></li>" % (L("/admin/maintain", {"dir": full}), name))
        else:
            low = name.lower()
            row = name + " "
            if low.endswith(".py") or low.endswith(".txt") or low.endswith(".cfg") or low.endswith(".csv"):
                row += "<a href='%s'>e</a> " % L("/admin/maintain/edit", {"path": full})
            row += "<a href='%s'>p</a> <a href='%s'>d</a>" % (
                L("/admin/maintain/overwrite", {"path": full}),
                L("/admin/maintain/delete", {"path": full, "dir": d}),
            )
            h.append("<li>%s</li>" % row)
        n += 1
        if (n & 3) == 0:
            gc.collect()
    h.append("</ul>")
    body = "".join(h)
    del h
    gc.collect()
    return "<html><body><h2>m</h2>%s</body></html>" % body, False
