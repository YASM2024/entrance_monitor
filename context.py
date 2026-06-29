import time

# =========================
# コンテキスト本体
# =========================
_ctx = {
    # -------------------------
    # EXIT関連
    # -------------------------
    "exit_door_opened": False,
    "exit_door_cycle": False,
    "last_pir_time": 0,

    # -------------------------
    # 認証・履歴
    # -------------------------
    "last_uid": None,
    "last_auth_result": None,

    # -------------------------
    # 監査
    # -------------------------
    "entry_count": 0,
    "alarm_count": 0,

    # -------------------------
    # サーバの状態
    # -------------------------
    "server_running": True,
}


# =========================
# 初期化
# =========================
def init():
    reset()


def reset():
    for k in _ctx:
        _ctx[k] = False if isinstance(_ctx[k], bool) else 0


# =========================
# EXIT制御（純粋データ操作）
# =========================
def reset_exit():
    _ctx["exit_door_opened"] = False
    _ctx["exit_door_cycle"] = False
    _ctx["last_pir_time"] = 0


def mark_exit_open():
    _ctx["exit_door_opened"] = True


def mark_exit_cycle():
    _ctx["exit_door_cycle"] = True


def update_pir():
    _ctx["last_pir_time"] = time.time()


# =========================
# 認証
# =========================
def set_uid(uid):
    _ctx["last_uid"] = uid


def set_auth_result(result):
    _ctx["last_auth_result"] = result


# =========================
# カウンタ
# =========================
def inc_entry():
    _ctx["entry_count"] += 1


def inc_alarm():
    _ctx["alarm_count"] += 1


# =========================
# サーバの状態
# =========================
def set_server_running(flag):
    _ctx["server_running"] = flag


def is_server_running():
    return _ctx["server_running"]


# =========================
# getter
# =========================
def get():
    return _ctx


def last_pir_time():
    return _ctx["last_pir_time"]