# Copyright 2018 - FosdemX
# This work is free. You can redistribute it and/or modify it under the
# terms of the Do What The Fuck You Want To Public License, Version 2,
# as published by Sam Hocevar. See the COPYING file or http://www.wtfpl.net/
# for more details.

from logging import Handler
from redis import Redis


redis = None


class RedisCounter(Handler):
    def emit(self, record):
        global redis

        try:
            if redis is None:
                redis = Redis()

            redis.incr("log_%s_count" % record.levelname.lower())

        except:
            # never fail, it will flood the log (WE ARE THE LOG!)
            pass
