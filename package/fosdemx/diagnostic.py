#!/usr/bin/python3

# Copyright 2018 - FosdemX
# This work is free. You can redistribute it and/or modify it under the
# terms of the Do What The Fuck You Want To Public License, Version 2,
# as published by Sam Hocevar. See the COPYING file or http://www.wtfpl.net/
# for more details.


from os import statvfs
from math import floor
from logging import getLogger
from time import monotonic

from helpers import push_message, timed_loop, utcnow, get_redis, d2s

import settings  # pragma: no flakes

logger = getLogger("diagnostic")


def runner():
    start_time = monotonic()
    start_dt = utcnow()
    redis = get_redis()

    for _, step_time in timed_loop(10, name="diagnostic"):
        # ram info, let's parse /proc/meminfo
        mems = open("/proc/meminfo").read().split("\n")[:5]
        mems = [l[:-3].replace(" ", "").split(":") for l in mems]
        mems = {k: int(v) for k, v in mems}

        # disk, redis, loadavg
        rootfs = statvfs("/")
        r_info = redis.info()
        queue_size = redis.llen("output")
        loadavg = open("/proc/loadavg").read().split(" ")[:3]

        # clock derivation
        runtime_dt = utcnow() - start_dt
        runtime = monotonic() - start_time
        derivation = runtime - runtime_dt.total_seconds()
        uptime = float(open("/proc/uptime").read().split(" ")[0])

        # error counters
        log_name = [k.decode() for k in redis.keys("log_*")]
        if log_name:
            log_counts = [int(c) for c in redis.mget(log_name)]
            logs = dict(zip(log_name, log_counts))
        else:
            logs = {}

        # eth1 tx/rx stats
        try:
            path = "/sys/class/net/wlan0/statistics/"
            target = ["tx_bytes", "tx_packets", "rx_bytes", "rx_packets"]
            wlan0 = {t: int(open(path + t).read()) for t in target}
        except:
            wlan0 = {}

        info = {
            "event": "board_status",
            "timestamp": d2s(step_time),

            # disk/nand status
            "rootfs_blocks": rootfs.f_bsize * rootfs.f_blocks,
            "rootfs_free": rootfs.f_bsize * rootfs.f_bfree,
            "rootfs_available": rootfs.f_bsize * rootfs.f_bavail,

            # redis info
            "redis_size": r_info["used_memory"],
            "redis_size_peak": r_info["used_memory_peak"],
            "redis_ops": r_info["instantaneous_ops_per_sec"],

            # load
            "loadavg1": float(loadavg[0]),
            "loadavg5": float(loadavg[1]),
            "loadavg15": float(loadavg[2]),

            # ram info
            "mem_total": mems["MemTotal"],
            "mem_free": mems["MemFree"],
            "mem_available": mems["MemAvailable"],
            "mem_buffers": mems["Buffers"],
            "mem_cached": mems["Cached"],

            # connection
            "queue_size": queue_size,

            # clock
            "derivation": derivation,
            "uptime": floor(uptime),
        }
        info.update(wlan0)
        info.update(logs)

        push_message("output", info)


if __name__ == "__main__":
    runner()
