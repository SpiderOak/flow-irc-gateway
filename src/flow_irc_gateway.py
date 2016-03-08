#! /usr/bin/env python
#
# Copyright (C) 2003-2015 Joel Rosdahl
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA
#
# Joel Rosdahl <joel@rosdahl.net>
"""
flow_irc_gateway.py: Flow-IRC-Gateway main script
"""

import os
import select
import socket
import sys
import time
from optparse import OptionParser
import signal
import ConfigParser
import re

import common
from channel import ChannelMember, Channel, DirectChannel
from irc_client import IRCClient
from notification import NotificationHandler
from flow import Flow


class FlowIRCGateway(object):
    """A Flow-IRC gateway."""

    def __init__(self, options):
        """Arguments:
        options : optparse.OptionParser, with the following attributes:
            irc_ports, verbose, debug, show_timestamps, daemon,
            flowappglue, username, server, port, db, schema, uri
        """
        self.irc_ports = options.irc_ports
        self.verbose = options.verbose
        self.debug = options.debug
        self.show_timestamps = options.show_timestamps

        gateway_name_limit = 63  # From the RFC.
        self.name = socket.getfqdn()[:gateway_name_limit]

        self.channels = {}  # ChannelID --> Channel instance.
        self.clients = {}  # Socket --> IRCClient instance.
        self.organizations = {}  # OrgID --> Organization Name
        self.pending_channels = {}  # ChannelID --> PendingChannel instance

        self.client_connected = True
        self.flow_service = None
        self.flow_initialized = False
        self.flow_username = ""
        self.flow_account_id = ""
        self.notification_handler = NotificationHandler(self)

    def terminate(self):
        """Terminates the Flow service."""
        self.flow_service.terminate()

    def get_member(self, irc_nickname):
        """Gets a channel member from its IRC nickname.
        Arguments:
        irc_nickname : string, IRC nickname of a 'ChannelMember'.
        Returns a ChannelMember instance or 'None' if not found.
        """
        for channel in self.channels.values():
            for member in channel.members:
                if member.get_irc_nickname() == irc_nickname:
                    return member
        return None

    def get_oid_from_name(self, org_name):
        """Returns an the OrgID given an organization name.
        Arguments:
        org_name : string, organization name.
        Returns an empty string if not found.
        """
        for oid, oname in self.organizations.iteritems():
            if oname == org_name:
                return oid
        return ""

    def get_member_account_id(self, username):
        """Returns an AccountID string from Flow given the username.
        Arguments:
        username : string, Flow username of the account.
        Returns an empty string if not found.
        """
        try:
            member_peer_data = self.flow_service.get_peer(username)
            if member_peer_data:
                return member_peer_data["AccountID"]
        except Flow.FlowError as flow_err:
            self.print_debug("get_peer: '%s'" % str(flow_err))
        return ""

    def transmit_message_to_channel(self, channel, message_text):
        """Sends a message using Flow.send_message.
        Arguments:
        channel : Channel instance
        message_test : Text to be sent to the channel.
        Returns True if the message was sent successfully.
        """
        try:
            message_id = self.flow_service.send_message(
                channel.organization_id,
                channel.channel_id,
                message_text)
            return message_id != ""
        except Flow.FlowError as flow_err:
            self.print_debug("send_message: '%s'" % str(flow_err))
            return False

    def create_direct_channel(self,
                              account_id,
                              account_username,
                              oid,
                              organization_name):
        """Creates a direct conversation channel.
        Arguments:
        account_id : string, receiver's AccountID.
        account_username : string, receiver's username.
        oid : string, OrganizationID the two members share.
        organization_name : Name of the Organization the two members share.
        Returns a 'Channel' instance.
        If there's an error in the channel creation, then 'None' is returned.
        """
        direct_conversation_channel = None
        try:
            direct_conversation_cid = \
                self.flow_service.new_direct_conversation(
                    oid,
                    account_id)
            if direct_conversation_cid:
                direct_conversation_channel = DirectChannel(
                    self,
                    direct_conversation_cid,
                    oid,
                    organization_name,
                    True)
                current_user = ChannelMember(
                    self.flow_username,
                    self.flow_account_id,
                    organization_name)
                other_member = ChannelMember(
                    account_username, account_id, organization_name)
                direct_conversation_channel.add_member(current_user)
                direct_conversation_channel.add_member(other_member)
                self.add_channel(direct_conversation_channel)
        except Flow.FlowError as flow_err:
            self.print_debug("NewDirectConversation: '%s'" % str(flow_err))
        return direct_conversation_channel

    def get_channel(self, channel_id):
        """Returns a 'Channel' instance given a ChannelID.
        Returns 'None' if not found.
        """
        try:
            return self.channels[channel_id]
        except KeyError:
            return None

    def get_channel_from_irc_name(self, channel_irc_name):
        """Returns a 'Channel' instance given the IRC name.
        Returns 'None' if not found.
        """
        for channel in self.channels.values():
            if channel.get_irc_name() == channel_irc_name:
                return channel
        return None

    def check_channel_collision(self, channel):
        """Checks and sets if a 'Channel'
        instance IRC name collides with other channel.
        """
        if self.get_channel_from_irc_name(channel.get_irc_name()):
            channel.name_collides = True

    def get_channels(self, oid, org_name):
        """Loads all channels of a given organization
        Arguments:
        oid : string, OrgID of the Organization
        org_name : string, Name of the Organization
        """
        channels = self.flow_service.enumerate_channels(oid)
        for channel in channels:
            channel_name = channel["Name"]
            direct_channel = channel["Purpose"] == "direct message"
            if direct_channel:
                irc_channel = DirectChannel(
                    self, channel["ID"], oid, org_name)
            else:
                irc_channel = Channel(
                    self, channel["ID"], channel_name, oid, org_name)
                self.check_channel_collision(irc_channel)
            self.get_channel_members(irc_channel)
            self.add_channel(irc_channel)

    def get_orgs_and_channels(self):
        """Loads all Organizations and Channels the account is member of."""
        self.organizations = {}
        self.channels = {}
        orgs = self.flow_service.enumerate_orgs()
        for org in orgs:
            oid = org["ID"]
            org_name = org["Name"]
            self.organizations[oid] = org_name
            self.get_channels(oid, org_name)

    def get_local_account(self):
        """Returns the first local Flow account on this device.
        It returns the username string.
        Returns 'None' if there is no account on the device.
        """
        local_accounts = self.flow_service.enumerate_local_accounts()
        if not local_accounts:
            return None
        return local_accounts[0]["EmailAddress"]

    def register_callbacks(self):
        """Registers all the notification types this gateway supports."""
        self.flow_service.register_callback(
            Flow.ORG_NOTIFICATION,
            self.notification_handler.org_notification)
        self.flow_service.register_callback(
            Flow.CHANNEL_NOTIFICATION,
            self.notification_handler.channel_notification)
        self.flow_service.register_callback(
            Flow.MESSAGE_NOTIFICATION,
            self.notification_handler.message_notification)
        self.flow_service.register_callback(
            Flow.CHANNEL_MEMBER_NOTIFICATION,
            self.notification_handler.channel_member_notification)

    def unregister_callbacks(self):
        """Unregisters all the notification types this gateway supports."""
        self.flow_service.unregister_callback(Flow.ORG_NOTIFICATION)
        self.flow_service.unregister_callback(Flow.CHANNEL_NOTIFICATION)
        self.flow_service.unregister_callback(Flow.MESSAGE_NOTIFICATION)
        self.flow_service.unregister_callback(Flow.CHANNEL_MEMBER_NOTIFICATION)

    def initialize_flow_service(self, options):
        """Initializes the Flow Service by logging into the user
        account and starting up the Flow session.
        """
        self.flow_initialized = False
        try:
            self.flow_username = options.username
            self.flow_service = Flow(
                "",
                "",
                options.flowappglue,
                options.debug,
                options.server,
                options.port,
                options.db,
                options.schema,
                options.attachment_dir)
            if not self.flow_username:
                self.flow_username = self.get_local_account()
            if not self.flow_username:
                raise Flow.FlowError("Local account not found.")
            self.flow_service.start_up(self.flow_username, options.uri)
            self.flow_initialized = True
        except Flow.FlowError as flow_err:
            self.print_error("Flow Initialization: '%s'" % str(flow_err))

    def add_channel(self, channel):
        """Adds a 'Channel' instance to the gateway's channel list."""
        self.channels[channel.channel_id] = channel

    def print_info(self, msg):
        """Prints a info msg string to stdout
        (if self.verbose is set to True).
        """
        if self.verbose:
            print(msg)
            sys.stdout.flush()

    def print_debug(self, msg):
        """Prints a debug msg string to stdout
        (if self.debug is set to True).
        """
        if self.debug:
            print(msg)
            sys.stdout.flush()

    @staticmethod
    def print_error(msg):
        """Prints an error msg string to stdout."""
        sys.stderr.write("%s\n" % msg)

    def remove_client(self, client):
        """Removes 'Client' instance 'client' from the clients map.
        The gateway stops processing notifications until reconnection.
        """
        del self.clients[client.client_socket]
        self.unregister_callbacks()
        self.client_connected = False

    def notify_clients(self, irc_msg):
        """Sends 'msg' string to all IRC client connections."""
        for client in self.clients.values():
            client.message(irc_msg)

    def get_channel_members(self, channel):
        """Retrieves (via Flow.enumerate_channel_members) and sets
        all channel members on a given 'Channel' instance.
        """
        members = self.flow_service.enumerate_channel_members(
            channel.channel_id)
        for member in members:
            account_id = member["AccountID"]
            account_username = member["EmailAddress"]
            if account_username == self.flow_username:
                self.flow_account_id = account_id
            channel_member = ChannelMember(
                account_username, account_id, channel.organization_name)
            channel.add_member(channel_member)

    def start(self):
        """FlowIRCGateway initialization and main loop"""
        if not self.flow_initialized:
            self.terminate()
            return
        gatewaysockets = []
        for port in self.irc_ports:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                # Listen to local connections only
                sock.bind(("localhost", port))
            except socket.error as sock_err:
                self.print_error(
                    "Could not bind port %s: %s." %
                    (port, sock_err))
                sys.exit(1)
            sock.listen(5)
            gatewaysockets.append(sock)
            del sock
            self.print_info("Listening on port %d." % port)
        last_aliveness_check = time.time()

        while True:
            # Process Flow notifications
            if self.client_connected:
                while self.flow_service.process_one_notification(0.05):
                    pass
            # Process IRC client socket connections
            (iwtd, owtd, _) = select.select(
                gatewaysockets +
                [client.client_socket for client in self.clients.values()],
                [client.client_socket for client in self.clients.values()
                 if client.write_queue_size() > 0],
                [], 0.05)
            for sock in iwtd:
                if sock in self.clients:
                    self.clients[sock].socket_readable_notification()
                else:
                    (conn, addr) = sock.accept()
                    try:
                        self.clients[conn] = IRCClient(self, conn)
                        self.print_info("Accepted connection from %s:%s." % (
                            addr[0], addr[1]))
                    except socket.error:
                        try:
                            conn.close()
                        except:
                            pass
            for sock in owtd:
                if sock in self.clients:  # client may have been disconnected
                    self.clients[sock].socket_writable_notification()
            now = time.time()
            if last_aliveness_check + 10 < now:
                for client in self.clients.values():
                    client.check_aliveness()
                last_aliveness_check = now


