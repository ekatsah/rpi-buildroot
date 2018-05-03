#!/usr/bin/python3

# Copyright 2018 - FosdemX
# This work is free. You can redistribute it and/or modify it under the
# terms of the Do What The Fuck You Want To Public License, Version 2,
# as published by Sam Hocevar. See the COPYING file or http://www.wtfpl.net/
# for more details.

from logging import getLogger

from helpers import push_message, timed_loop, d2s

import settings  # pragma: no flakes


logger = getLogger("fakegps")


def runner():
    for _, step_time in timed_loop(5, name="fakegps"):
        # we should probably open /dev/ttyXX the serial of
        # the gps ship and parse the output

        push_message("wifi_analyzer", {
            "event": "new_position",
            "timestamp": d2s(step_time),
            "latitude": 50.819658,
            "longitude": 4.398903,
        })


if __name__ == "__main__":
    runner()
