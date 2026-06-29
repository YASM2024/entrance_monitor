# MicroPython 起動時に lib / fonts を import パスへ追加
import sys

for _p in ("/lib", "lib", "/fonts", "fonts"):
    if _p not in sys.path:
        sys.path.append(_p)
