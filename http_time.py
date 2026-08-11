# time / archive settings (lazy-imported from http_admin)
import schedule_mgr
import http_util as U


def dispatch(method, body):
    if method == "GET":
        return _form()
    if method == "POST":
        return _post(body)
    return U._method_not_allowed()


def _form():
    import config
    y, mo, d, h, mi, s = schedule_mgr.get_datetime_tuple()
    ah, am = schedule_mgr.get_archive_time()
    body = (
        "<p>%s / %s</p><p>RTC %s</p><p>arch %s clk=%s arc=%s</p>"
        "<form method=POST action='%s'>%s"
        "<p><button type=button onclick=\"var d=new Date();"
        "document.querySelector('[name=year]').value=d.getFullYear();"
        "document.querySelector('[name=month]').value=d.getMonth()+1;"
        "document.querySelector('[name=day]').value=d.getDate();"
        "document.querySelector('[name=hour]').value=d.getHours();"
        "document.querySelector('[name=minute]').value=d.getMinutes();"
        "document.querySelector('[name=second]').value=d.getSeconds()\">now</button></p>"
        "<p>y<input name=year type=number value=%d min=2020 max=2099 size=4> "
        "m<input name=month type=number value=%d min=1 max=12 size=2> "
        "d<input name=day type=number value=%d min=1 max=31 size=2></p>"
        "<p>H<input name=hour type=number value=%d min=0 max=23 size=2> "
        "M<input name=minute type=number value=%d min=0 max=59 size=2> "
        "S<input name=second type=number value=%d min=0 max=59 size=2></p>"
        "<p>arch H<input name=archive_hour type=number value=%d min=0 max=23 size=2> "
        "M<input name=archive_minute type=number value=%d min=0 max=59 size=2></p>"
        "<p><button>save+rb</button></p></form><p><a href='%s'>menu</a></p>"
    ) % (
        config.IP,
        config.SSID,
        schedule_mgr.format_datetime(),
        schedule_mgr.format_archive_time(),
        1 if schedule_mgr.has_saved_clock() else 0,
        1 if schedule_mgr.has_saved_archive() else 0,
        U._link("/admin/time"),
        U._hidden_input(),
        y, mo, d, h, mi, s, ah, am,
        U._link("/admin"),
    )
    return U._page("time", body), False


def _post(body):
    try:
        p = U._parse_form(body)
    except Exception as e:
        return U._page("err", "<p>%s</p><p><a href='%s'>back</a></p>" % (e, U._link("/admin/time"))), False
    y = U._int_param(p, "year", 2026, 2020, 2099)
    mo = U._int_param(p, "month", 1, 1, 12)
    d = U._int_param(p, "day", 1, 1, 31)
    h = U._int_param(p, "hour", 0, 0, 23)
    mi = U._int_param(p, "minute", 0, 0, 59)
    s = U._int_param(p, "second", 0, 0, 59)
    ah = U._int_param(p, "archive_hour", 0, 0, 23)
    am = U._int_param(p, "archive_minute", 5, 0, 59)
    try:
        schedule_mgr.save_clock(y, mo, d, h, mi, s)
        schedule_mgr.save_archive(ah, am)
    except Exception as e:
        return U._page("err", "<p>%s</p><p><a href='%s'>back</a></p>" % (e, U._link("/admin/time"))), False
    return U._page(
        "rb",
        "<p>saved %04d-%02d-%02d %02d:%02d:%02d arch %02d:%02d</p><p>rebooting...</p>"
        % (y, mo, d, h, mi, s, ah, am),
    ), True
