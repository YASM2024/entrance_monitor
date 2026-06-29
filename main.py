import time

# =========================
# 外部モジュール（I/O層）
# =========================
import door_sensor      # SPS-320（リードスイッチ）
import pir_sensor       # HC-SR501
import rfid_reader      # RC522
import touch_display    # ILI9341（入出力）
import logger           # ログ出力
import schedule_mgr     # 時刻設定・定期タスク
import timer_mgr        # タイマ管理
import state_machine    # 状態遷移本体（ここがコアロジック）
import config
from wifi_manager import start_wifi_ap
import http_server

# =========================
# イベント定義（そのまま使用）
# =========================
DOOR_OPEN           = "DOOR_OPEN"
DOOR_CLOSE          = "DOOR_CLOSE"
PIR_DETECT          = "PIR_DETECT"
RFID_OK             = "RFID_OK"
RFID_NG             = "RFID_NG"
ENTRY_BTN1          = "ENTRY_BTN1"
ENTRY_BTN2          = "ENTRY_BTN2"
ENTRY_BTN3          = "ENTRY_BTN3"
ENTRY_BTN4          = "ENTRY_BTN4"
EXIT_REQUEST        = "EXIT_REQUEST"
SERVER_STOP_REQUEST = "SERVER_STOP_REQUEST"
TIMEOUT_OPEN        = "TIMEOUT_OPEN"
TIMEOUT_AUTH        = "TIMEOUT_AUTH"
TIMEOUT_EXIT        = "TIMEOUT_EXIT"

# =========================
# 初期化
# =========================
def init():
    
    start_wifi_ap()

    schedule_mgr.init()
    logger.init()

    door_sensor.init()
    pir_sensor.init()
    rfid_reader.init()
    touch_display.init()
    timer_mgr.init()
    state_machine.init()
    logger.info("SYSTEM START")

# =========================
# イベント生成（ポーリング）
# =========================
def poll_events():
    events  = []
    addinfo = None

    # --- ドアセンサ ---
    if door_sensor.is_open():
        events.append(DOOR_OPEN)
    else:
        events.append(DOOR_CLOSE)

    # --- PIR ---
    if pir_sensor.detect():
        events.append(PIR_DETECT)

    # --- RFID ---
    uid = rfid_reader.read()
    addinfo = uid
    if uid:
        if rfid_reader.is_valid(uid):
            events.append(RFID_OK)
        else:
            events.append(RFID_NG)

    # --- ENTRY要求（タッチUI） ---

    if state_machine.get_state() == "ENTRY_PENDING":
        if touch_display.entry_button1_pressed():
            events.append(ENTRY_BTN1)

        if touch_display.entry_button2_pressed():
            events.append(ENTRY_BTN2)
        
        if touch_display.entry_button3_pressed():
            events.append(ENTRY_BTN3)
            
        if touch_display.entry_button4_pressed():
            events.append(ENTRY_BTN4)

    # --- EXIT要求（タッチUI） ---
    if state_machine.get_state() == "ENTRY":
        if touch_display.exit_button_pressed():
            events.append(EXIT_REQUEST)
        if touch_display.shutdown_button_pressed():
            events.append(SERVER_STOP_REQUEST)

    # --- タイムアウト系 ---
    events += timer_mgr.check_timeouts()

    return events, addinfo

# =========================
# ディスプレイスリープ
# =========================
def _has_activity(touched, door_changed, uid):
    return (
        touched
        or door_changed
        or uid is not None
    )


# =========================
# メインループ
# =========================
def main():
    init()
    last_activity = time.time()

    while True:

        if http_server.reboot_pending():
            logger.info("REBOOT")
            http_server.stop_http_server()
            time.sleep(1.5)
            import machine
            machine.reset()

        schedule_mgr.tick()

        touched = touch_display.is_touched()
        door_changed = door_sensor.consume_change()
        events, addinfo = poll_events()

        if touch_display.is_asleep():
            if _has_activity(touched, door_changed, addinfo):
                touch_display.exit_sleep()
                last_activity = time.time()
                logger.log_event("DISPLAY_WAKE")

        for event in events:
            state_machine.handle(event, addinfo)

        state = state_machine.get_state()

        if _has_activity(touched, door_changed, addinfo):
            last_activity = time.time()

        if state in config.DISPLAY_SLEEP_WARNING_STATES:
            last_activity = time.time()
        elif not touch_display.is_asleep():
            if (time.time() - last_activity) >= config.DISPLAY_SLEEP_SEC:
                touch_display.enter_sleep()
                logger.log_event("DISPLAY_SLEEP")

        if not touch_display.is_asleep():
            touch_display.render(state, state_machine.get_context())

        time.sleep(0.1)


# =========================
# 起動
# =========================
if __name__ == "__main__":
    main()

