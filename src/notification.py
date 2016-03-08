"""
notification.py
"""

import common
from channel import ChannelMember, PendingChannel, Channel, DirectChannel


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
            oid = org["ID"]
            organization_name = org["Name"]
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
            oid = channel_data["OrgID"]
            channel_id = channel_data["ID"]
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
        channel_id = message["ID"]
        channel_name = message["Name"]
        direct_channel = message["Purpose"] == "direct message"
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
        sender_account_id = message["SenderAccountID"]
        channel_id = message["ChannelID"]
        message_text = message["Text"]
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
                message["CreationTime"])
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
        channel_messages = messages_data["ChannelMessages"]
        if channel_messages:
            for message in channel_messages:
                self.process_channel_message(message)

        regular_messages = messages_data["RegularMessages"]
        if regular_messages:
            for message in regular_messages:
                self.process_regular_message(message)

    def channel_member_notification(self, channel_ids):
        """Processes 'channel-member-event' notifications."""
        for channel_id in channel_ids:
            channel = self.gateway.get_channel(channel_id)
            # A channel-member-event may arrive before 'channel' and 'message'
            # notifications
            if not channel:
                continue
            members = self.gateway.flow_service.enumerate_channel_members(
                channel_id)
            for member in members:
                if not channel.get_member_from_nickname(
                        member["EmailAddress"]):
                    channel_member = ChannelMember(member["EmailAddress"],
                                                   member["AccountID"],
                                                   channel.organization_name)
                    channel.add_member(channel_member)
                    self.gateway.notify_clients(
                        ":%s!%s@%s JOIN :%s" %
                        (channel_member.get_irc_nickname(),
                         channel_member.user,
                         channel_member.host,
                         channel.get_irc_name()))
