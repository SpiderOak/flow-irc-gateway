"""
notification.py
"""

from . import common
from .channel import ChannelMember, PendingChannel, Channel, DirectChannel


class NotificationHandler(object):
    """A Flow notifications handler.
    It implements callback methods to deal with Flow notifications.
    """

    def __init__(self, gateway):
        """Arguments:
        gateway : FlowIRCGateway instance.
        """
        self.gateway = gateway

    def org_notification(self, organizations_data):
        """Processes 'org' notifications."""
        assert organizations_data
        for org in organizations_data:
            oid = org["id"]
            organization_name = org["name"]
            assert oid
            assert organization_name
            self.gateway.organizations[oid] = organization_name
            self.gateway.get_channels(oid, organization_name)
            for channel in self.gateway.channels.values():
                if channel.organization_id == oid:
                    for client in self.gateway.clients.values():
                        client.send_channel_data(channel)

    def channel_notification(self, channels_data):
        """Processes 'channel' notifications."""
        assert channels_data
        for channel_data in channels_data:
            oid = channel_data["orgId"]
            channel_id = channel_data["id"]
            assert oid
            assert channel_id
            channel = self.gateway.get_channel(channel_id)
            if channel or oid not in self.gateway.organizations:
                # If existing channel or unknown organization, then ignore
                # notification
                continue
            organization_name = self.gateway.organizations[oid]
            self.gateway.pending_channels[channel_id] = PendingChannel(
                channel_id, "", oid, organization_name)

    def process_channel_message(self, message):
        """Processes the 'ChannelMessages' attribute
        of 'channel' notifications.
        """
        channel_id = message["id"]
        channel_name = message["name"]
        direct_channel = message["purpose"] == "direct message"
        assert channel_id
        assert channel_name or direct_channel
        # ChannelMessage notifications may arrive from new_direct_conversation
        # started by the client
        if channel_id not in self.gateway.pending_channels:
            return
        pending_channel = self.gateway.pending_channels[channel_id]
        if direct_channel:
            channel = DirectChannel(
                self.gateway,
                channel_id,
                pending_channel.oid,
                pending_channel.org_name)
        else:
            channel = Channel(
                self.gateway,
                channel_id,
                channel_name,
                pending_channel.oid,
                pending_channel.org_name)
            self.gateway.check_channel_collision(channel)

        self.gateway.get_channel_members(channel)

        self.gateway.add_channel(channel)
        del self.gateway.pending_channels[channel_id]

        for client in self.gateway.clients.values():
            client.send_channel_join_commands(channel)

    def process_regular_message(self, message):
        """Processes the 'RegularMessages' attribute
        of 'channel' notifications.
        """
        sender_account_id = message["senderAccountId"]
        channel_id = message["channelId"]
        message_text = message["text"]
        assert sender_account_id
        assert channel_id
        channel = self.gateway.get_channel(channel_id)
        # 'channel' notification not received yet
        # (this can happen on some occasions, TODO: investigate)
        if not channel:
            return
        sender_member = channel.get_member_from_account_id(sender_account_id)
        assert sender_member
        if self.gateway.show_timestamps:
            message_timestamp = common.get_message_timestamp_string(
                message["creationTime"])
            message_text = message_timestamp + " " + message_text
        # IRC does not support newline within messages
        message_text = message_text.replace("\n", "\\n")
        self.gateway.notify_clients(":%s!%s@%s PRIVMSG %s :%s" %
                                    (sender_member.get_irc_nickname(),
                                     sender_member.user,
                                     sender_member.host,
                                     channel.get_irc_name(),
                                     message_text))

    def message_notification(self, messages_data):
        """Processes 'message' notifications."""
        channel_messages = messages_data["channelMessages"]
        if channel_messages:
            for message in channel_messages:
                self.process_channel_message(message)

        regular_messages = messages_data["regularMessages"]
        if regular_messages:
            for message in regular_messages:
                self.process_regular_message(message)

    def channel_member_notification(self, channel_members_data):
        """Processes 'channel-member-event' notifications."""
        for member_data in channel_members_data:
            channel = self.gateway.get_channel(member_data["channelId"])
            # A 'channel-member-event' may arrive
            # before 'channel' and 'message' notifications
            if not channel:
                continue
            self.process_member(channel, member_data["accountId"])

    def process_member(self, channel, member_account_id):
        """Process a new member for a channel.
        Arguments:
        channel : Channel instance
        member_account_id : string, new member's accountId
        """
        if channel.get_member_from_account_id(member_account_id):
            return
        username = self.gateway.get_username_from_id(member_account_id)
        assert username
        channel_member = ChannelMember(username,
                                       member_account_id,
                                       channel.organization_name)
        channel.add_member(channel_member)
        self.gateway.notify_clients(
            ":%s!%s@%s JOIN :%s" %
            (channel_member.get_irc_nickname(),
             channel_member.user,
             channel_member.host,
             channel.get_irc_name()))
