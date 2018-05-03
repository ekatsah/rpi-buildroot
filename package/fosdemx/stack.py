#!/usr/bin/python3

# Copyright 2018 - FosdemX
# This work is free. You can redistribute it and/or modify it under the
# terms of the Do What The Fuck You Want To Public License, Version 2,
# as published by Sam Hocevar. See the COPYING file or http://www.wtfpl.net/
# for more details.

from logging import getLogger
from os import waitpid, WNOHANG, environ, lstat, mkdir, strerror
from signal import SIGCHLD, SIGINT, SIGTERM, SIGUSR1, signal
from time import sleep, monotonic
from ctypes import CDLL, get_errno, c_char_p
import traceback

from helpers import utcnow, push_message, d2s, system
from sv import SV

import settings  # pragma: no flakes


logger = getLogger("stack")
should_halt = False
should_reboot = False


def iprint(fmt, *args):
    print("[i%11.6f] %s" % (monotonic(), fmt % args))


def reap_process(signum, frame):
    try:
        waitpid(-1, WNOHANG)
    except Exception as e:
        # since we wait for child in helpers.system(), remove noise
        pass


def halt_request(signum, frame):
    global should_halt
    should_halt = True
    logger.info("stack halt request")


def reboot_request(signum, frame):
    global should_reboot
    should_reboot = True
    logger.info("stack reboot request")


def redis_add_boot_msg():
    push_message(
        "output",
        {
            "event": "boot",
            "timestamp": d2s(utcnow()),
            # add context information here, like a boot counter and version etc
        },
    )


def redis_add_stop_msg():
    push_message(
        "output",
        {
            "event": "stop",
            "timestamp": d2s(utcnow()),
        },
    )


def sysreboot(i):
    libc = CDLL("libc.so.0", use_errno=True)
    libc.reboot(i)


def syssync():
    libc = CDLL("libc.so.0", use_errno=True)
    libc.sync()


def mount(source, target, fs):
    # example: mount("/dev/sdb1", "/mnt", "ext4", "rw")
    iprint("mount %s to %s, %s", source, target, fs)
    libc = CDLL("libc.so.0", use_errno=True)
    r = libc.mount(c_char_p(source.encode()), c_char_p(target.encode()),
                   c_char_p(fs.encode()), 0, 0)
    if r < 0:
        iprint("mount fail: %s on %s, %s", source, target, strerror(get_errno()))
    return r


def halt_board():
    iprint("halt target")
    libc = CDLL("libc.so.0", use_errno=True)
    libc.reboot(0xcdef0123)


def make_directory(target):
    iprint("mkdir %s", target)
    try:
        lstat(target)
    except OSError:
        try:
            mkdir(target)
        except Exception as e:
            iprint("mkdir %s failed: %s", target, e)


def low_level_setup():
    # FIXME: rootfs must be readonly

    mount("proc", "/proc", "proc")
    # on raspi, no need to mount /dev
    # mount("dev", "/dev", "devtmpfs")
    make_directory("/dev/pts")
    mount("devpts", "/dev/pts", "devpts")
    mount("sys", "/sys", "sysfs")
    make_directory("/var/run")
    mount("tmpfs", "/var/run", "tmpfs")
    mount("tmpfs", "/tmp", "tmpfs")
    system("busybox loadkmap", input="/etc/kmap-be")

    for mod in ["brcmfmac", "brcmutil", "cfg80211", "rfkill", "bcm2835_gpiomem",
                "i2c-bcm2835", "i2c_bcm2708", "i2c_dev"]:
        iprint("load module %s", mod)
        r = system("modprobe %s" % mod)
        if r != 0:
            iprint("modprobe: loading %s failed (r is %d)", mod, r)

    # generate host key
    iprint("generate host key")
    system("dropbearkey -t rsa -f /tmp/dropbear_key -s 2048")

    iprint("config setup")
    system("date -s 1801010000") # default date, for certificate
    open("/etc/resolv.conf", "w").write("nameserver 8.8.8.8\n")
    system("ifconfig lo 127.0.0.1")
    system("ifconfig eth0 10.0.0.2")
    make_directory("/var/log")
    make_directory("/var/run/dropbear")


def main():
    global should_halt, should_reboot

    environ["PATH"] = "/usr/bin:/usr/sbin:/bin:/sbin"
    low_level_setup()

    logger.info("stack starting")
    sv = SV()


    # start logger and redis
    logger.info("starting syslog, redis and ssh")
    sv.start_process("klogd -n")
    sv.start_process("syslogd -n")
    sv.start_process("redis-server /etc/redis.conf")
    sv.start_process("dropbear -Fr /tmp/dropbear_key")
    sv.start_process("ntpd -gnc /etc/ntp.conf")
    sv.start_process("wpa_supplicant -iwlan0 -c/etc/wpa_supplicant.conf")

    sleep(1)

    # reset datastore, add boot msg
    logger.info("reset keyspace and init seq")
    redis_add_boot_msg()

    # start apps
    logger.info("start hilevel apps")
    sv.start_process("diagnostic.py")
    sv.start_process("fakegps.py")
    sv.start_process("wifi_scan.py")
    sv.start_process("wifi_analyzer.py")
    sv.start_process("send_data.py")

    while not (should_halt or should_reboot):
        sv.check()

    logger.info("halt asked")
    logger.info("stopping hilevel apps")
    # hi level apps should be stopped first to give
    # a chance to push to finish uploaded all msgs
    sv.stop_process("diagnostic.py")

    # send one last message, then cut push (he will have 3s)
    redis_add_stop_msg()
    sleep(1)

    # halt push and other process
    sv.stop_process("push.py")
    logger.info("stop all systems")
    sv.stop_all()
    syssync()

    # syscall to halt/reboot
    if should_reboot:
        # just reboot
        sysreboot(0x1234567)
    else:
        # just halt
        sysreboot(0xcdef0123)


if __name__ == "__main__":
    try:
        signal(SIGCHLD, reap_process)
        signal(SIGINT, halt_request)
        signal(SIGUSR1, halt_request)
        signal(SIGTERM, reboot_request)
        main()
    except Exception as e:
        print("main exception: ", [e])
        traceback.print_exc()

    print("stack dead now - exit")
    # don't panic
    while True: sleep(1)