def get_from_config(config, var_name, default_value, isbool=False):
    """Utility function to get value from config, only if present.
    Arguments:
    options : container object with options.
    config : ConfigParser.ConfigParser instance.
    var : string, name of variable within the config.
    isbool : boolean, 'True' if the config variable
    is supposed to be a boolean.
    """
    value = default_value
    if config.has_option(common.CONFIG_FILE_SECTION, var_name):
        if isbool:
            value = config.getboolean(common.CONFIG_FILE_SECTION, var_name)
        else:
            value = config.get(common.CONFIG_FILE_SECTION, var_name)
    return value


def read_from_config(opt_parser, options):
    """Attempts to read options from a config file.
    It overrides the default values with values present in the config.
    Arguments:
    opt_parser : optparser.OptionParser instance.
    options : container object with options.
    """
    if not os.path.isfile(options.config):
        opt_parser.error(
            "Cannot access '%s', no such file or directory." %
            options.config)
    config = ConfigParser.RawConfigParser()
    config.read(options.config)

    if not options.username and config.has_option(
            common.CONFIG_FILE_SECTION, "username"):
        options.username = config.get(common.CONFIG_FILE_SECTION, "username")

    # override with values from config (if present)
    options.server = get_from_config(config, "server", options.server)
    options.port = get_from_config(config, "port", options.port)
    options.db = get_from_config(config, "db", options.db)
    options.schema = get_from_config(config, "schema", options.schema)
    options.attachment_dir = get_from_config(
        config, "attachment-dir", options.attachment_dir)
    options.uri = get_from_config(config, "uri", options.uri)
    options.flowappglue = get_from_config(
        config, "flowappglue", options.flowappglue)
    options.debug = get_from_config(config, "debug", options.debug, True)
    options.verbose = get_from_config(config, "verbose", options.verbose, True)
    options.daemon = get_from_config(config, "daemon", options.daemon, True)
    options.irc_ports = get_from_config(config, "irc-ports", options.irc_ports)
    options.show_timestamps = get_from_config(
        config, "show-timestamps", options.show_timestamps)


