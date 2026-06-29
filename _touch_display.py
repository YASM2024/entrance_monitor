from machine import Pin, SPI
from ili9341 import Display, color565
from xglcd_font import XglcdFont

# =========================
# 設定（ハード依存）
# =========================

_LCD_SPI_ID   = 0
_LCD_SCK_PIN  = 6
_LCD_MOSI_PIN = 7
_LCD_DC_PIN   = 15
_LCD_CS_PIN   = 13
_LCD_RST_PIN  = 14
_LCD_ROTATION = 90

_TOUCH_SPI_ID   = 1
_TOUCH_SCK_PIN  = 10
_TOUCH_MOSI_PIN = 11
_TOUCH_MISO_PIN = 8
_TOUCH_CS_PIN   = 12
_TOUCH_IRQ_PIN  = 0

_BL_PIN = 9

_TOUCH_X_MIN = 200
_TOUCH_X_MAX = 3900
_TOUCH_Y_MIN = 200
_TOUCH_Y_MAX = 3900

_SCREEN_W = 320
_SCREEN_H = 240

# ENTRY 4ボタン（タッチ座標と一致させる）
_ENTRY_BTN_W = 150
_ENTRY_BTN_H = 60
_ENTRY_BTNS = (
    (10, 80, "INSPECT", None),
    (160, 80, "MAINT", None),
    (10, 160, "AUDIT", None),
    (160, 160, "OTHER", None),
)

# =========================
# カラーパレット（モダン・ダーク）
# =========================
C_BG      = color565(14, 18, 26)
C_HEADER  = color565(22, 30, 44)
C_CARD    = color565(34, 42, 56)
C_BORDER  = color565(55, 68, 88)
C_ACCENT  = color565(0, 140, 200)
C_TEXT    = 0xFFFF
C_MUTED   = color565(140, 150, 168)
C_OK      = color565(46, 175, 95)
C_WARN    = color565(245, 175, 45)
C_ERR     = color565(215, 55, 55)
C_BTN_INSPECT = color565(35, 95, 165)
C_BTN_MAINT   = color565(175, 95, 35)
C_BTN_AUDIT   = color565(95, 55, 165)
C_BTN_OTHER   = color565(35, 140, 110)
C_BTN_EXIT    = color565(185, 45, 55)
C_BTN_OFF     = color565(70, 78, 95)

_CHAR_W = 12
_CHAR_H = 24

# =========================
# 内部状態
# =========================
_display = None
_font = None
_sm_font = None

_spi_touch = None
_t_cs = None
_t_irq = None
_bl = None

_prev_state = None
_asleep = False


# =========================
# 初期化
# =========================
def init():
    global _display, _font, _sm_font
    global _spi_touch, _t_cs, _t_irq, _bl

    spi = SPI(
        _LCD_SPI_ID,
        baudrate=20000000,
        sck=Pin(_LCD_SCK_PIN),
        mosi=Pin(_LCD_MOSI_PIN)
    )

    _display = Display(
        spi,
        dc=Pin(_LCD_DC_PIN),
        cs=Pin(_LCD_CS_PIN),
        rst=Pin(_LCD_RST_PIN),
        width=_SCREEN_W,
        height=_SCREEN_H,
        rotation=_LCD_ROTATION
    )

    _font = XglcdFont("fonts/Unispace12x24.c", 12, 24)
    _sm_font = XglcdFont("fonts/font6x8.c", 6, 8)

    _display.clear()
    _bl = Pin(_BL_PIN, Pin.OUT)
    _bl.value(1)

    _spi_touch = SPI(
        _TOUCH_SPI_ID,
        baudrate=1000000,
        sck=Pin(_TOUCH_SCK_PIN),
        mosi=Pin(_TOUCH_MOSI_PIN),
        miso=Pin(_TOUCH_MISO_PIN)
    )

    _t_cs = Pin(_TOUCH_CS_PIN, Pin.OUT)
    _t_cs.value(1)
    _t_irq = Pin(_TOUCH_IRQ_PIN, Pin.IN)


