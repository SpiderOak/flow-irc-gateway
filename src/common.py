"""
common.py
"""

VERSION = "1.0"
CONFIG_FILE_SECTION = "flow-irc-gateway"

from datetime import datetime

def get_message_timestamp_string(timestamp_usecs):
    """Given a timestamp float in microseconds, it returns a timestamp string in the format '[%Y-%m-%d %H:%M:%S]'"""
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
