#!/usr/bin/env python3
"""
  Utils - dmtest util file for command processing

  Copyright (c) Red Hat
"""

from __future__ import print_function

import logging
import os
import subprocess
import textwrap

logger = logging.getLogger('dmtest')

def runCommand(args, ignoreErrors=False):
  """
  Run a shell command
  """
  if isinstance(args, str):
    command = args
  else:
    command = " ".join(args)
  
  logger.debug("Running Command: {0}".format(command))
  result = subprocess.run(command, shell=True, text=True, capture_output=True)

  if (not ignoreErrors) and (result.returncode != 0):
    logger.error("Command '{cmd}' failed: stderr:\n{err}\nstdout:\n{out}".format(
      cmd = command, err = result.stderr, out = result.stdout))
  elif result.stdout != "":
    logger.debug("runCommand stdout:\n{0}".format(result.stdout.rstrip()))
  return result

def runCommandIgnoringErrors(args):
  """
  Run a shell command ignoring any errors
  """
  return runCommand(args, True)

