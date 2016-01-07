"""
Flow API Python Module
"""

import sys
import subprocess
import json
import requests
import signal


class Flow(object):

    def __init__(self, flowappgluebinary_path, debug=False):
        """Starts the flowappglue local server"""
        self.debug = debug
        self._StartFlowAppGlue(flowappgluebinary_path)

    def __del__(self):
        if self._flowappglue:
            self._flowappglue.terminate()

    def _print_debug(self, msg):
        if self.debug:
            print(msg.encode('utf-8'))
            sys.stdout.flush()

    def _signal_handler(self, signal, frame):
        print("... terminating ...")
        if self._flowappglue:
            self._flowappglue.terminate()
        sys.exit(0)

    def _Run(self, method, params):
        request_str = json.dumps(
            dict(
                method=method,
                params=[params],
                token=self._token))
        self._print_debug("request: %s" % request_str)
        response = requests.post(
            "http://localhost:%s/rpc" %
            self._port,
            headers={
                'Content-type': 'application/json'},
            data=request_str)
        response_data = json.loads(response.text)
        self._print_debug(
            "response: HTTP %s : %s" %
            (response.status_code, response.text))
        if "error" in response_data.keys() and len(response_data["error"]) > 0:
            raise Flow.FlowError(response_data["error"])
        if "result" in response_data.keys():
            return response_data["result"]
        else:
            return response_data

    def _StartFlowAppGlue(self, flowappgluebinary_path):
        self._flowappglue = subprocess.Popen(
            [flowappgluebinary_path, "0"], stdout=subprocess.PIPE)
        token_port_line = self._flowappglue.stdout.readline().rstrip().split(", ")
        self._token = token_port_line[0].split(":")[1][1:-1]
        self._port = token_port_line[1].split(":")[1][1:-2]
        signal.signal(signal.SIGINT, self._signal_handler)

    def Config(
            self,
            flow_serv_host,
            flow_serv_port,
            flow_local_database_dir,
            flow_local_schema_dir,
            use_tls="true"):
        """Sets up the basic configuration parameters for FlowApp to talk FlowServ and create local accounts. Returns 'null'."""
        self._Run(method="Config", params=dict(
            FlowServHost=flow_serv_host,
            FlowServPort=flow_serv_port,
            FlowLocalDatabaseDir=flow_local_database_dir,
            FlowLocalSchemaDir=flow_local_schema_dir,
            FlowUseTLS=use_tls,
        ))

    def NewSession(self, email, server_uri):
        """Creates a new session for the given user, even if it doesn't exist. Returns an integer representing a SessionID."""
        response = self._Run(method="NewSession", params=dict(
            EmailAddress=email,
            ServerURI=server_uri,
        ))
        return response["SessionID"]

    def StartUp(self, sid):
        """Starts the flowapp instance (notification internal loop, etc) for an account that is already created and
        has a device already configured in the current device. Returns 'null'.
        """
        self._Run(method="StartUp", params=dict(
            SessionID=sid,
        ))

    def CreateAccount(
            self,
            sid,
            phone_number,
            device_name,
            email,
            server_uri,
            password,
            totpverifier=""):
        """Creates an account with the specified data. 'PhoneNumber', along with 'EmailAddress' and 'ServerURI'
        (these last two provided at 'NewSession') must be unique. Returns 'null'.
        """
        return self._Run(method="CreateAccount", params=dict(
            SessionID=sid,
            PhoneNumber=phone_number,
            DeviceName=device_name,
            EmailAddress=email,
            ServerURI=server_uri,
            Password=password,
            TotpVerifier=totpverifier,
        ))

    def NewOrg(self, sid, name, discoverable):
        """Creates a new organization. Returns an 'Org' dict."""
        return self._Run(method="NewOrg", params=dict(
            SessionID=sid,
            Name=name,
            Discoverable=discoverable,
        ))

    def NewChannel(self, sid, oid, name):
        """Creates a new channel in a specific 'OrgID'. Returns a string that represents the `ChannelID` created"""
        return self._Run(method="NewChannel", params=dict(
            SessionID=sid,
            OrgID=oid,
            Name=name,
        ))

    def EnumerateOrgs(self, sid):
        """Lists all the orgs the caller is a member of. Returns array of 'Org' dicts."""
        return self._Run(method="EnumerateOrgs", params=dict(
            SessionID=sid,
        ))

    def EnumerateChannels(self, sid, oid):
        """Lists the channels available for an 'OrgID'. Returns an array of 'Channel' dicts."""
        return self._Run(method="EnumerateChannels", params=dict(
            SessionID=sid,
            OrgID=oid,
        ))

    def EnumerateChannelMembers(self, sid, cid):
        """Lists the channel members for a given 'ChannelID'. Returns an array of 'ChannelMember' dicts."""
        return self._Run(method="EnumerateChannelMembers", params=dict(
            SessionID=sid,
            ChannelID=cid,
        ))

    def SendMessage(self, sid, oid, cid, msg, other_data={}):
        """Sends a message to a channel this user is a member of. Returns a string that represents the 'MessageID' that has just been sent."""
        return self._Run(method="SendMessage", params=dict(
            SessionID=sid,
            OrgID=oid,
            ChannelID=cid,
            Text=msg,
            OtherData=other_data,
        ))

    def WaitForNotification(self, sid):
        """Returns the oldest unseen notification in the queue for this device.
        WARNING: it will block until there's a new notification if there isn't any at
        the time it is called. It's advised to call this method in a thread outside of
        the main one. Returns a 'Change' dict.
        """
        return self._Run(method="WaitForNotification", params=dict(
            SessionID=sid,
        ))

    def EnumerateMessages(self, sid, oid, cid, filters={}):
        """Lists all the messages for a channel. Returns an array of 'Message' dicts"""
        return self._Run(method="EnumerateMessages", params=dict(
            SessionID=sid,
            OrgID=oid,
            ChannelID=cid,
            Filters=filters,
        ))

    def GetChannel(self, sid, cid):
        """Returns all the metadata for a channel the user is a member of. Returns a 'Channel' dict."""
        return self._Run(method="GetChannel", params=dict(
            SessionID=sid,
            ChannelID=cid,
        ))

    def NewOrgJoinRequest(self, sid, oid):
        """Creates a new request to join an existing organization. Return 'null'."""
        return self._Run(method="NewOrgJoinRequest", params=dict(
            SessionID=sid,
            OrgID=oid,
        ))

    def EnumerateOrgJoinRequests(self, sid, oid):
        """Lists all the join requests for an 'OrgID'. Returns an array of 'OrgJoinRequest' dicts"""
        return self._Run(method="EnumerateOrgJoinRequests", params=dict(
            SessionID=sid,
            OrgID=oid,
        ))

    def OrgAddMember(self, sid, oid, account_id, member_state):
        """Adds a member to an organization, assuming the user has the proper permissions. Returns 'null'.
        'member_state' argument valid values are 'm' (member), 'a' (admin), 'o' (owner), 'b' blocked
        """
        return self._Run(method="OrgAddMember", params=dict(
            SessionID=sid,
            OrgID=oid,
            MemberAccountID=account_id,
            MemberState=member_state,
        ))

    def ChannelAddMember(self, sid, oid, cid, account_id, member_state):
        """Adds the specified member to the channel as long as the requestor has the right permissions. Returns 'null'."""
        return self._Run(method="ChannelAddMember", params=dict(
            SessionID=sid,
            OrgID=oid,
            ChannelID=cid,
            MemberAccountID=account_id,
            MemberState=member_state,
        ))

    def Close(self, sid):
        """Closes a session and cleanly finishes any long running operations. It could be seen as a logout. Returns 'null'."""
        return self._Run(method="Close", params=dict(
            SessionID=sid,
        ))

    class FlowError(Exception):
        pass