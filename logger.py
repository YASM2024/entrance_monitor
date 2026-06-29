import time
import os

# =========================
# ログレベル
# =========================
INFO  = "INFO"
WARN  = "WARN"
ERROR = "ERROR"
DEBUG = "DEBUG"

# =========================
# 設定
# =========================
_TMP_DIR = "/storage/tmp"
_LOG_DIR = "/storage/logs"
_RETENTION_DAYS = 14  # ★変更可能

# =========================
# 内部フラグ
# =========================
_enable_debug = True
_current_log_file = None
_current_date_str = None


# =========================
# 初期化
# =========================
def init(debug=True, retention_days=14):
    global _enable_debug, _RETENTION_DAYS

    _enable_debug = debug
    _RETENTION_DAYS = retention_days

    # ディレクトリ作成
    try:
        os.mkdir("/storage")
    except OSError:
        pass
    try:
        os.mkdir(_TMP_DIR)
    except OSError:
        pass
    try:
        os.mkdir(_LOG_DIR)
    except OSError:
        pass

    _rotate_file_if_needed()
    _cleanup_old_logs()

    info("LOGGER INIT")


# =========================
# 当日のログを閲覧
# =========================
def get_today_filename():
    t = time.localtime()
    return "%04d%02d%02d.csv" % (t[0], t[1], t[2])

# =========================
# 時刻取得
# =========================
def _ts_str():
    t = time.localtime()
    return "{:04}-{:02}-{:02} {:02}:{:02}:{:02}".format(
        t[0], t[1], t[2],
        t[3], t[4], t[5]
    )

def _ts_epoch():
    return time.time()

def _date_str():
    t = time.localtime()
    return "{:04}{:02}{:02}".format(t[0], t[1], t[2])


def _yesterday_date_str():
    t = time.localtime(time.time() - 86400)
    return "{:04}{:02}{:02}".format(t[0], t[1], t[2])


# =========================
# ファイル管理
# =========================
def _rotate_file_if_needed():
    global _current_log_file, _current_date_str

    today = _date_str()

    if _current_date_str != today:
        _current_date_str = today
        _current_log_file = "{}/{}.csv".format(_TMP_DIR, today)


def _cleanup_old_tmps():
    t = time.localtime()
    today = "{:04d}{:02d}{:02d}".format(t[0], t[1], t[2])

    for f in os.listdir(_LOG_DIR):
        if f.endswith(".csv") and not f.startswith(today):
            try:
                os.remove("{}/{}".format(_LOG_DIR, f))
            except:
                pass
            

def _cleanup_old_logs():
    now = time.time()
    limit = _RETENTION_DAYS * 86400

    try:
        files = os.listdir(_LOG_DIR)
    except:
        return

    for f in files:
        if not f.endswith(".csv"):
            continue

        path = "{}/{}".format(_LOG_DIR, f)

        try:
            stat = os.stat(path)
            if (now - stat[8]) > limit:  # stat[8] = mtime
                os.remove(path)
        except:
            pass

def file_copy(src, dst):
    try:
        os.remove(dst)
    except:
        pass

    with open(src, "rb") as fsrc:
        with open(dst, "wb") as fdst:
            while True:
                buf = fsrc.read(1024)
                if not buf:
                    break
                fdst.write(buf)

def archive_previous_day():
    """前日分の tmp ログを logs/ へコピー（schedule_mgr から呼ぶ）。"""
    yesterday = _yesterday_date_str()
    filename = yesterday + ".csv"
    src = _TMP_DIR + "/" + filename
    dst = _LOG_DIR + "/" + filename

    try:
        os.stat(src)
        file_copy(src, dst)
        info("ARCHIVE {}".format(filename))
        return True
    except OSError:
        return False


def resolve_log_path(filename):
    """当日分は tmp、それ以外は logs から配信する。"""
    if filename == get_today_filename():
        return _TMP_DIR + "/" + filename
    return _LOG_DIR + "/" + filename


def list_log_files():
    files = []
    try:
        for f in os.listdir(_LOG_DIR):
            if f.endswith(".csv") and not f.startswith("."):
                files.append(f)
    except OSError:
        pass

    today = get_today_filename()
    try:
        os.stat(_TMP_DIR + "/" + today)
        if today not in files:
            files.append(today)
    except OSError:
        pass

    files.sort()
    return files


# =========================
# ベースログ
# =========================
def _log(level, msg):
    global _current_log_file

    ts_str = _ts_str()
    ts_epoch = _ts_epoch()

    line = f"[{ts_str}] [{level}] {msg}"

    # --- コンソール ---
    print(line)

    # --- ファイル ---
    try:
        _rotate_file_if_needed()

        with open(_current_log_file, "a") as f:
            f.write("{},{},{}\n".format(
                ts_str,
                level,
                msg
            ))

    except Exception as e:
        # ログ書き込み失敗は潰す（無限ループ防止）
        print("[LOGGER ERROR]", e)


# =========================
# 情報ログ
# =========================
def info(msg):
    _log(INFO, msg)


def warn(msg):
    _log(WARN, msg)


def error(msg):
    _log(ERROR, msg)


# =========================
# デバッグログ
# =========================
def debug(msg):
    if _enable_debug:
        _log(DEBUG, msg)


# =========================
# イベントログ
# =========================
def log_event(event):
    _log(INFO, f"EVENT:{event}")


# =========================
# 状態遷移ログ
# =========================
def log_state(old, new):
    _log(INFO, f"STATE:{old}->{new}")