def set_sane_defaults(options):
    """Set sane defaults to avoid the need for a config.
    Aguments:
    options : container object to fill with the default values.
    """
    options.server = ""
    options.port = ""
    options.db = ""
    options.schema = ""
    options.attachment_dir = ""
    options.uri = ""
    options.flowappglue = ""
    options.verbose = False
    options.daemon = False
    options.irc_ports = common.DEFAULT_IRC_PORT


def parse_options_and_config(argv):
    """Command line and config options parsing"""
    opt_parser = OptionParser(
        version=common.VERSION,
        description="flow-irc-gateway is a small IRC gateway to "
                    "SpiderOak Flow (based off of miniircd)")
    opt_parser.add_option(
        "--config",
        metavar="X",
        help="config ini file X")
    opt_parser.add_option(
        "--debug",
        action="store_true",
        help="Debug Mode",
        default=False)
    opt_parser.add_option(
        "--show-timestamps",
        action="store_true",
        help="Prepend timestamps in messages",
        default=False)
    opt_parser.add_option(
        "--username",
        metavar="X",
        help="flow account username")

    (options, _) = opt_parser.parse_args(argv[1:])

    set_sane_defaults(options)

    if options.config:
        read_from_config(opt_parser, options)

    if options.username:
        try:
            system_encoding = common.get_system_encoding()
        except:  # OSX bug in locale.getdefaultlocale()
            system_encoding = common.DEFAULT_ENCODING
            print(
                "locale.getdefaultlocale() failed, using '%s'." %
                system_encoding)
        options.username = options.username.decode(system_encoding)

    if options.debug:
        options.verbose = True

    ports = []
    for port in re.split(r"[,\s]+", options.irc_ports):
        try:
            ports.append(int(port))
        except ValueError:
            opt_parser.error("bad port: %r" % port)
    options.irc_ports = ports

    return options


def daemonize():
    """Forks a daemon process and exits."""
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except OSError:
        sys.exit(1)
    os.setsid()
    try:
        pid = os.fork()
        if pid > 0:
            print("PID: %d" % pid)
            sys.exit(0)
    except OSError:
        sys.exit(1)
    os.chdir("/")
    os.umask(0)
    dev_null = open("/dev/null", "r+")
    os.dup2(dev_null.fileno(), sys.stdout.fileno())
    os.dup2(dev_null.fileno(), sys.stderr.fileno())
    os.dup2(dev_null.fileno(), sys.stdin.fileno())


def main():
    """Entry point for the application"""

    options = parse_options_and_config(sys.argv)

    if options.daemon:
        daemonize()

    gateway = FlowIRCGateway(options)

    def signal_handler(sig, frame):
        """Function used to gracefully terminate the gateway."""
        print("... terminating ...")
        gateway.terminate()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        gateway.initialize_flow_service(options)
        gateway.start()
    except:
        gateway.terminate()
        raise


if __name__ == "__main__":
    main()
