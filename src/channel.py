"""
channel.py
"""

from collections import namedtuple

from . import common


class ChannelMember(object):
    """Represents a member of a IRC/Flow channel"""

    def __init__(self, username, account_id, organization_name,
                 user="", host="", realname=""):
        """Arguments:
        username : string, Account username.
        account_id : string, Account's accountId.
        organization_name : string, Organization's Name
        user, host and realname: string, IRC attributes reserved for later use
        """
        self.nickname = common.irc_escape(username)
        self.account_id = account_id
        self.organization_name = common.irc_escape(organization_name)
        self.user = user
        self.host = host
        self.realname = realname

    def get_irc_nickname(self):
        """Returns the IRC nickname identification
        for this member: 'Username(OrgName)'.
        """
        return self.nickname + "(" + self.organization_name + ")"


class Channel(object):
    """Represents a IRC/Flow Channel"""

    def __init__(self, gateway, channel_id, channel_name="",
                 organization_id="", organization_name=""):
        """Arguments:
        gateway : FlowIRCGateway, reference to the FlowIRCGateway object
        channel_id : string, Channel's channelId.
        channel_name : string, Channel's Name.
        organization_id : string, Organization's orgId.
        organization_name : string, Organization's Name.
        """
        self.gateway = gateway
        self.members = set()  # set of "channelMember"
        self.channel_id = channel_id
        self.channel_name = channel_name
        self.organization_id = organization_id
        self.organization_name = organization_name
        self.name_collides = False

    def channel_suffix(self):
        """Returns a suffix with the first last 5 chars of the channelId.
        IRC channels are identified with their name, so you can't have
        two channels with the same name. This suffix is used to display
        Flow Channels with the same name within an Organization.
        """
        return "-" + self.channel_id[:5]

    def get_irc_name(self):
        """Returns the IRC name of the Channel.
        Format: #ChannelName(TeamName).
        If there are two channels with the same name within an Organization,
        then channel_suffix() is used.
        """
        append_id = self.channel_suffix() if self.name_collides else ""
        return "#" + common.irc_escape(self.channel_name) + "(" + \
            common.irc_escape(self.organization_name) + ")" + append_id

    def get_member_from_account_id(self, account_id):
        """Returns the member within this channel given an account_id
        Arguments:
        account_id : string, represents the member accountId
        Returns a 'ChannelMember' instance.
        Returns 'None' if the member does not exist within this channel.
        """
        for member in self.members:
            if member.account_id == account_id:
                return member
        return None

    def add_member(self, member):
        """Adds a member to this channel.
        Arguments:
        member : 'ChannelMember' instance, member to add to the channel.
        """
        self.members.add(member)


class DirectChannel(Channel):
    """Represents a Direct Conversation IRC/Flow Channel"""

    def __init__(self, gateway, channel_id, organization_id="",
                 organization_name="", created_on_irc_session=False):
        """Arguments:
        created_on_irc_session : boolean, sets whether the direct conversation
        was started from the IRC client on the current IRC session.
        """
        super(
            DirectChannel,
            self
        ).__init__(
            gateway,
            channel_id,
            "",
            organization_id,
            organization_name
        )
        self.created_on_irc_session = created_on_irc_session

    def get_irc_name(self):
        """Returns the IRC name of the Channel.
        If the channel was created on the current IRC session,
        then it returns the following:
            #OtherMember(TeamName)
        If the conversation was not created on the current IRC session or
        it was started by the other member, then the following is returned:
            #OtherMember(TeamName)-Suffix
        """
        other = self.get_other_dc_member()
        assert other
        if self.created_on_irc_session:
            return other.get_irc_nickname()
        else:
            return "#" + other.nickname + \
                "(" + common.irc_escape(self.organization_name) + ")" + \
                self.channel_suffix()

    def get_other_dc_member(self):
        """Returns the 'ChannelMember' that is not
        the logged-in account on this gateway.
        """
        assert len(self.members) == 2, "%s" % self.members
        for member in self.members:
            if member.account_id != self.gateway.flow_account_id:
                return member
        return None

# Tuple to store 'channel' notifications data until the first 'message'
# notification arrives
PendingChannel = namedtuple(
    "PendingChannel", [
        "id", "name", "oid", "org_name"])