# =========================
# UI ヘルパ
# =========================
def _text_cx(x, w, text):
    return x + max(0, (w - len(text) * _CHAR_W) // 2)


def _text_cy(y, h):
    return y + max(0, (h - _CHAR_H) // 2)


def _fill_bg():
    _display.fill_rectangle(0, 0, _SCREEN_W, _SCREEN_H, C_BG)


def _draw_header(title, subtitle=None, accent=C_ACCENT):
    # 高さ48: タイトル24px + サブタイトル8px が重ならないようにする
    _display.fill_rectangle(0, 0, _SCREEN_W, 48, C_HEADER)
    _display.fill_rectangle(0, 0, _SCREEN_W, 4, accent)
    _display.draw_text(14, 10, title, _font, color=C_TEXT)
    if subtitle:
        _display.draw_text(14, 38, subtitle, _sm_font, color=C_MUTED)


def _draw_card(x, y, w, h, accent=C_BORDER):
    _display.fill_rectangle(x, y, w, h, C_CARD)
    _display.draw_rectangle(x, y, w, h, C_BORDER)
    _display.fill_rectangle(x, y, w, 3, accent)


def _draw_pill(x, y, text, bg, fg=C_TEXT):
    pw = len(text) * 6 + 16
    ph = 14
    _display.fill_rectangle(x, y, pw, ph, bg)
    _display.draw_rectangle(x, y, pw, ph, C_BORDER)
    _display.draw_text(x + 8, y + 3, text, _sm_font, color=fg)


def _draw_button(x, y, w, h, label, bg, fg=C_TEXT):
    _display.fill_rectangle(x, y, w, h, bg)
    _display.draw_rectangle(x, y, w, h, C_BORDER)
    _display.fill_rectangle(x, y + h - 4, w, 4, C_BORDER)
    tx = _text_cx(x, w, label)
    ty = _text_cy(y, h)
    _display.draw_text(tx, ty, label, _font, color=fg)


def _draw_icon_block(x, y, w, h, label, color):
    _draw_card(x, y, w, h, accent=color)
    tx = _text_cx(x, w, label)
    ty = y + (h - _CHAR_H) // 2
    _display.draw_text(tx, ty, label, _font, color=color)


_FOOTER_Y = 224  # ENTRY_PENDING 最下段ボタン(y=160,h=60)の直下

def _draw_footer_bar():
    _display.fill_rectangle(0, _FOOTER_Y, _SCREEN_W, _SCREEN_H - _FOOTER_Y, C_HEADER)
    # draw_hline の引数仕様は ili9341 版によって異なるため 1px の矩形で区切り線を描く
    _display.fill_rectangle(0, _FOOTER_Y, _SCREEN_W, 1, C_BORDER)


def _draw_state_idle():
    _fill_bg()
    _draw_header("ACCESS", "Room entry system")
    _draw_card(12, 52, 296, 108, accent=C_ACCENT)
    _display.draw_text(28, 68, "WELCOME", _font, color=C_OK)
    _display.draw_text(28, 110, "KAIKON-LAB.", _font, color=C_TEXT)
    _draw_pill(12, 172, "READY", C_ACCENT)


def _draw_state_open():
    _fill_bg()
    _draw_header("DOOR", "Waiting for entry", accent=C_WARN)
    _draw_icon_block(12, 56, 296, 72, "DOOR OPEN", C_WARN)
    _display.draw_text(28, 148, "Please authenticate", _font, color=C_MUTED)


def _draw_state_auth_pending():
    _fill_bg()
    _draw_header("AUTH", "Card required", accent=C_WARN)
    _draw_card(12, 56, 296, 88, accent=C_WARN)
    _display.draw_text(36, 78, "AUTH...", _font, color=C_WARN)
    _display.draw_text(28, 112, "Touch IC card", _font, color=C_TEXT)
    _draw_pill(120, 160, "WAITING", C_WARN)


def _draw_state_entry_pending():
    _fill_bg()
    _draw_header("ENTRY", "Select reason", accent=C_ACCENT)
    colors = (C_BTN_INSPECT, C_BTN_MAINT, C_BTN_AUDIT, C_BTN_OTHER)
    for i, (bx, by, label, _) in enumerate(_ENTRY_BTNS):
        _draw_button(bx, by, _ENTRY_BTN_W, _ENTRY_BTN_H, label, colors[i])


def _draw_state_entry(context):
    _fill_bg()
    _draw_header("INSIDE", "Room occupied", accent=C_OK)
    _draw_pill(12, 52, "ENTERED", C_OK)
    _draw_button(10, 80, 300, 60, "EXIT", C_BTN_EXIT)
    if context and context.get("server_running"):
        # 表示位置は従来の SHUTDOWN 付近（タッチ生座標は変更なし）
        _draw_button(210, 198, 100, 36, "STOP", C_BTN_OFF)


def _draw_state_exit():
    _fill_bg()
    _draw_header("EXIT", "Verify departure", accent=C_ACCENT)
    _draw_icon_block(12, 56, 296, 72, "EXIT...", C_ACCENT)
    _display.draw_text(28, 148, "Close door after exit", _font, color=C_MUTED)


def _draw_state_alarm():
    _fill_bg()
    _draw_header("ALARM", "Action required", accent=C_ERR)
    _display.fill_rectangle(12, 52, 296, 80, C_ERR)
    _display.draw_rectangle(12, 52, 296, 80, C_TEXT)
    _display.draw_text(48, 80, "ALARM!", _font, color=C_TEXT)
    _display.draw_text(28, 148, "Use authorized card", _font, color=C_MUTED)


def _draw_state_simple(title, subtitle, accent, msg):
    _fill_bg()
    _draw_header(title, subtitle, accent=accent)
    _draw_icon_block(12, 56, 296, 72, msg, accent)


# =========================
# ディスプレイスリープ
# =========================
def is_asleep():
    return _asleep


def enter_sleep():
    global _asleep
    if _asleep:
        return
    _bl.value(0)
    _display.display_off()
    _asleep = True


def exit_sleep():
    global _asleep, _prev_state
    if not _asleep:
        return
    _display.display_on()
    _bl.value(1)
    _asleep = False
    _prev_state = None


def is_touched():
    return _read_touch_raw() is not None


# =========================
# タッチ読み取り
# =========================
def _read_touch_raw():
    if _t_irq.value() == 1:
        return None

    def read(cmd):
        _t_cs.value(0)
        _spi_touch.write(bytearray([cmd]))
        data = _spi_touch.read(2)
        _t_cs.value(1)
        return (data[0] << 8 | data[1]) >> 3

    x = read(0xD0)
    y = read(0x90)
    return x, y


# =========================
# 描画
# =========================
def render(state, context):
    global _prev_state

    if _asleep:
        return

    if state != _prev_state:
        if state == "IDLE":
            _draw_state_idle()
        elif state == "OPEN":
            _draw_state_open()
        elif state == "AUTH_PENDING":
            _draw_state_auth_pending()
        elif state == "ENTRY_PENDING":
            _draw_state_entry_pending()
        elif state == "ENTRY":
            _draw_state_entry(context)
        elif state == "AUTH_OK":
            _draw_state_simple("AUTH", "Verified", C_OK, "ACCESS OK")
        elif state == "AUTH_NG":
            _draw_state_simple("AUTH", "Denied", C_ERR, "ACCESS NG")
        elif state == "DOOR_OPEN":
            _draw_state_simple("DOOR", "Open", C_OK, "DOOR OPEN")
        elif state == "EXIT":
            _draw_state_exit()
        elif state == "ALARM":
            _draw_state_alarm()
        else:
            _fill_bg()
            _draw_header("SYSTEM", "Unknown state", accent=C_WARN)
            _display.draw_text(20, 80, "STATE:", _font, color=C_MUTED)
            _display.draw_text(20, 108, str(state)[:18], _font, color=C_TEXT)

    if context:
        has_footer = "remaining" in context or "user" in context
        # 下段にタッチボタンがある画面ではフッターと重なる
        if has_footer and state != "ENTRY_PENDING":
            _draw_footer_bar()
            line_y = _FOOTER_Y + 6
            if "remaining" in context:
                _display.draw_text(
                    10, line_y,
                    "Time {}s".format(context["remaining"]),
                    _sm_font,
                    color=C_WARN,
                )
                line_y += 10
            if "user" in context:
                _display.draw_text(
                    10, line_y,
                    "User {}".format(context["user"]),
                    _sm_font,
                    color=C_MUTED,
                )

    _prev_state = state


# =========================
# タッチ判定（XPT2046 の生値。画面pxとは別。キャリブ済み範囲）
# 表示ボタン座標: ENTRY 4つ (10,80)(160,80)(10,160)(160,160) 各150x60
#                  EXIT (10,80) 300x60 / STOP 付近 (210,198) 100x36
# =========================
def entry_button1_pressed():
    raw = _read_touch_raw()
    if not raw:
        return False
    x, y = raw
    return (1450 <= x <= 2280) and (550 <= y <= 2000)


def entry_button2_pressed():
    raw = _read_touch_raw()
    if not raw:
        return False
    x, y = raw
    return (1450 <= x <= 2280) and (2260 <= y <= 3760)


def entry_button3_pressed():
    raw = _read_touch_raw()
    if not raw:
        return False
    x, y = raw
    return (2700 <= x <= 3520) and (550 <= y <= 2000)


def entry_button4_pressed():
    raw = _read_touch_raw()
    if not raw:
        return False
    x, y = raw
    return (2700 <= x <= 3520) and (2260 <= y <= 3760)


def exit_button_pressed():
    raw = _read_touch_raw()
    if not raw:
        return False
    x, y = raw
    return (1492 <= x <= 2270) and (530 <= y <= 3712)


def shutdown_button_pressed():
    raw = _read_touch_raw()
    if not raw:
        return False
    x, y = raw
    return (3356 <= x <= 3670) and (2830 <= y <= 3830)
