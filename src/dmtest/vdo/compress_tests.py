from dmtest.assertions import assert_equal, assert_near
from dmtest.vdo.stats import vdo_stats
from dmtest.vdo.utils import BLOCK_SIZE, MB, discard, fsync, run_fio, standard_vdo, wait_for_index
import dmtest.process as process

import logging as log
import time

def wait_until_packer_only(vdo):
    """Waits until all the I/Os being processed by a VDO device are
    completed or waiting in the packer.

    Returns VDO stats collected after waiting. (dict, see vdo_stats)

    """
    while True:
        stats = vdo_stats(vdo)
        if stats['currentVIOsInProgress'] == stats['packer']['compressedFragmentsInPacker']:
            # We're done
            return stats
        time.sleep(0.001)

def t_compress(fix):
    size = 4 * MB
    size_in_blocks = int(size / BLOCK_SIZE)
    with standard_vdo(fix, compression="on") as vdo:
        process.run("udevadm settle")
        stats = vdo_stats(vdo)
        assert_equal(stats['dataBlocksUsed'], 0, 'data blocks used (init)')
        assert_equal(stats['hashLock']['dedupeAdviceValid'], 0,
                     'dedupe advice valid (init)')
        assert_equal(stats['biosIn']['write'], 0,
                     'write bios in (init)')
        log.info(f"data blocks used: {stats['dataBlocksUsed']}")
        wait_for_index(vdo)
        # No flushing here!
        run_fio(vdo, size, 0, compression=74)
        # Flushing will cause I/Os in the packer to be pushed out;
        # there could be a bin with only one entry, which will get
        # written out uncompressed, or two entries, but (with the
        # consistent pattern of 3:1 compressibility) all the other
        # bins should hold three entries and get written out
        # compressed.
        #
        # However, any I/Os still in earlier stages of processing
        # (e.g., deduplication) that haven't yet reached the packer
        # stage will get written out uncompressed if the flush
        # notification reaches the packer first. In order to get
        # predictable rates for the test, we wait for all the I/Os we
        # sent to VDO either complete or stop in the packer.
        wait_until_packer_only(vdo)
        # And now we flush the I/Os left in the packer.
        fsync(vdo)
        stats = vdo_stats(vdo)
        assert_equal(stats['biosIn']['write'], size_in_blocks,
                     'write bios in (1st write)')
        expected_size = int((size_in_blocks + 2) / 3)
        # Some blocks in the packer may be written uncompressed when
        # we flush. That _should_ be only one, at most.
        assert_near(stats['dataBlocksUsed'], expected_size, 1,
                    'data blocks used (1st write)')
        assert_equal(stats['index']['postsNotFound'], size_in_blocks,
                     'posts not found (1st write)')
        assert_equal(stats['index']['postsFound'], 0,
                     'posts found (1st write)')
        assert_equal(stats['hashLock']['dedupeAdviceValid'], 0,
                     'dedupe advice valid (1st write)')
        # Write same data again, different location.
        # Confirm we deduplicate against compressed blocks.
        run_fio(vdo, size, size, compression=74)
        stats2 = wait_until_packer_only(vdo)
        assert_equal(stats2['dataBlocksUsed'], stats['dataBlocksUsed'],
                     'data blocks used (2nd write)')
        assert_equal(stats2['index']['postsNotFound'], size_in_blocks,
                     'posts not found (2nd write)')
        assert_equal(stats2['index']['postsFound'], size_in_blocks,
                     'posts found (2nd write)')
        assert_equal(stats2['hashLock']['dedupeAdviceValid'],
                     size_in_blocks, 'dedupe advice valid (2nd write)')
        # Confirm we can read back compressed data correctly.
        run_fio(vdo, size, 0, verify=True, stats=False, compression=74)
        # Check recovery of unreferenced compressed data.
        discard(vdo, 2 * size, 0)
        fsync(vdo)
        stats = vdo_stats(vdo)
        assert_equal(stats['dataBlocksUsed'], 0,
                     'data blocks used (discard)')

def register(tests):
    tests.register_batch(
        "/vdo/compress/",
        [
            ("compress", t_compress),
        ],
    )
