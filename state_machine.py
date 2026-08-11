import time
import logger
import context
import timer_mgr
import config
import rfid_reader

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

EXIT_TIMEOUT_SEC = 12
ENTRY_PENDING_TIMEOUT_SEC = 30
EXIT_QUIET_AFTER_CLOSE_SEC = 2


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


def _enter_entry_pending():
    timer_mgr.stop("OPEN")
    timer_mgr.stop("AUTH")
    _set_state(ENTRY_PENDING)
    timer_mgr.start("ENTRY_PENDING", ENTRY_PENDING_TIMEOUT_SEC)


def _now():
    return time.time()


def _exit_quiet_after_close():
    close_at = context.exit_door_close_time()
    if not close_at:
        return False

    now = _now()
    if (now - close_at) < EXIT_QUIET_AFTER_CLOSE_SEC:
        return False

    if context.last_pir_time() > close_at:
        return False

    return True


def _finish_exit_success():
    timer_mgr.stop("EXIT")
    _set_state(IDLE)
    logger.log_event("EXIT_SUCCESS")


def _finish_exit_aborted():
    timer_mgr.stop("EXIT")
    _enter_entry_pending()
    logger.log_event("EXIT_ABORTED")


def _try_exit_success():
    if context.exit_door_cycle() and _exit_quiet_after_close():
        _finish_exit_success()


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
            _enter_entry_pending()
            logger.log_event("RFID_OK({})".format(rfid_reader.format_log_uid(addinfo)))
            context.inc_entry()
            return

        return


    # =================================================
    # AUTH_PENDING
    # =================================================
    if _state == AUTH_PENDING:

        if event == "RFID_OK":
            _enter_entry_pending()
            logger.log_event("RFID_OK({})".format(rfid_reader.format_log_uid(addinfo)))
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
            timer_mgr.stop("ENTRY_PENDING")
            _set_state(ENTRY)
            label = config.ENTRY_REASON_LABELS.get(event, event)
            logger.log_event("ENTRY_REASON:{}".format(label))
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
            timer_mgr.start("EXIT", EXIT_TIMEOUT_SEC)

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
            if context.exit_door_opened():
                context.mark_exit_door_closed()
                _try_exit_success()
            return

        if event == "PIR_DETECT":
            if context.exit_door_cycle():
                context.note_exit_pir_after_close()
            else:
                context.note_exit_pir_before_close()
            _try_exit_success()
            return

        if event == "TIMEOUT_EXIT":
            if context.exit_door_cycle() and _exit_quiet_after_close():
                _finish_exit_success()
            elif context.exit_door_cycle():
                _finish_exit_aborted()
            elif context.last_pir_time() and (_now() - context.last_pir_time()) < 5:
                _finish_exit_aborted()
            else:
                _finish_exit_success()

            return


    # =================================================
    # ALARM
    # =================================================
    if _state == ALARM:

        if event == "RFID_OK":
            _enter_entry_pending()
            logger.log_event("RECOVER")
            return

        return