"""
時刻設定（RTC）と日次スケジュールをメインループの tick() で実行する。

config.py の CLOCK_* / ARCHIVE_* を参照する。
"""

import time
import machine
import os

_CLOCK_FILE = "/storage/clock.cfg"
_ARCHIVE_FILE = "/storage/archive.cfg"
_tasks = []


# =========================
# 時刻設定
# =========================
def set_datetime(year, month, day, hour, minute, second=0):
    rtc = machine.RTC()
    weekday = _weekday(year, month, day)
    rtc.datetime((year, month, day, weekday, hour, minute, second, 0))


def get_datetime_tuple():
    """(year, month, day, hour, minute, second)"""
    t = time.localtime()
    return (t[0], t[1], t[2], t[3], t[4], t[5])


def format_datetime():
    y, mo, d, h, mi, s = get_datetime_tuple()
    return "{:04}-{:02}-{:02} {:02}:{:02}:{:02}".format(y, mo, d, h, mi, s)


def _weekday(year, month, day):
    try:
        ts = time.mktime((year, month, day, 12, 0, 0, 0, 0))
        return time.localtime(ts)[6]
    except OSError:
        return 0


def _today_key(t=None):
    if t is None:
        t = time.localtime()
    return "{:04}{:02}{:02}".format(t[0], t[1], t[2])


def _minutes_of_day(t):
    return t[3] * 60 + t[4]


def _ensure_storage_dir():
    try:
        os.mkdir("/storage")
    except OSError:
        pass


def ensure_storage():
    """/storage を用意する（clock.cfg 等の保存先）。"""
    _ensure_storage_dir()


def has_saved_clock():
    try:
        os.stat(_CLOCK_FILE)
        return True
    except OSError:
        return False


def save_clock(year, month, day, hour, minute, second=0):
    _ensure_storage_dir()
    with open(_CLOCK_FILE, "w") as f:
        f.write("{},{},{},{},{},{}\n".format(
            year, month, day, hour, minute, second
        ))
    set_datetime(year, month, day, hour, minute, second)


def load_clock():
    try:
        with open(_CLOCK_FILE) as f:
            parts = f.read().strip().split(",")
        if len(parts) < 6:
            return None
        return tuple(int(parts[i]) for i in range(6))
    except (OSError, ValueError):
        return None


def _apply_clock_from_storage():
    saved = load_clock()
    if saved is None:
        return False
    set_datetime(*saved)
    return True


def has_saved_archive():
    try:
        os.stat(_ARCHIVE_FILE)
        return True
    except OSError:
        return False


def save_archive(hour, minute):
    _ensure_storage_dir()
    with open(_ARCHIVE_FILE, "w") as f:
        f.write("{},{}\n".format(hour, minute))


def load_archive():
    try:
        with open(_ARCHIVE_FILE) as f:
            parts = f.read().strip().split(",")
        if len(parts) < 2:
            return None
        return (int(parts[0]), int(parts[1]))
    except (OSError, ValueError):
        return None


def get_archive_time():
    """(hour, minute) — storage → config の順で参照。"""
    saved = load_archive()
    if saved is not None:
        return saved
    import config
    return (config.ARCHIVE_HOUR, config.ARCHIVE_MINUTE)


def format_archive_time():
    h, m = get_archive_time()
    return "{:02}:{:02}".format(h, m)


def _apply_clock_from_config():
    import config

    if not getattr(config, "ENABLE_CLOCK_SET", False):
        return False

    set_datetime(
        config.CLOCK_YEAR,
        config.CLOCK_MONTH,
        config.CLOCK_DAY,
        config.CLOCK_HOUR,
        config.CLOCK_MINUTE,
        getattr(config, "CLOCK_SECOND", 0),
    )
    return True


# =========================
# タスク登録
# =========================
def register_daily(task_id, hour, minute, callback):
    """
    毎日 hour:minute 以降の最初の tick で callback を1回実行する。
    再起動で時刻を過ぎていた場合も、その日のうちに未実行なら実行する。
    """
    _tasks.append({
        "id": task_id,
        "type": "daily",
        "hour": hour,
        "minute": minute,
        "callback": callback,
        "last_run": None,
    })


def register_once(task_id, year, month, day, hour, minute, callback):
    """指定の年月日時分以降の最初の tick で1回だけ実行する。"""
    _tasks.append({
        "id": task_id,
        "type": "once",
        "year": year,
        "month": month,
        "day": day,
        "hour": hour,
        "minute": minute,
        "callback": callback,
        "fired": False,
    })


def _register_builtin_tasks():
    import logger

    ah, am = get_archive_time()
    register_daily(
        "log_archive",
        ah,
        am,
        logger.archive_previous_day,
    )
    print("Archive schedule:", format_archive_time())


# =========================
# 初期化・ポーリング
# =========================
def init():
    global _tasks
    _tasks = []

    ensure_storage()

    if _apply_clock_from_storage():
        print("RTC set from storage:", format_datetime())
    elif _apply_clock_from_config():
        print("RTC set from config:", format_datetime())
    else:
        print("RTC: using current RTC")

    _register_builtin_tasks()


def tick():
    """main.py のループから呼ぶ。"""
    t = time.localtime()
    today_key = _today_key(t)
    now_min = _minutes_of_day(t)

    for task in _tasks:
        if task["type"] == "daily":
            if task["last_run"] == today_key:
                continue
            sched_min = task["hour"] * 60 + task["minute"]
            if now_min < sched_min:
                continue
            _run_task(task, today_key)

        elif task["type"] == "once":
            if task["fired"]:
                continue
            target_min = task["hour"] * 60 + task["minute"]
            if (t[0], t[1], t[2]) < (task["year"], task["month"], task["day"]):
                continue
            if (t[0], t[1], t[2]) > (task["year"], task["month"], task["day"]):
                task["fired"] = True
                continue
            if (t[0], t[1], t[2]) == (task["year"], task["month"], task["day"]):
                if now_min < target_min:
                    continue
            _run_task(task, None, once=True)


def _run_task(task, today_key, once=False):
    try:
        task["callback"]()
    except Exception as e:
        print("schedule_mgr [{}] error:".format(task["id"]), e)

    if once:
        task["fired"] = True
    else:
        task["last_run"] = today_key
