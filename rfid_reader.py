from machine import Pin, SPI
from mfrc522 import MFRC522
import time

# =========================
# 設定
# =========================
_SPI_ID      = 0
_SCK         = 18
_MOSI        = 19
_MISO        = 16
_CS          = 17
_RST         = 22

_SUPPRESS_SEC = 2 # 同一UIDの連続検出抑制（秒）

# 内部状態
_reader         = None
_last_uid       = None
_last_read_time = 0


# =========================
# 初期化
# =========================
def init():
    global _reader

    spi = SPI(
        _SPI_ID,
        baudrate=1000000,
        polarity=0,
        phase=0,
        sck=Pin(_SCK),
        mosi=Pin(_MOSI),
        miso=Pin(_MISO)
    )

    cs = Pin(_CS, Pin.OUT)
    rst = Pin(_RST, Pin.OUT)

    _reader = MFRC522(spi, cs, rst)


# =========================
# UID読み取り
# =========================
def read():
    """
    return:
        uid (tuple) or None
    """

    global _last_uid, _last_read_time

    # カード検出
    (status, _) = _reader.request(_reader.REQIDL)
    if status != _reader.OK:
        return None

    # UID取得
    (status, uid) = _reader.anticoll()
    if status != _reader.OK:
        return None

    uid_tuple = tuple(uid)
    now = time.time()

    # -------------------------
    # 重複抑制
    # -------------------------
    if uid_tuple == _last_uid:
        if (now - _last_read_time) < _SUPPRESS_SEC:
            return None

    # 更新
    _last_uid = uid_tuple
    _last_read_time = now

    return uid_tuple


# =========================
# 認証判定
# =========================
# ホワイトリスト（例）
_WHITELIST = {
    (22, 119, 76, 6, 43),   # ダミーUID
}


def is_valid(uid):
    """
    return:
        True / False
    """
    if uid is None:
        return False

    return uid in _WHITELIST
