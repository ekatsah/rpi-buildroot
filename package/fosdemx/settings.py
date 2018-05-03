# Copyright 2018 - FosdemX
# This work is free. You can redistribute it and/or modify it under the
# terms of the Do What The Fuck You Want To Public License, Version 2,
# as published by Sam Hocevar. See the COPYING file or http://www.wtfpl.net/
# for more details.

import logging.config

# hardcoded safety limit
QUEUE_HARD_LIMIT = 20000

# cooldown period for the supervisor
SV_COOLDOWN = 60

# dev logging strategy
logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s.%(levelname)s %(name)s: %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
        },
        'redis_ctr': {
            'level': 'DEBUG',
            'class': '_log.RedisCounter',
        },
    },
    'loggers': {
        '': {
            'handlers': ['console', 'redis_ctr'],
            'level': 'DEBUG',
            'propagate': True
        },
    },
})


try:
    from settings_prod import *  # pragma: no flakes
except ImportError:
    pass
