# Copyright 2018 - FosdemX
# This work is free. You can redistribute it and/or modify it under the
# terms of the Do What The Fuck You Want To Public License, Version 2,
# as published by Sam Hocevar. See the COPYING file or http://www.wtfpl.net/
# for more details.

from logging import getLogger
from signal import SIGUSR1, SIGTERM
from datetime import datetime, timedelta
from subprocess import Popen
from os import kill
from redis import Redis
from time import sleep
from json import dumps, loads

import settings  # pragma: no flakes


logger = getLogger("helpers")
redis = Redis()


def get_redis():
    """ wrapper to mock redis """
    return redis


def utcnow():
    """ wrapper for utcnow, for easy mocking """
    return datetime.utcnow()


def d2s(d):
    return d.isoformat()


def timed_loop(period, name="", skip=False):
    """ infinite generator yielding the time every $period """

    # alway sync on a complete second
    logger.info("start timed loop %s period %s", name, period)
    init_delay = float(utcnow().microsecond) / 10 ** 6
    sleep(timedelta(0, 1 - init_delay).total_seconds())

    # *step is the current and next touchpoints
    last_step = utcnow().replace(microsecond=0)
    overrun = False
    while True:
        if not overrun:
            # drop step if overrun
            try:
                yield (utcnow(), last_step)
            except GeneratorExit:
                break
            except:
                # always log any main loop exception, but exit anyway
                logger.exception("%s main loop fail", name)
                break

        next_step, now = last_step + timedelta(0, period), utcnow()
        if (now - next_step).total_seconds() < -(period + 1):
            # clock skew backward in time
            logger.warning("%s clock skew backward, %s, %s",
                           name, next_step, now)
            next_step = utcnow().replace(microsecond=0)
            overrun = True

        if (now - next_step).total_seconds() > period * 10:
            # huge overrun behind, MASSIVE overrun (change of time most likely)
            # reset next_step
            logger.warning("%s massive overrun, %s, %s", name, next_step, now)
            next_step = utcnow().replace(microsecond=0)
            overrun = True
            # FIXME: maybe use monotonic(), truncate utcnow for step
            #        time (real_time not used anyway) and detect
            #        change of time around sleep

        elif now > next_step:
            if not overrun:
                # only warning the first time, no need to flood
                logger.warning("%s took to much time, %s %s", name, next_step, now)
            overrun = True

        else:
            sleep((next_step - now).total_seconds())
            overrun = False

        last_step = next_step


def push_message(qname, event):
    logger.debug("EVENT %s: %s", qname, event)

    # hardcoded, safety limit
    if redis.llen(qname) >= settings.QUEUE_HARD_LIMIT:
        logger.warning("drop event %s: %s", qname, event)
    else:
        redis.rpush(qname, dumps(event))


def get_message(qname):
    return loads(redis.blpop(qname)[1].decode())


def system(cmd, input=None):
    if input:
        fdin = open(input, "rb", 0)
        return Popen(cmd.split(" "), stdin=fdin).wait()
    else:
        return Popen(cmd.split(" ")).wait()


def reboot():
    kill(1, SIGUSR1)


def halt():
    kill(1, SIGTERM)


def qlen(qname=None):
    if qname:
        return get_redis().llen(qname)
    else:
        queues = ["output", "wifi_analyzer"]
        p = get_redis().pipeline()
        for q in queues:
            p = p.llen(q)
        lens = p.execute()
        return list(zip(queues, lens))
