"""
common.py
"""

import os
import sys
from datetime import datetime
import locale


VERSION = "0.1"
CONFIG_FILE_SECTION = "flow-irc-gateway"

# Sane default definitions
DEFAULT_ENCODING = "UTF-8"
DEFAULT_SERVER = "45.55.26.105"
DEFAULT_PORT = "4443"
DEFAULT_URI = "flow.spideroak.com"
DEFAULT_IRC_PORT = "6667"

# OS specifics defaults
_CONFIG_OS_PATH_MAP = {
    "darwin": "Library/Application Support/semaphor",
    "linux2": ".config/semaphor",
    "win32": r"AppData\Local\semaphor",
}
_DEFAULT_APP_OSX_PATH = "/Applications/Semaphor.app/Contents/Resources/app"
_DEFAULT_APP_LINUX_RPM_PATH = "/opt/Semaphor-linux-x64/resources/app"
_DEFAULT_APP_LINUX_DEB_PATH = "/usr/share/semaphor/resources/app"
_DEFAULT_APP_WINDOWS_PATH = r"Semaphor\resources\app"

# Default dirs and binaries
_DEFAULT_ATTACHMENT_DIR = "downloads"
_DEFAULT_SCHEMA_DIR = "schema"
_DEFAULT_FLOWAPPGLUE_BINARY_DEV_NAME = "flowappglue"
_DEFAULT_FLOWAPPGLUE_BINARY_PROD_NAME = "semaphor-backend"


def _osx_app_path():
    """Returns the default application directory for OSX."""
    return _DEFAULT_APP_OSX_PATH


def _linux_app_path():
    """Returns the default application directory for Linux
    depending on the packaging (deb or rpm).
    """
    # check if RPM first
    if os.path.exists(_DEFAULT_APP_LINUX_RPM_PATH):
        return _DEFAULT_APP_LINUX_RPM_PATH
    # otherwise return DEB
    return _DEFAULT_APP_LINUX_DEB_PATH


def _windows_app_path():
    """Returns the default application directory for Windows."""
    return os.path.join(os.environ["ProgramFiles"],
                        _DEFAULT_APP_WINDOWS_PATH)


def _get_home_directory():
    """Returns a string with the home directory of the current user.
    Returns $HOME for Linux/OSX and %USERPROFILE% for Windows.
    """
    return os.path.expanduser("~")


def _get_config_path():
    """Returns the default semaphor config path."""
    return os.path.join(_get_home_directory(),
                        _CONFIG_OS_PATH_MAP[sys.platform])


_APP_OS_PATH_MAP = {
    "darwin": _osx_app_path,
    "linux2": _linux_app_path,
    "win32": _windows_app_path,
}


def get_default_db_path():
    """Returns the default db path depending on the platform,
    which in all platforms is the config path.
    E.g. on OSX it would be:
    $HOME/Library/Application Support/semaphor.
    """
    return _get_config_path()


def get_default_schema_path():
    """Returns the default schema directory depending on the platform.
    E.g. on OSX it would be:
    /Applications/Semaphor.app/Contents/Resources/app/schema.
    """
    return os.path.join(_APP_OS_PATH_MAP[sys.platform](), _DEFAULT_SCHEMA_DIR)


def get_default_attachment_path():
    """Returns the default attachment directory depending on the platform.
    E.g. on OSX it would be:
    $HOME/Library/Application Support/semaphor/downloads.
    """
    return os.path.join(_get_config_path(), _DEFAULT_ATTACHMENT_DIR)


def get_default_flowappglue_path():
    """Returns a string with the absolute path for
    the flowappglue binary; the return value depends on the platform.
    """
    flowappglue_path = os.path.join(
        _APP_OS_PATH_MAP[sys.platform](),
        _DEFAULT_FLOWAPPGLUE_BINARY_PROD_NAME)
    if os.path.isfile(flowappglue_path):
        return flowappglue_path
    flowappglue_path = os.path.join(
        _APP_OS_PATH_MAP[sys.platform](),
        _DEFAULT_FLOWAPPGLUE_BINARY_DEV_NAME)
    return flowappglue_path


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
