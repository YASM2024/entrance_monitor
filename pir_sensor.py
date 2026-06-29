from machine import Pin
import time

# =========================
# 設定
# =========================
_PIR_PIN          = 28
_WARMUP_SEC       = 2   # 起動後の安定待ち（秒）
_STABLE_SEC       = 0.2 # デバウンス時間（秒） 少し長め（200ms）
_pin              = None

# 内部状態  # 0
_last_raw         = 0
_stable_state     = 0
_last_change_time = 0
_init_time        = 0


# =========================
# 初期化
# =========================
def init():
    global _pin, _last_raw, _stable_state, _last_change_time, _init_time

    _pin = Pin(_PIR_PIN, Pin.IN)

    _last_raw = _pin.value()
    _stable_state = _last_raw
    _last_change_time = time.ticks_ms()
    _init_time = time.time()


# =========================
# 内部処理
# =========================
def _now_ms():
    return time.ticks_ms()


def _read_raw():
    return _pin.value()


def _update():
    global _last_raw, _stable_state, _last_change_time

    current = _read_raw()
    now = _now_ms()

    # 状態変化検出
    if current != _last_raw:
        _last_raw = current
        _last_change_time = now
        return

    # 一定時間安定したら確定
    if (now - _last_change_time) >= int(_STABLE_SEC * 1000):
        _stable_state = current


# =========================
# 外部API
# =========================
def detect():

    # --- ウォームアップ期間は無視 ---
    if (time.time() - _init_time) < _WARMUP_SEC:
        return False

    _update()

    return _stable_state == 1