import time

# =========================
# タイマ保持領域
# =========================
_timers = {
    "OPEN": None,
    "AUTH": None,
    "EXIT": None,
}

# =========================
# 初期化
# =========================
def init():
    global _timers
    _timers["OPEN"] = None
    _timers["AUTH"] = None
    _timers["EXIT"] = None


# =========================
# タイマ開始
# =========================
def start(name, duration_sec):
    """
    name:
        OPEN / AUTH / EXIT
    """
    _timers[name] = {
        "start": time.time(),
        "duration": duration_sec
    }


# =========================
# タイマ停止
# =========================
def stop(name):
    _timers[name] = None


# =========================
# タイムアウト判定
# =========================
def _expired(timer):
    if timer is None:
        return False
    return (time.time() - timer["start"]) >= timer["duration"]


# =========================
# イベント生成
# =========================
def check_timeouts():
    """
    return:
        event list
    """

    events = []

    # -------------------------
    # OPENタイムアウト
    # -------------------------
    if _expired(_timers["OPEN"]):
        events.append("TIMEOUT_OPEN")
        _timers["OPEN"] = None

    # -------------------------
    # AUTHタイムアウト
    # -------------------------
    if _expired(_timers["AUTH"]):
        events.append("TIMEOUT_AUTH")
        _timers["AUTH"] = None

    # -------------------------
    # EXITタイムアウト
    # -------------------------
    if _expired(_timers["EXIT"]):
        events.append("TIMEOUT_EXIT")
        _timers["EXIT"] = None

    return events


# =========================
# 状態確認（デバッグ用）
# =========================
def debug_dump():
    return _timers