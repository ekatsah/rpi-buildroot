# Copyright 2018 - FosdemX
# This work is free. You can redistribute it and/or modify it under the
# terms of the Do What The Fuck You Want To Public License, Version 2,
# as published by Sam Hocevar. See the COPYING file or http://www.wtfpl.net/
# for more details.

from re import match
from subprocess import Popen, DEVNULL, TimeoutExpired
from time import monotonic, sleep
from logging import getLogger
import json

from helpers import get_redis

import settings  # pragma: no flakes


logger = getLogger("sv")


class Process(object):
    def __init__(self, cmd, redirect_input=True, wait_delay=1):
        self.cmd = cmd
        self.name = self.cmd.split(" ")[0]
        self.wait_delay = wait_delay
        self.start_time = monotonic()
        self.redirect_input = redirect_input
        self.process = None
        self.restart = 0
        self._start()

    def _start(self):
        logger.info("start %s", self.cmd)
        assert self.process is None, "process already started"

        # reset volatile state
        self.last_start_time = monotonic()
        self.ack_dead = False

        try:
            if self.redirect_input:
                self.process = Popen(self.cmd.split(" "), stdin=DEVNULL)
            else:
                self.process = Popen(self.cmd.split(" "))
        except Exception as e:
            logger.exception("popen on %s", self.cmd)

    def stop(self):
        logger.info("stop %s", self.name)
        if self.process is None:
            # not startable/stopped process, nothing to do
            return

        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(self.wait_delay)
                self.process = None
                return
            except TimeoutExpired:
                pass

        if self.process.poll() is None:
            self.process.kill()
            sleep(0.1)
            assert self.process.poll() is not None, "unkillable process"
            self.process = None

    def check(self):
        if self.process is None:
            # not startable/stopped process, nothing to do
            return

        if self.process.poll() is not None:
            # dead process
            duration = monotonic() - self.last_start_time

            if not self.ack_dead:
                # one time only, we may wait before restarting
                self.ack_dead = True
                logger.info("process %s died after %.2fs",
                            self.name, duration)

            if duration > settings.SV_COOLDOWN:
                # cycle the process if waited enough
                self.restart += 1
                self.process = None
                self._start()

    def signal(self, signum):
        if self.process:
            self.process.send_signal(signum)

    def stats(self):
        now = monotonic()
        if self.process is None or self.process.poll() is not None:
            return {
                "alive": False,
                "cmd": self.cmd,
                "name": self.name,
                "total_runtime": now - self.start_time,
                "restart": self.restart,
            }
        else:
            return {
                "alive": True,
                "cmd": self.cmd,
                "name": self.name,
                "pid": self.process.pid,
                "runtime": now - self.last_start_time,
                "total_runtime": now - self.start_time,
                "restart": self.restart,
        }


class SV(object):
    def __init__(self):
        self.processes = []

    def start_process(self, cmd, redirect_input=True, wait_delay=1):
        self.processes.append(Process(cmd, redirect_input, wait_delay))

    def stop_process(self, pattern):
        to_stop = [p for p in self.processes if match(pattern, p.cmd)]
        self.processes = [p for p in self.processes if not match(pattern, p.cmd)]
        for p in reversed(to_stop):
            p.stop()

    def _do_task(self, payload):
        action, data = json.loads(payload.decode())
        if action == "start":
            cmd, delay = data
            self.start_process(cmd, wait_delay=delay)
        elif action == "stop":
            self.stop_process(data)
        elif action == "signal":
            pattern, signum = data
            self.signal(pattern, signum)
        else:
            logger.warning("unknow supervisor action %s, ignore", action)

    def check(self):
        while True:
            # consume redis order
            # FIXME: should find a way to accelerate the blpop in testing
            task = get_redis().blpop(["sv-queue"], 1)
            if task is None:
                break
            else:
                self._do_task(task[1])

        # restart dead process
        for p in self.processes:
            p.check()

        # post stats
        get_redis().set("sv-status", json.dumps(self.stats()))

    def stop_all(self):
        for p in reversed(self.processes):
            p.stop()
        self.processes = []

    def signal(self, pattern, signum):
        for p in self.processes:
            if match(pattern, p.cmd):
                p.signal(signum)

    def stats(self):
        return [p.stats() for p in self.processes]


def start_process(cmd, wait_delay=1):
    get_redis().rpush("sv-queue", json.dumps(["start", [cmd, wait_delay]]))


def stop_process(pattern):
    get_redis().rpush("sv-queue", json.dumps(["stop", pattern]))


def stats_process():
    return json.loads(get_redis().get("sv-status").decode())


def signal_process(pattern, signum):
    get_redis().rpush("sv-queue", json.dumps(["signal", [pattern, signum]]))
