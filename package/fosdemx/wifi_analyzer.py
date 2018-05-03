#!/usr/bin/python3

# Copyright 2018 - FosdemX
# This work is free. You can redistribute it and/or modify it under the
# terms of the Do What The Fuck You Want To Public License, Version 2,
# as published by Sam Hocevar. See the COPYING file or http://www.wtfpl.net/
# for more details.

from logging import getLogger

from helpers import push_message, get_message

import settings  # pragma: no flakes


logger = getLogger("fakegps")


def runner():
    current_position = None

    while True:
        message = get_message("wifi_analyzer")

        if message["event"] == "new_position":
            current_position = (message["latitude"], message["longitude"])

        if message["event"] == "new_wifi" and current_position:
            push_message("output", {
                "event": "new_wifi",
                "timestamp": message["timestamp"],
                "latitude": current_position[0],
                "longitude": current_position[1],
                "bssid": message["bssid"],
                "ssid": message["ssid"],
            })


if __name__ == "__main__":
    runner()
