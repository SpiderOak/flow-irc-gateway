"""
common.py
"""

VERSION = "0.1"
CONFIG_FILE_SECTION = "flow-irc-gateway"
DEFAULT_ENCODING = "UTF-8"

from datetime import datetime
import locale


def get_message_timestamp_string(timestamp_usecs):
    """Given a timestamp float in microseconds.
    Returns a timestamp string in the format '[%Y-%m-%d %H:%M:%S]'
    """
    # TODO: Make timestamp string configurable
    timestamp_secs = timestamp_usecs / 1.0e+6
    return datetime.fromtimestamp(
        timestamp_secs).strftime("[%Y-%m-%d %H:%M:%S]")


def irc_escape(string):
    """Escapes the given 'string' to fulfill IRC channel/nickname constraints.
    Returns a string with ',' replaced with '-' and spaces replaced with '_'.
    """
    # TODO: Make this arbitrary replacement configurable
    return string.replace(",", "_").replace(" ", "-")


def get_system_encoding():
    """Returns a string representing the encoding of the system.
    If it cannot be determined, then UTF-8 is returned.
    """
    _, sys_encoding = locale.getdefaultlocale()
    if not sys_encoding:
        sys_encoding = DEFAULT_ENCODING
    return sys_encoding
