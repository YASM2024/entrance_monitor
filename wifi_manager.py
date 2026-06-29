import network
import time
import rp2
import config

class WiFiManager:
    def __init__(self, ssid, password, ip="192.168.4.1", subnet="255.255.255.0"):
        self._ssid = ssid
        self._password = password
        self._ip = ip
        self._subnet = subnet
        self._wlan = network.WLAN(network.AP_IF)

    def init(self):
        rp2.country('JP')
        time.sleep(1)
        self._wlan.active(True)
        time.sleep(0.3)

        # AP の固定 IP 設定
        self._wlan.ifconfig((self._ip, self._subnet, self._ip, self._ip))

        # AP 設定
        self._wlan.config(essid=self._ssid, password=self._password)


    @property
    def ip(self):
        return self._wlan.ifconfig()[0]

    @property
    def mac(self):
        mac_bytes = self._wlan.config('mac')
        return ':'.join('%02x' % b for b in mac_bytes)


def start_wifi_ap():
    wifi = WiFiManager(
        config.SSID,
        config.PASSWORD,
        config.IP,
        config.SUBNET
    )
    wifi.init()
    print("AP started:", wifi.ip)
    return wifi

