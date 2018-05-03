#!/usr/bin/python3

# Copyright 2018 - FosdemX
# This work is free. You can redistribute it and/or modify it under the
# terms of the Do What The Fuck You Want To Public License, Version 2,
# as published by Sam Hocevar. See the COPYING file or http://www.wtfpl.net/
# for more details.

from helpers import get_message


def runner():
    while True:
        message = get_message("output")
        # send that message to the cloud!


if __name__ == "__main__":
    runner()
