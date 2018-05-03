################################################################################
#
# fosdemx firmware
#
################################################################################

FOSDEMX_VERSION       = 1.0
FOSDEMX_SOURCE        =
FOSDEMX_SITE          = $(TOPDIR)/package/fosdemx
FOSDEMX_SITE_METHOD   = local

define FOSDEMX_INSTALL_TARGET_CMDS
	cp -p $(BUILD_DIR)/fosdemx-1.0/*py $(TARGET_DIR)/sbin/
	rm $(TARGET_DIR)/sbin/init || echo
	ln -s stack.py $(TARGET_DIR)/sbin/init
	echo /usr/bin/python3 > $(TARGET_DIR)/etc/shells
	cp $(BUILD_DIR)/fosdemx-1.0/kmap-be $(TARGET_DIR)/etc/
        cp $(BUILD_DIR)/fosdemx-1.0/redis.conf $(TARGET_DIR)/etc/
endef

$(eval $(generic-package))
