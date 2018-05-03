#!/bin/sh

set -u
set -e

# Add a console on tty1
if [ -e ${TARGET_DIR}/etc/inittab ]; then
    grep -qE '^tty1::' ${TARGET_DIR}/etc/inittab || \
	sed -i '/GENERIC_SERIAL/a\
tty1::respawn:/sbin/getty -L  tty1 0 vt100 # HDMI console' ${TARGET_DIR}/etc/inittab
fi

# switch to python as shell
sed -i "s/\/bin\/sh/\/usr\/bin\/python3/" ${TARGET_DIR}/etc/passwd
sed -i "s/\/root/\/sbin/" ${TARGET_DIR}/etc/passwd
