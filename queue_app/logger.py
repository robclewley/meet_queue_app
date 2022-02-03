"""Simple text log pattern using local sub-directory.
"""

import logging
import os
import sys
import fileinput
import re
from time import strptime
import datetime
import ast
import queue_app.utils
import json
import socket
from logging.handlers import SysLogHandler


def initialize_logger(output_dir='logs',
                      relative_path=True,
                      force_filename='',
                      default_level='error',
                      overwrite_log_files=False,
                      use_console=False):
    """Simple file logger pattern, provides methods such as
    logger.error and logger.info.

    force_filename is an optional string to set a specific log file name.

    overwrite_log_files option (default False) specifies whether old debug logs are
    retained and new ones created with _N extension (where N is the latest
    available). This is helpful for iterating during test development.
    N cannot become larger than 99.

    Default log level is logging.ERROR specified with default_level='error'

    Based on https://aykutakin.wordpress.com/2013/08/06/logging-to-console-and-file-in-python/
    """
    # Ensure directory exists
    if relative_path:
        local = os.getcwd()
        output_dir_abs = os.path.join(local, output_dir)
    else:
        output_dir_abs = output_dir
    direct = os.path.dirname(output_dir_abs)
    if not os.path.exists(direct):
        os.makedirs(direct)

    # create debug file handler and set level to debug
    if force_filename:
        if not overwrite_log_files:
            raise ValueError("Set overwrite_log_files to True when forcing filename")
        log_fname = force_filename
    else:
        if not overwrite_log_files:
            i = -1
            while i < 99:
                if i == -1:
                    ext = ''
                else:
                    ext = '_' + str(i)
                if os.path.exists(os.path.join(output_dir, "all%s.log"%ext)):
                    i += 1
                else:
                    break
            if i >= 99:
                raise ValueError("No compatible log file name available -- clean up your logs!")
        else:
            ext = ''
        log_fname = "all%s.log"%ext

    logger = logging.getLogger(log_fname)
    logger.setLevel(logging.DEBUG)

    if use_console:
        # create console handler and set level to info
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter("%(asctime)s %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    # create error file handler and set level to error
    handler = logging.FileHandler(os.path.join(output_dir, "error.log"),
                                  "w", encoding=None, delay="true")
    handler.setLevel(logging.ERROR)
    formatter = logging.Formatter("%(asctime)s %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    handler = logging.FileHandler(os.path.join(output_dir, log_fname), "w")
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # shut requests verbosity down from mouthy INFO level!
    try:
        level = getattr(logging, default_level.upper())
    except AttributeError:
        raise ValueError("Invalid default logging level: %s" % default_level)
    logging.getLogger('requests.packages.urllib3.connectionpool').setLevel(level)
    return logger


def merge_logs(file_paths, sort_on_time=False, timestamp_format='%a %b %d %H:%M:%S %Y'):
    """Beware of sorting logs that use multi-line groups per record and which originate
    from concurrent processes.
    """
    lines = list(fileinput.input(file_paths))
    if sort_on_time:
        t_pat = re.compile(r'\[(.+?)\]') # pattern to extract timestamp
        return sorted(lines, key=lambda l: strptime(t_pat.search(l).group(1),
                                                    timestamp_format))
    else:
        return lines

class StdErrLoggerWriter:
    def __init__(self, level):
        # self.level is really like using log.debug(message)
        # at least in my case
        self.level = level

    def write(self, message):
        # if statement reduces the amount of newlines that are
        # printed to the logger
        if message != '\n':
            self.level(message)

    def flush(self):
        # create a flush method so things can be flushed when
        # the system wants to. Not sure if simply 'printing'
        # sys.stderr is the correct way to do it, but it seemed
        # to work properly for me.
        self.level(sys.stderr)

    def fileno(self):
        # 2 is what stderr is supposed to return
        return 2

# ===========

class ContextFilter(logging.Filter):
    hostname = socket.gethostname()

    def filter(self, record):
        record.hostname = ContextFilter.hostname
        return True


class LogClass(object):
    def make_log(self, app=None):
        if 'DYNO' in os.environ:
            # papertrail
            # https://help.papertrailapp.com/kb/configuration/configuring-centralized-logging-from-python-apps/#examples
            syslog = SysLogHandler(address=('logs7.papertrailapp.com', 51173))
            syslog.addFilter(ContextFilter())

            if app is None:
                # game's logger
                format = '%(asctime)s %(hostname)s EEH-game: %(message)s'
                formatter = logging.Formatter(format, datefmt='%b %d %H:%M:%S')
                syslog.setFormatter(formatter)
                logger = logging.getLogger()
                logger.addHandler(syslog)
                logger.addHandler(logging.StreamHandler(sys.stdout))
                # set to ERROR to prevent REDIS noise
                logger.setLevel(logging.ERROR)
                log_object = logger
            else:
                # app's logger
                format = '%(asctime)s %(hostname)s EEH-app: %(message)s'
                formatter = logging.Formatter(format, datefmt='%b %d %H:%M:%S')
                syslog.setFormatter(formatter)
                app.logger = log_object = logging.getLogger()
                app.logger.addHandler(syslog)
                app.logger.addHandler(logging.StreamHandler(sys.stdout))
                app.logger.setLevel(logging.ERROR)
        else:
            if app is None:
                destn = 'game.log'
            else:
                destn = 'app.log'
            log_object = initialize_logger(force_filename=destn,
                                        output_dir='logs',
                                        overwrite_log_files=True)
            if app is not None:
                app.logger = log_object
        self.logger = log_object

    def info(self, msg):
        self.logger.info(msg)

    def warning(self, msg):
        self.logger.warning(msg)

    def error(self, msg):
        self.logger.error(msg)

    def critical(self, msg):
        self.logger.critical(msg)

    def debug(self, msg):
        self.logger.debug(msg)

log = LogClass()
