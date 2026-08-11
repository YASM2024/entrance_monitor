# shared HTTP helpers (keep small; always imported with admin)
def _urlencode(value):
    out = []
    for ch in str(value):
        o = ord(ch)
        if (48 <= o <= 57) or (65 <= o <= 90) or (97 <= o <= 122) or ch in "-_.~":
            out.append(ch)
        elif ch == " ":
            out.append("+")
        elif o < 128:
            out.append("%{:02X}".format(o))
        else:
            for b in ch.encode("utf-8"):
                out.append("%{:02X}".format(b))
    return "".join(out)


def _link(path, params=None):
    import config
    q = []
    if params:
        for k, v in params.items():
            q.append("{}={}".format(_urlencode(k), _urlencode(v)))
    if config.ENABLE_TOKEN_CHECK:
        q.append("key=" + _urlencode(config.SECRET_KEY))
    return path if not q else path + "?" + "&".join(q)


def _hidden_input():
    import config
    if config.ENABLE_TOKEN_CHECK:
        return '<input type="hidden" name="key" value="{}">'.format(config.SECRET_KEY)
    return ""


def _page(title, body_html):
    return (
        "<!DOCTYPE html><html><head><meta charset=utf-8>"
        '<meta name=viewport content="width=device-width,initial-scale=1">'
        "<title>{}</title></head><body><h2>{}</h2>{}</body></html>"
    ).format(title, title, body_html)


def _urldecode(value):
    if isinstance(value, bytes):
        try:
            value = value.decode("ascii")
        except UnicodeError:
            value = value.decode("latin-1")
    out = bytearray()
    i, n = 0, len(value)
    while i < n:
        c = value[i]
        if c == "+":
            out.append(32)
            i += 1
        elif c == "%" and i + 2 < n:
            try:
                out.append(int(value[i + 1:i + 3], 16))
                i += 3
            except ValueError:
                out.append(ord(c))
                i += 1
        else:
            o = ord(c)
            if o > 255:
                for b in c.encode("utf-8"):
                    out.append(b)
            else:
                out.append(o)
            i += 1
    try:
        return out.decode("utf-8")
    except UnicodeError:
        return out.decode("latin-1")


def _as_str_body(body):
    if body is None:
        return ""
    if isinstance(body, memoryview):
        body = bytes(body)
    if isinstance(body, bytearray):
        body = bytes(body)
    if isinstance(body, bytes):
        try:
            return body.decode()
        except UnicodeError:
            return body.decode("latin-1")
    return str(body)


def _parse_form(body):
    body = _as_str_body(body)
    params = {}
    for pair in body.split("&"):
        if "=" not in pair:
            continue
        k, v = pair.split("=", 1)
        params[_urldecode(k.strip())] = _urldecode(v.strip())
    return params


def _parse_form_list(body, name):
    body = _as_str_body(body)
    values = []
    for pair in body.split("&"):
        if "=" not in pair:
            continue
        k, v = pair.split("=", 1)
        if _urldecode(k.strip()) == name:
            values.append(_urldecode(v.strip()))
    return values


def _int_param(params, name, default, lo, hi):
    try:
        v = int(params.get(name, default))
    except (TypeError, ValueError):
        v = default
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


def _msg_page(title, message, back_href):
    return _page(
        title,
        "<p>%s</p><p><a href='%s'>back</a> / <a href='%s'>menu</a></p>"
        % (message, back_href, _link("/admin")),
    ), False


def _method_not_allowed():
    return _page("Error", "<p>405</p><p><a href='%s'>Menu</a></p>" % _link("/admin")), False


def _buf_find(buf, sub, start=0):
    try:
        return buf.find(sub, start)
    except (TypeError, AttributeError):
        pass
    n, m = len(buf), len(sub)
    if m == 0:
        return start
    i = start
    while i <= n - m:
        j = 0
        while j < m and buf[i + j] == sub[j]:
            j += 1
        if j == m:
            return i
        i += 1
    return -1


def _multipart_parse(body, content_type):
    fields, spans = {}, {}
    if body is None or not content_type:
        return fields, spans
    boundary = None
    for part in content_type.split(";"):
        part = part.strip()
        if part.lower().startswith("boundary="):
            boundary = part.split("=", 1)[1].strip().strip('"')
            break
    if not boundary:
        return fields, spans
    delim = b"--" + boundary.encode()
    n, pos = len(body), 0
    while pos < n:
        i = _buf_find(body, delim, pos)
        if i < 0:
            break
        i += len(delim)
        if i + 1 < n and body[i] == 45 and body[i + 1] == 45:
            break
        if i + 1 < n and body[i] == 13 and body[i + 1] == 10:
            i += 2
        header_end = _buf_find(body, b"\r\n\r\n", i)
        if header_end < 0:
            break
        try:
            headers = bytes(body[i:header_end]).decode()
        except UnicodeError:
            pos = header_end + 4
            continue
        data_start = header_end + 4
        next_b = _buf_find(body, delim, data_start)
        data_end = n if next_b < 0 else next_b
        if next_b >= 0 and data_end >= 2 and body[data_end - 2] == 13 and body[data_end - 1] == 10:
            data_end -= 2
        name = filename = None
        for line in headers.split("\r\n"):
            if not line.lower().startswith("content-disposition:"):
                continue
            for item in line.split(";"):
                item = item.strip()
                low = item.lower()
                if low.startswith("name="):
                    name = item.split("=", 1)[1].strip().strip('"')
                elif low.startswith("filename="):
                    filename = item.split("=", 1)[1].strip().strip('"')
        if name:
            if filename is not None:
                spans[name] = (filename, data_start, data_end)
            else:
                try:
                    fields[name] = bytes(body[data_start:data_end]).decode()
                except UnicodeError:
                    fields[name] = bytes(body[data_start:data_end]).decode("latin-1")
        pos = next_b if next_b >= 0 else n
    return fields, spans


def _write_span(body, start, end, dest_path):
    if start < 0 or end < start:
        raise OSError("bad span")
    with open(dest_path, "wb") as f:
        i = start
        while i < end:
            j = end if i + 512 > end else i + 512
            f.write(body[i:j])
            i = j
    return end - start
