# ============================
# APの設定
# ============================

SSID     = "SSID"
PASSWORD = "password"
IP       = "192.168.4.1"
SUBNET   = "255.255.255.0"

# ============================
# セキュリティ機能 ON/OFF
# ============================

ENABLE_IP_FILTER      = False
ENABLE_TOKEN_CHECK    = False
ENABLE_RATE_LIMIT     = False
ENABLE_REQ_SIZE_LIMIT = False
ENABLE_TIMEOUT        = False

# ============================
# セキュリティ機能設定
# ============================

ALLOWED_IP            = "192.168.4.3"
SECRET_KEY            = "abcd1234"
HTTP_RATE_LIMIT_SEC   = 1
HTTP_MAX_REQ_SIZE     = 512
HTTP_TIMEOUT_SEC      = 3

# ============================
# 時刻設定（RTC）
# ============================

ENABLE_CLOCK_SET = True
CLOCK_YEAR       = 2026
CLOCK_MONTH      = 5
CLOCK_DAY        = 20
CLOCK_HOUR       = 0
CLOCK_MINUTE     = 0
CLOCK_SECOND     = 0

# ============================
# ログアーカイブ（毎日・前日分を logs/ へ）
# ============================

ARCHIVE_HOUR   = 0
ARCHIVE_MINUTE = 5

# ============================
# ディスプレイスリープ
# ============================

DISPLAY_SLEEP_SEC = 180

# 警告表示中はスリープしない FSM 状態
DISPLAY_SLEEP_WARNING_STATES = frozenset({
    "OPEN",
    "AUTH_PENDING",
    "ALARM",
})

