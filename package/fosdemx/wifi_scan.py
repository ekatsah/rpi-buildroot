#!/usr/bin/python3

# Copyright 2018 - FosdemX
# This work is free. You can redistribute it and/or modify it under the
# terms of the Do What The Fuck You Want To Public License, Version 2,
# as published by Sam Hocevar. See the COPYING file or http://www.wtfpl.net/
# for more details.

from logging import getLogger
from subprocess import check_output

from helpers import push_message, timed_loop, d2s

import settings  # pragma: no flakes


logger = getLogger("fakegps")


def runner():
    known_wifis = set()

    for _, step_time in timed_loop(5, name="wifi_scan"):
        wifis = check_output("/usr/sbin/wpa_cli scan_results".split(" "))
        wifis = [l.split("\t") for l in wifis.decode().strip().split("\n")[2:]]
        wifis = [(bssid, ssid) for bssid, freq, signal, flags, ssid in wifis]
        wifis = set(wifis)

        for bssid, ssid in known_wifis - wifis:
            # lost wifi
            push_message("wifi_analyzer", {
                "event": "lost_wifi",
                "timestamp": d2s(step_time),
                "bssid": bssid,
                "ssid": ssid,
            })

        for bssid, ssid in wifis - known_wifis:
            # new wifi
            push_message("wifi_analyzer", {
                "event": "new_wifi",
                "timestamp": d2s(step_time),
                "bssid": bssid,
                "ssid": ssid,
            })

        known_wifis = wifis


if __name__ == "__main__":
    runner()
