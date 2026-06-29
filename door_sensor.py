from machine import Pin
import time

# =========================
# 設定
# =========================
_DOOR_PIN         = 20
_DEBOUNCE_SEC     = 0.1  # 100ms
_pin              = None

# 内部状態  # 0 = CLOSED
_last_state       = 0
_stable_state     = 0
_last_change_time = 0
_reported_state   = 0


# =========================
# 初期化
# =========================
def init():
    global _pin, _last_state, _stable_state, _last_change_time, _reported_state

    _pin = Pin(_DOOR_PIN, Pin.IN, Pin.PULL_UP)

    _last_state = _pin.value()
    _stable_state = _last_state
    _reported_state = _last_state
    _last_change_time = time.ticks_ms()


# =========================
# 内部ユーティリティ
# =========================
def _now_ms():
    return time.ticks_ms()


def _read_raw():
    return _pin.value()


# =========================
# チャタリング除去ロジック
# =========================
def _update_debounce():
    """
    状態が安定するまでdebounce_sec以上同一なら確定
    """

    global _last_state, _stable_state, _last_change_time

    current = _read_raw()
    now = _now_ms()

    # 状態変化検出
    if current != _last_state:
        _last_state = current
        _last_change_time = now
        return

    # 一定時間安定したら確定
    if (now - _last_change_time) >= int(_DEBOUNCE_SEC * 1000):
        _stable_state = current


# =========================
# 外部API
# =========================
def is_open():
    _update_debounce()

    # PULL_UP想定:
    # 0 = 接触 （CLOSE）
    # 1 = 非接触（OPEN）
    return _stable_state == 1


def consume_change():
    """
    安定状態が前回通知以降に変わったら True を1回返す。
    表示スリープ復帰・アイドル計測のエッジ検出用。
    """
    global _reported_state

    _update_debounce()

    if _stable_state != _reported_state:
        _reported_state = _stable_state
        return True
    return False
