"""
HTTP 管理メニュー（時刻設定など）
"""

import schedule_mgr

_HIDDEN_KEY = ""


def _init_key_suffix():
    global _HIDDEN_KEY
    import config

    if config.ENABLE_TOKEN_CHECK:
        _HIDDEN_KEY = "?key=" + config.SECRET_KEY
    else:
        _HIDDEN_KEY = ""


def _link(path):
    return path + _HIDDEN_KEY


def _hidden_input():
    import config

    if config.ENABLE_TOKEN_CHECK:
        return '<input type="hidden" name="key" value="{}">'.format(config.SECRET_KEY)
    return ""


def _page(title, body_html):
    return (
        "<!DOCTYPE html><html><head>"
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        "<title>{}</title></head><body>"
        "<h2>{}</h2>{}</body></html>"
    ).format(title, title, body_html)


def _urldecode(value):
    out = []
    i = 0
    while i < len(value):
        c = value[i]
        if c == "+":
            out.append(" ")
            i += 1
        elif c == "%" and i + 2 < len(value):
            try:
                out.append(chr(int(value[i + 1:i + 3], 16)))
                i += 3
            except ValueError:
                out.append(c)
                i += 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


def _parse_form(body):
    params = {}
    for pair in body.split("&"):
        if "=" not in pair:
            continue
        k, v = pair.split("=", 1)
        params[_urldecode(k.strip())] = _urldecode(v.strip())
    return params


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


def dispatch(method, path, body):
    """
    管理ルートを処理する。
    return: (html, reboot) または None（未処理）
    """
    _init_key_suffix()

    if path == "/admin" or path == "/admin/":
        if method != "GET":
            return _method_not_allowed()
        return _menu_page()

    if path == "/admin/time":
        if method == "GET":
            return _time_form_page()
        if method == "POST":
            return _time_post(body)
        return _method_not_allowed()

    return None


def _method_not_allowed():
    return _page("Error", "<p>Method not allowed</p><p><a href='{}'>Menu</a></p>".format(_link("/admin"))), False


def _menu_page():
    body = (
        "<ul>"
        "<li><a href='{}'>時刻・アーカイブ設定</a></li>"
        "<li><a href='/'>ログ一覧</a></li>"
        "</ul>"
    ).format(_link("/admin/time"))
    return _page("管理メニュー", body), False


def _time_form_page():
    import config

    y, mo, d, h, mi, s = schedule_mgr.get_datetime_tuple()
    ah, am = schedule_mgr.get_archive_time()
    saved_clock = schedule_mgr.has_saved_clock()
    saved_archive = schedule_mgr.has_saved_archive()
    admin_url = "http://{}/admin/time".format(config.IP)

    body = (
        "<p>接続先: <strong>{}</strong>（WiFi: {}）</p>"
        "<p>現在時刻（RTC）: <strong>{}</strong></p>"
        "<p>保存ファイル: {}</p>"
        "<p>アーカイブ予定: <strong>毎日 {}</strong>（前日分を logs/ へ）</p>"
        "<p>アーカイブ保存: {}</p>"
        "<form id='clock-form' method='POST' action='{}'>"
        "{}"
        "<h3>設定する現在時刻</h3>"
        "<p><button type='button' onclick='setBrowserTime()'>"
        "ブラウザの現在時刻を入力</button></p>"
        "<p>年 <input name='year' type='number' value='{}' min='2020' max='2099' size='6'></p>"
        "<p>月 <input name='month' type='number' value='{}' min='1' max='12' size='4'></p>"
        "<p>日 <input name='day' type='number' value='{}' min='1' max='31' size='4'></p>"
        "<p>時 <input name='hour' type='number' value='{}' min='0' max='23' size='4'></p>"
        "<p>分 <input name='minute' type='number' value='{}' min='0' max='59' size='4'></p>"
        "<p>秒 <input name='second' type='number' value='{}' min='0' max='59' size='4'></p>"
        "<h3>ログアーカイブ時刻</h3>"
        "<p>時 <input name='archive_hour' type='number' value='{}' min='0' max='23' size='4'></p>"
        "<p>分 <input name='archive_minute' type='number' value='{}' min='0' max='59' size='4'></p>"
        "<p><button type='submit'>保存して再起動</button></p>"
        "</form>"
        "<p>保存すると /storage/clock.cfg に書き込み、次回起動時も同じ時刻基準を使います。</p>"
        "<p><a href='{}'>管理メニューへ</a></p>"
        "<script>"
        "function setBrowserTime(){{"
        "var d=new Date();"
        "document.querySelector(\"input[name='year']\").value=d.getFullYear();"
        "document.querySelector(\"input[name='month']\").value=d.getMonth()+1;"
        "document.querySelector(\"input[name='day']\").value=d.getDate();"
        "document.querySelector(\"input[name='hour']\").value=d.getHours();"
        "document.querySelector(\"input[name='minute']\").value=d.getMinutes();"
        "document.querySelector(\"input[name='second']\").value=d.getSeconds();"
        "}}"
        "</script>"
    ).format(
        admin_url,
        config.SSID,
        schedule_mgr.format_datetime(),
        "あり (/storage/clock.cfg)" if saved_clock else "なし（未設定）",
        schedule_mgr.format_archive_time(),
        "あり (/storage/archive.cfg)" if saved_archive else "なし（config.py）",
        _link("/admin/time"),
        _hidden_input(),
        y, mo, d, h, mi, s,
        ah, am,
        _link("/admin"),
    )
    return _page("時刻・アーカイブ設定", body), False


def _time_post(body):
    params = _parse_form(body)

    year = _int_param(params, "year", 2026, 2020, 2099)
    month = _int_param(params, "month", 1, 1, 12)
    day = _int_param(params, "day", 1, 1, 31)
    hour = _int_param(params, "hour", 0, 0, 23)
    minute = _int_param(params, "minute", 0, 0, 59)
    second = _int_param(params, "second", 0, 0, 59)

    archive_hour = _int_param(params, "archive_hour", 0, 0, 23)
    archive_minute = _int_param(params, "archive_minute", 5, 0, 59)

    try:
        schedule_mgr.save_clock(year, month, day, hour, minute, second)
        schedule_mgr.save_archive(archive_hour, archive_minute)
    except OSError as e:
        body_html = (
            "<p>保存に失敗しました: {}</p>"
            "<p><a href='{}'>戻る</a></p>"
        ).format(e, _link("/admin/time"))
        return _page("エラー", body_html), False

    body_html = (
        "<p>設定を保存しました。</p>"
        "<p>RTC: {:04}-{:02}-{:02} {:02}:{:02}:{:02}</p>"
        "<p>保存先: /storage/clock.cfg</p>"
        "<p>アーカイブ: 毎日 {:02}:{:02}</p>"
        "<p>まもなく本体を再起動します（HTTP停止ではありません）。</p>"
        "<p>WiFi が一度切れたら 30 秒ほど待ってから再度 AP へ接続してください。</p>"
    ).format(
        year, month, day, hour, minute, second,
        archive_hour, archive_minute,
    )

    return _page("再起動", body_html), True
