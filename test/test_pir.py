# PIRセンサー配線・動作確認（GP28）
# raw 0=検知なし / raw 1=検知あり（起動後2秒はウォームアップ）
import time

import pir_sensor

_PIR_PIN = 28
_POLL_MS = 100


def main():
    pir_sensor.init()

    print("=== pir_sensor test ===")
    print("GPIO = GP{}".format(_PIR_PIN))
    print("raw 0=NONE  raw 1=MOTION")
    print("起動後 {} 秒はウォームアップ（detect は常に False）".format(pir_sensor._WARMUP_SEC))
    print("Ctrl+C で停止")
    print()

    warmup_done = False
    prev_detect = None
    while True:
        if not warmup_done and (time.time() - pir_sensor._init_time) >= pir_sensor._WARMUP_SEC:
            print("warmup done — 検知開始")
            print()
            warmup_done = True

        raw = pir_sensor._read_raw()
        motion = pir_sensor.detect()

        if warmup_done and motion != prev_detect:
            print("detect: {}  (raw={})".format(
                "MOTION" if motion else "NONE",
                raw,
            ))
            prev_detect = motion

        time.sleep_ms(_POLL_MS)


if __name__ == "__main__":
    main()
