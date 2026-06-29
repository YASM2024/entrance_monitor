# 配線確認専用（VCC/GND・GP9バックライト・LCD SPI+CS/RST/DC）
# 成功時: 画面が 緑 → 赤 → 青 に切り替わる
import time
from machine import Pin, SPI
from ili9341 import Display, color565

LCD_SCK = 6
LCD_MOSI = 7
LCD_DC = 15
LCD_CS = 13
LCD_RST = 14
BL_PIN = 9


def main():
    print("=== display wiring test ===")
    print("SCK=GP{} MOSI=GP{} CS=GP{} RST=GP{} DC=GP{}".format(
        LCD_SCK, LCD_MOSI, LCD_CS, LCD_RST, LCD_DC,
    ))

    # [1] バックライト
    print("[1] GP{} = HIGH (backlight)".format(BL_PIN))
    Pin(BL_PIN, Pin.OUT).value(1)
    print("    まだ真っ暗 -> VCC/GND または LED/BL 配線を確認")
    time.sleep(1)

    # [2] LCD SPI + CS / RST / DC
    print("[2] LCD init (SPI0 + CS/RST/DC)...")
    spi = SPI(
        0,
        baudrate=20000000,
        sck=Pin(LCD_SCK),
        mosi=Pin(LCD_MOSI),
    )
    disp = Display(
        spi,
        dc=Pin(LCD_DC),
        cs=Pin(LCD_CS),
        rst=Pin(LCD_RST),
        width=320,
        height=240,
        rotation=90,
    )

    for name, color in (
        ("GREEN", color565(0, 120, 0)),
        ("RED", color565(200, 0, 0)),
        ("BLUE", color565(0, 0, 200)),
    ):
        disp.clear(color)
        print("[OK] {}".format(name))
        print("    この色が見えれば VCC/GND + SPI + CS/RST/DC は正常")
        time.sleep(2)

    print("=== done ===")


if __name__ == "__main__":
    main()

