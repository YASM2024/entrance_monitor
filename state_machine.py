import time
import logger
import context
import timer_mgr

from http_server import start_http_server, stop_http_server

# =========================
# 状態定義
# =========================
IDLE         = "IDLE"
OPEN         = "OPEN"
AUTH_PENDING = "AUTH_PENDING"
ENTRY_PENDING= "ENTRY_PENDING"
ENTRY        = "ENTRY"
EXIT         = "EXIT"
ALARM        = "ALARM"

_state = IDLE


# =========================
# 初期化
# =========================
def init():
    global _state
    _state = IDLE
    start_http_server()
    context.reset()
    context.set_server_running(True)
    logger.info("INIT")

# =========================
# getter
# =========================
def get_state():
    return _state


def get_context():
    return context.get()


# =========================
# 状態遷移
# =========================
def _set_state(new_state):
    global _state
    old = _state
    _state = new_state
    logger.info(f"STATE {old} -> {new_state}")


def _now():
    return time.time()


# =========================
# メインハンドラ
# =========================
def handle(event, addinfo = None):

    global _state

    # =================================================
    # IDLE
    # =================================================
    if _state == IDLE:

        if event == "DOOR_OPEN":
            _set_state(OPEN)
            logger.log_event("OPEN")
            timer_mgr.start("OPEN", 5)
            return

        return


    # =================================================
    # OPEN
    # =================================================
    if _state == OPEN:

        if event == "PIR_DETECT":
            _set_state(AUTH_PENDING)
            timer_mgr.start("AUTH", 10)
            return

        if event == "TIMEOUT_OPEN":
            _set_state(AUTH_PENDING)
            timer_mgr.start("AUTH", 10)
            return

        if event == "RFID_OK":
            _set_state(ENTRY_PENDING)
            logger.log_event(f"RFID_OK({addinfo})")
            context.inc_entry()
            return

        return


    # =================================================
    # AUTH_PENDING
    # =================================================
    if _state == AUTH_PENDING:

        if event == "RFID_OK":
            _set_state(ENTRY_PENDING)
            logger.log_event(f"RFID_OK({addinfo})")
            context.inc_entry()
            return

        if event == "TIMEOUT_AUTH":
            _set_state(ALARM)
            logger.log_event("ALARM")
            context.inc_alarm()
            return

        return


    # =================================================
    # ENTRY_PENDING
    # =================================================
    if _state == ENTRY_PENDING:

        if event in ("ENTRY_BTN1", "ENTRY_BTN2", "ENTRY_BTN3", "ENTRY_BTN4"):
            _set_state(ENTRY)
            logger.log_event(f"ENTRY_REASON:{event}")
            return

        if event == "TIMEOUT_ENTRY_PENDING":
            _set_state(ALARM)
            logger.log_event("ENTRY_PENDING_TIMEOUT")
            context.inc_alarm()
            return

        return

    # =================================================
    # ENTRY
    # =================================================
    if _state == ENTRY:

        if event == "EXIT_REQUEST":
            _set_state(EXIT)

            logger.log_event("EXIT")

            context.reset_exit()
            timer_mgr.start("EXIT", 8)

            return

        if event == "SERVER_STOP_REQUEST":
            stop_http_server()
            context.set_server_running(False)
            
            return

        if event == "DOOR_OPEN":
            logger.log_event("ENTRY_DOOR_OPEN_WARNING")
            return

        return


    # =================================================
    # EXIT
    # =================================================
    if _state == EXIT:

        if event == "DOOR_OPEN":
            context.mark_exit_open()
            return

        if event == "DOOR_CLOSE":
            context.mark_exit_cycle()
            return

        if event == "PIR_DETECT":
            context.update_pir()
            return

        if event == "TIMEOUT_EXIT":

            if (_now() - context.last_pir_time()) < 5:
                _set_state(ENTRY_PENDING)
                logger.log_event("EXIT_ABORTED")
            else:
                _set_state(IDLE)
                logger.log_event("EXIT_SUCCESS")

            return


    # =================================================
    # ALARM
    # =================================================
    if _state == ALARM:

        if event == "RFID_OK":
            _set_state(ENTRY_PENDING)
            logger.log_event("RECOVER")
            return

        return