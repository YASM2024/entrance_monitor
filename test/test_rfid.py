# RC522 (MFRC522) 配線・動作確認（SPI0）
# カードをかざすと UID と認証結果を表示
import time

import rfid_reader

_SCK = 18
_MOSI = 19
_MISO = 16
_CS = 17
_RST = 22
_POLL_MS = 100


def _fmt_uid(uid):
    return ":".join("{:02X}".format(b) for b in uid)


def main():
    rfid_reader.init()

    print("=== rfid_reader test ===")
    print("SPI0  SCK=GP{}  MOSI=GP{}  MISO=GP{}".format(_SCK, _MOSI, _MISO))
    print("      CS=GP{}   RST=GP{}".format(_CS, _RST))
    print("同一 UID は {} 秒間は再表示しない".format(rfid_reader._SUPPRESS_SEC))
    print("Ctrl+C で停止")
    print()

    while True:
        uid = rfid_reader.read()
        if uid is not None:
            valid = rfid_reader.is_valid(uid)
            print("UID: {}  auth={}".format(
                _fmt_uid(uid),
                "OK" if valid else "NG",
            ))

        time.sleep_ms(_POLL_MS)


if __name__ == "__main__":
    main()
