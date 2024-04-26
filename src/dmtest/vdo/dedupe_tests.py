from dmtest.assertions import assert_near
from dmtest.vdo.utils import standard_vdo, wait_for_index
import dmtest.fs as fs
import dmtest.process as process
import dmtest.vdo.stats as stats

import os
import re
import logging as log
import time

#---------------------------------

def make_delta_stats(stats_post, stats_pre):
    """
    Given two stats dicts, the code creates a copy of post_stats except all
    its int fields values are the delta between post and pre.
    """
    if isinstance(stats_post, dict):
        node = {}
        for key, value in stats_post.items():
            node[key] = make_delta_stats(value, stats_pre[key])
        return node
    elif isinstance(stats_post, int):
        return stats_post - stats_pre
    return stats_post

def get_dataset_config():
    config = {
        "gen.large.num" : 32,
        "gen.large.min" : 4 * 1024 * 1024,
        "gen.large.max" : 4 * 1024 * 1024,
    }
    return config

def verify_dedupe(vdo, fs_type, dedupe):
    # Wait for index to be online
    wait_for_index(vdo)
    # Do our usual wait on udev
    process.run("udevadm settle")

    fs = fs_type(vdo)
    fs.format(discard=False, quiet=True, lazy=False, noreserve=True, bs=4096)

    with fs.mount_and_chdir("./mnt"):
        # Grab the initial stats
        stats_pre = stats.vdo_stats(vdo)
        # Generate the files on top of VDO
        config = get_dataset_config()
        config["gen.large.numCoalescent"] = int((config["gen.large.num"] * dedupe) / 100)
        config["gen.root.dir"] = os.getcwd()
        options = "--stdout --logDir=../"
        for k, v in config.items():
            options += " -D" + k + "=" + str(v)
        gen_data = os.getcwd() + "/../src/scripts/gen_dataset.py"
        process.run(gen_data +  " " + options)
        # Grab the current stats and determine the differance between the two,
        # thus showing what are the stats just for the gen_data_set call.
        stats_post = stats.vdo_stats(vdo)
        stats_delta = make_delta_stats(stats_post, stats_pre)
        unique_files = config["gen.large.num"] - config["gen.large.numCoalescent"]
        expected = unique_files / config["gen.large.num"]
        actual = stats_delta["dataBlocksUsed"] / stats_delta["logicalBlocksUsed"]
        log.info(f"expected: {expected}, found: {actual}")
        assert_near(actual, expected, 0.1)

def t_dedupe0(fix):
    with standard_vdo(fix) as vdo:
        verify_dedupe(vdo, fs.Ext4, 0)

def t_dedupe50(fix):
    with standard_vdo(fix) as vdo:
        verify_dedupe(vdo, fs.Ext4, 50)

def t_dedupe75(fix):
    with standard_vdo(fix) as vdo:
        verify_dedupe(vdo, fs.Ext4, 75)


def register(tests):
    tests.register_batch(
        "/vdo/dedupe/",
        [
            ("dedupe0", t_dedupe0),
            ("dedupe50", t_dedupe50),
            ("dedupe75", t_dedupe75),
        ],
    )
