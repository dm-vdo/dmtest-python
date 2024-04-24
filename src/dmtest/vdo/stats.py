import dmtest.process as process

import os
import re
import yaml


def _parse_vdo_stats(stats):
    return yaml.safe_load(stats)

def vdo_stats(dev):
    os.sync()
    stats = dev.message(0, "stats"); 
    return _parse_vdo_stats(stats)
