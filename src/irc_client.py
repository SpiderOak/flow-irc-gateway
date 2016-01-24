"""
irc_client.py
"""

import re
import time
import socket
import string
from common import *
from channel import *


class IRCClient(object):
    """Represents an IRC client connection."""
    __linesep_regexp = re.compile(r"\r?\n")
    __dc_member_regexp = re.compile(r"(.+)\((.+)\)")

    def __init__(self, gateway, socket):
        """Arguments:
        gateway : FlowIRCGateway instance
        socket : socket instance
        """
        self.gateway = gateway
        self.socket = socket
        self.nickname = ""
        self.user = ""
        self.realname = ""
        (self.host, self.port) = socket.getpeername()
        self.__timestamp = time.time()
        self.__readbuffer = ""
        self.__writebuffer = ""
        self.__sent_ping = False
        self.__handle_command = self.__registration_handler

    def check_aliveness(self):
        """Checks whether the IRC client connection is alive. Uses IRC's PING command."""
        now = time.time()
        if self.__timestamp + 180 < now:
            self.disconnect("ping timeout")
            return
        if not self.__sent_ping and self.__timestamp + 90 < now:
            if self.__handle_command == self.__command_handler:
                # Registered.
                self.message("PING :%s" % self.gateway.name)
                self.__sent_ping = True
            else:
                # Not registered.
                self.disconnect("ping timeout")

    def write_queue_size(self):
        """Returns the length of the output buffer"""
        return len(self.__writebuffer)

    def __parse_read_buffer(self):
        """"Parses the input buffer received from the IRC client connection"""
        lines = self.__linesep_regexp.split(self.__readbuffer)
        self.__readbuffer = lines[-1]
        lines = lines[:-1]
        for line in lines:
            if not line:
                # Empty line. Ignore.
                continue
            x = line.split(" ", 1)
            command = x[0].upper()
            if len(x) == 1:
                arguments = []
            else:
                if len(x[1]) > 0 and x[1][0] == ":":
                    arguments = [x[1][1:]]
                else:
                    y = string.split(x[1], " :", 1)
                    arguments = string.split(y[0])
                    if len(y) == 2:
                        arguments.append(y[1])
            self.__handle_command(command, arguments)

    def send_welcome(self):
        """Sends the Welcome Message to the IRC client connection"""
        self.reply("001 %s :Hi, welcome to Flow" % self.nickname)
        self.reply("002 %s :Your host is %s, running version flow-irc-gateway-%s" %
                   (self.nickname, self.gateway.name, VERSION))

    def __registration_handler(self, command, arguments):
        """Handler for the IRC client registration. NICK and USER are received. 
        This gateway ignores the arguments provided and forces the NICK and USER to be the Flow username.
        After the registration is complete, all organizations and channels are retrieved from Flow and sent to the IRC client.
        Arguments:
        command : string, IRC command
        arguments : list, IRC command arguments 
        """
        if command == "NICK":
            self.nickname = self.gateway.flow_username  # override user provided NICK
        elif command == "USER":
            self.user = self.gateway.flow_username  # override user provided USER
        elif command == "QUIT":
            self.disconnect("Client quit")
            return
        if self.nickname and self.user:
            self.send_welcome()
            self.gateway.get_orgs_and_channels()
            self.send_lusers()
            self.send_motd()
            self.send_nick_data()
            self.send_channels_data()
            self.__handle_command = self.__command_handler

    def __command_handler(self, command, arguments):
        """IRC commands handler."""
        def away_handler():
            """AWAY command is not supported by this gateway."""
            pass

        def ison_handler():
            """ISON command is not supported by this gateway."""
            pass

        def join_handler():
            """JOIN command is not supported by this gateway. 
            The user can only be part of the channels provided by the gateway
            """
            pass

        def nick_handler():
            """NICK command is not supported by this gateway.
            After the user has registered, this gateway does not allow IRC NICK change.
            """
            pass

        def part_handler():
            """PART command is not supported by this gateway. You cannot leave a Flow channel from the IRC client."""
            pass

        def topic_handler():
            """TOPIC command is not supported by this gateway."""
            pass

        def list_handler():
            """Handler for the LIST IRC command. Flow Channels will return an empty IRC topic."""
            if len(arguments) < 1:
                channels = gateway.channels.values()
            else:
                channels = []
                for channelname in arguments[0].split(","):
                    channel = gateway.get_channel_from_irc_name(channelname)
                    if channel:
                        channels.append(channel)
            channels.sort(key=lambda x: x.channel_name)
            for channel in channels:
                self.reply("322 %s %s %d :"
                           % (self.nickname, channel.get_irc_name(),
                              len(channel.members)))
            self.reply("323 %s :End of LIST" % self.nickname)

        def lusers_handler():
            """Handler for the LUSERS IRC command."""
            self.send_lusers()

        def mode_handler():
            """Handler for the MODE IRC command.
            Flow channels have no MODEs therefore this returns MODE responses with no modes in them.
            """
            if len(arguments) < 1:
                self.reply_461("MODE")
                return
            targetname = arguments[0]
            self.reply("324 %s %s" % (self.nickname, targetname))

        def motd_handler():
            """Handler for the MOTD IRC command."""
            self.send_motd()

        def pong_handler():
            """Handler for the PONG IRC command. Nothing to do here."""
            pass

        def send_to_member(self):
            sent_to_member = False
            items = self.__dc_member_regexp.split(targetname)[1:-1]
            username = items[0]
            organization_name = items[1]
            # Try to get the member from local members
            member = gateway.get_member(targetname)
            if not member or (member and member.account_id != gateway.flow_account_id):
                if not member:
                    # This is an unknown member to this gateway, try to get the peer data
                    member_account_id = gateway.get_member_account_id(username)
                else:
                    member_account_id = member.account_id
                if member_account_id:
                    # Get OrgID from name
                    oid = gateway.get_oid_from_name(organization_name)
                    if oid:
                        direct_conversation_channel = gateway.create_direct_conversation_channel(
                            member_account_id, username, oid, organization_name)
                        if direct_conversation_channel:
                            sent_to_member = gateway.transmit_message_to_channel(direct_conversation_channel, message)            
            return sent_to_member

        def notice_and_privmsg_handler():
            """Handler for the PRIVMSG/NOTICE IRC command.
            PRIVMSG for a channel: If the channel exists, then it sends the message to the Channel via Flow.SendMessage
            PRIVMSG for a member: If the member exists and there's no direct conversation within the session, then 
            a new direct conversation channel is created (with Flow.NewDirectConversation) and the message is sent.
            """
            privmsg_success = False
            if len(arguments) == 0:
                self.reply("411 %s :No recipient given (%s)"
                           % (self.nickname, command))
                return
            if len(arguments) == 1:
                self.reply("412 %s :No text to send" % self.nickname)
                return
            targetname = arguments[0]
            message = arguments[1]
            channel = gateway.get_channel_from_irc_name(targetname)
            if channel:
                privmsg_success = gateway.transmit_message_to_channel(
                    channel, message)
            else:
                privmsg_success = self.send_to_member()
            if not privmsg_success:
                self.reply("401 %s %s :No such nick/channel"
                           % (self.nickname, targetname))

        def ping_handler():
            """Handler for the PING IRC command."""
            if len(arguments) < 1:
                self.reply("409 %s :No origin specified" % self.nickname)
                return
            self.reply("PONG %s :%s" % (gateway.name, arguments[0]))

        def quit_handler():
            """Handler for the QUIT IRC command."""
            if len(arguments) < 1:
                quitmsg = self.nickname
            else:
                quitmsg = arguments[0]
            self.disconnect(quitmsg)

        def who_handler():
            """Handler for the WHO IRC command."""
            if len(arguments) < 1:
                return
            targetname = arguments[0]
            channel = gateway.get_channel_from_irc_name(targetname)
            if channel:
                for member in channel.members:
                    self.reply("352 %s %s %s %s %s %s H :0 %s"
                               % (self.nickname, targetname, member.user,
                                  member.host, gateway.name, member.get_irc_nickname(),
                                  member.realname))
                self.reply("315 %s %s :End of WHO list"
                           % (self.nickname, targetname))

        def whois_handler():
            """Handler for the WHOIS IRC command."""
            if len(arguments) < 1:
                return
            membername = arguments[0]
            member = gateway.get_member(membername)
            if member:
                self.reply("311 %s %s %s %s * :%s"
                           % (self.nickname, member.get_irc_nickname(), member.user,
                              member.host, member.realname))
                self.reply("312 %s %s %s :%s"
                           % (self.nickname, member.get_irc_nickname(), "", ""))
                self.reply("318 %s %s :End of WHOIS list"
                           % (self.nickname, member.get_irc_nickname()))
            else:
                self.reply("401 %s %s :No such nick"
                           % (self.nickname, membername))

        handler_table = {
            "AWAY": away_handler,
            "ISON": ison_handler,
            "JOIN": join_handler,
            "LIST": list_handler,
            "LUSERS": lusers_handler,
            "MODE": mode_handler,
            "MOTD": motd_handler,
            "NICK": nick_handler,
            "NOTICE": notice_and_privmsg_handler,
            "PART": part_handler,
            "PING": ping_handler,
            "PONG": pong_handler,
            "PRIVMSG": notice_and_privmsg_handler,
            "QUIT": quit_handler,
            "TOPIC": topic_handler,
            "WHO": who_handler,
            "WHOIS": whois_handler,
        }
        gateway = self.gateway
        try:
            handler_table[command]()
        except KeyError:
            self.reply("421 %s %s :Unknown command" % (self.nickname, command))

    def socket_readable_notification(self):
        """Reads data from the IRC client socket (the data is written to self.__readbuffer)."""
        try:
            data = (self.socket.recv(2 ** 10)).decode('utf-8')
            self.gateway.print_debug(
                "[%s:%d] -> %r" % (self.host, self.port, data))
            quitmsg = "EOT"
        except socket.error as x:
            data = ""
            quitmsg = x
        if data:
            self.__readbuffer += data
            self.__parse_read_buffer()
            self.__timestamp = time.time()
            self.__sent_ping = False
        else:
            self.disconnect(quitmsg)

    def socket_writable_notification(self):
        """Sends data to IRC client socket (using self.__writebuffer)."""
        try:
            sent = self.socket.send(self.__writebuffer.encode('utf-8'))
            self.gateway.print_debug(
                "[%s:%d] <- %r" % (
                    self.host, self.port, self.__writebuffer[:sent]))
            self.__writebuffer = self.__writebuffer[sent:]
        except socket.error as x:
            self.disconnect(x)

    def disconnect(self, quitmsg):
        """Closes the socket for this IRC client and it is removed from the client list."""
        self.message("ERROR :%s" % quitmsg)
        self.gateway.print_info(
            "Disconnected connection from %s:%s (%s)." % (
                self.host, self.port, quitmsg))
        self.socket.close()
        self.gateway.remove_client(self)

    def message(self, msg):
        """Writes to the self.__writebuffer buffer, to be send via socket_writable_notification()."""
        self.__writebuffer += msg + "\r\n"

    def reply(self, msg):
        """Sends an IRC reply message to an IRC client connection."""
        self.message(":%s %s" % (self.gateway.name, msg))

    def send_lusers(self):
        """Replies the IRC client connection with LUSERS response data."""
        self.reply("251 %s :There are %d orgs and %d channels"
                   % (self.nickname, len(self.gateway.organizations), len(self.gateway.channels)))

    def get_list_of_channels_by_org(self):
        """Returns a map of OrgName -> [(ChannelName, IsDirectConversation, ChannelMemberCount)]."""
        orgs_channels = {}
        for org_name in self.gateway.organizations.values():
            orgs_channels[org_name] = []
        for channel in self.gateway.channels.values():
            orgs_channels[channel.organization_name].append(
                (channel.get_irc_name(), isinstance(channel, DirectChannel), len(channel.members)))
        for channels in orgs_channels.values():
            channels.sort()
        return orgs_channels

    def send_motd(self):
        """Sends the MOTD with the list of organizations, their channels with their member count."""
        self.reply("375 %s :- Message of the day -" % self.nickname)
        self.reply("372 %s :- Your Flow username is: %s" % (self.nickname, self.nickname))
        self.reply("372 %s :- List of Organizations and Channels:" % self.nickname)
        orgs_channels = self.get_list_of_channels_by_org()
        for org_name, channel_list in orgs_channels.iteritems():
            self.reply("372 %s :  - %s: [%d channels]" %
                       (self.nickname, org_name, len(channel_list)))
            for channel_name, direct, member_count in channel_list:
                direct_channel = " [direct conversation]" if direct else (
                    " [%d members]" % member_count)
                self.reply("372 %s :    - %s%s" %
                           (self.nickname, channel_name, direct_channel))
        self.reply("376 %s :End of /MOTD command" % self.nickname)

    def send_nick_data(self):
        """Sends the NICK data to the user (forced by the gateway)."""
        self.message(":%s!%s@%s NICK :%s" %
                     (self.nickname, self.user, self.host, self.nickname))

    def send_channels_data(self):
        """Sends the channel and messages data to the IRC client connection."""
        for channel in self.gateway.channels.values():
            self.send_channel_join_commands(channel)
            self.send_channel_messages(channel)

    def send_channel_join_commands(self, channel):
        """Sends the Channel JOIN commands to the IRC client connection."""
        # JOIN command for the current user
        self.message(":%s!%s@%s JOIN :%s" %
                     (self.nickname, self.user, self.host, channel.get_irc_name()))
        # Then, JOIN for the remaining members
        for member in channel.members:
            if member.account_id != self.gateway.flow_account_id:
                self.message(":%s!%s@%s JOIN :%s" %
                             (member.get_irc_nickname(), member.user, member.host, channel.get_irc_name()))

    def send_channel_messages(self, channel):
        """Retrieves and sends the messages of a given channel to the IRC client connection."""
        messages = self.gateway.flow_service.EnumerateMessages(
            self.gateway.flow_sid, channel.organization_id, channel.channel_id)
        for message in reversed(messages):
            member = channel.get_member_from_account_id(
                message["SenderAccountID"])
            if member:
                message_text = message["Text"]
                if self.gateway.show_timestamps:
                    message_timestamp = irc_util.get_message_timestamp_string(
                        message["CreationTime"])
                    message_text = message_timestamp + " " + message_text
                if member.account_id == self.gateway.flow_account_id:
                    message_nickname = member.nickname
                else:
                    message_nickname = member.get_irc_nickname()
                self.message(":%s!%s@%s PRIVMSG %s :%s" %
                             (message_nickname, member.user, member.host, channel.get_irc_name(), message_text))
