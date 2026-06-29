# ドアセンサー配線・動作確認（GP20, PULL_UP）
# 0 = 接触(CLOSE) / 1 = 非接触(OPEN)
import time

import door_sensor

_DOOR_PIN = 20
_POLL_MS = 100


def main():
    door_sensor.init()

    print("=== door_sensor test ===")
    print("GPIO = GP{} (PULL_UP)".format(_DOOR_PIN))
    print("raw 0=CLOSE  raw 1=OPEN")
    print("Ctrl+C で停止")
    print()

    prev_open = None
    while True:
        raw = door_sensor._read_raw()
        open_ = door_sensor.is_open()

        if open_ != prev_open:
            print("state: {}  (raw={})".format(
                "OPEN" if open_ else "CLOSE",
                raw,
            ))
            prev_open = open_

        time.sleep_ms(_POLL_MS)


if __name__ == "__main__":
    main()
