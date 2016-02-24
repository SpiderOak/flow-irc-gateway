#! /usr/bin/env python
"""
A Python Script that generates the following synthetic data using the Python Flow module:

    - Created two Accounts, Account_1 and Account_2
    - Account_1 creates one Organization with one Channel
    - Account_1 sends message to channel
    - Account_2 sends Join Request to the Organization
    - Account_1 accepts Account_2 Organization Join Request
    - Account_1 also sends invite to join the Channel to Account_2
    - Account_1 creates an extra organization with a channel
    - Account_1, proactively, adds Account 2 to newly created Org
    - Account_1, proactively, adds Account 2 to newly created Channel
    - Account_1 and Account_2 loop on WaitForNotification
    - Close both sessions

Usage:

    ./gen_data.py \
        --debug \
        --server=45.55.26.105 \
        --port=4443 \
        --db=/home/john/.config/flow-alpha/ \
        --schema=/home/john/FlowAlpha/resources/app/schema/ \
        --flowappglue=/home/john/FlowAlpha/resources/app/flowappglue \
        --uri=flow.spideroak.com \
        --attachment=/home/john/.config/semaphor/downloads/
        > output.txt
"""

import sys
sys.path.append('../src')
from flow.flow_api import Flow
import argparse
import random
import string
import time
import threading


def wait_for_notifications(sid, flow):
    while True:
        time.sleep(5)
        try:
            flow.WaitForNotification(sid)
        except Flow.FlowError as e:
            try:
                if str(e) == "Unknown session":
                    break
            except UnicodeEncodeError:
                pass


def main():

    parser = argparse.ArgumentParser(
        description="Flow Synthetic Data Generator")
    parser.add_argument(
        "--flowappglue",
        metavar="PATH",
        type=str,
        default="./flowappglue",
        help="flowappglue Binary Path")
    parser.add_argument("--debug", action="store_true", help="Debug Mode")
    parser.add_argument(
        "--server",
        type=str,
        help="Flow Service Hostname/IP",
        required=True)
    parser.add_argument(
        "--port",
        type=str,
        help="Flow Service Port",
        required=True)
    parser.add_argument(
        "--db",
        type=str,
        help="Flow Local Database Directory",
        required=True)
    parser.add_argument(
        "--schema",
        type=str,
        help="Flow Local Schema Directory",
        required=True)
    parser.add_argument(
        "--attachment",
        type=str,
        help="Flow Local Attachment Directory",
        required=True)
    parser.add_argument(
        "--uri",
        default="flow.spideroak.com",
        type=str,
        help="Flow URI Hostname")
    parser.set_defaults(debug=True)

    args = parser.parse_args()

    device_name = "TestDevice"
    password = "testpass"
    email = "".join(random.choice(string.ascii_lowercase)
                    for _ in range(10)) + "@testing.com"
    phone_number = "".join(
        random.choice(
            string.ascii_uppercase +
            string.digits) for _ in range(10))
    org_name = "Team-" + \
        "".join(random.choice(string.ascii_uppercase + string.digits)
                for _ in range(10))
    channel_name = "Channel-" + \
        "".join(random.choice(string.ascii_uppercase + string.digits)
                for _ in range(10))
    message_text = "Test Message %d!" % (random.randint(1, 300))

    flow = Flow(args.flowappglue, args.debug)

    flow.Config(
        args.server,
        args.port,
        args.db,
        args.schema,
        args.attachment)

    # Create one account with one organization and one channel
    sid = flow.NewSession()

    flow.CreateAccount(
        sid,
        phone_number,
        device_name,
        email,
        args.uri,
        password)

    # Start WaitForNotification thread for new account
    account1_thread = threading.Thread(
        target=wait_for_notifications, args=(sid, flow))
    account1_thread.start()

    org = flow.NewOrg(sid, org_name, True)

    oid = org["ID"]
    channel_id = flow.NewChannel(sid, oid, channel_name)

    time.sleep(3)

    oid = flow.EnumerateOrgs(sid)[0]["ID"]
    channel = flow.EnumerateChannels(sid, oid)[0]
    cid = channel["ID"]
    channel_data = flow.GetChannel(sid, cid)
    print("Organization: %s, Channel: %s" %
          (org["Name"], channel_data["Name"]))
    flow.SendMessage(sid, oid, cid, message_text)
    members = flow.EnumerateChannelMembers(sid, cid)
    print("- members=")
    for member in members:
        print("  %s" % member["EmailAddress"])
    messages = flow.EnumerateMessages(sid, oid, cid)
    print("- messages:")
    for message in messages:
        print("  %s" % message["Text"])

    email = "".join(random.choice(string.ascii_lowercase)
                    for _ in range(10)) + "@testing.com"
    phone_number = "".join(
        random.choice(
            string.ascii_uppercase +
            string.digits) for _ in range(10))
    message_text = "Other Message %d!" % (random.randint(1, 300))

    # Create a second account that wants to join the above organization and
    # channel
    sid2 = flow.NewSession()

    flow.CreateAccount(
        sid2,
        phone_number,
        device_name,
        email,
        args.uri,
        password)

    # Start WaitForNotification thread for new account
    account2_thread = threading.Thread(
        target=wait_for_notifications, args=(sid2, flow))
    account2_thread.start()

    # Account 2 Perform Join Request
    flow.NewOrgJoinRequest(sid2, oid)

    time.sleep(3)

    # Account 1 receives Join Request
    join_requests = flow.EnumerateOrgJoinRequests(sid, oid)
    account_id_2 = join_requests[0]["AccountID"]

    # Account 1 accepts Join Request
    flow.OrgAddMember(sid, oid, account_id_2, "m")

    # Account 1 invites Account 2 to the channel
    flow.ChannelAddMember(sid, oid, channel_id, account_id_2, "m")

    time.sleep(3)

    # Validate Account 2 is part of channel
    channel = flow.EnumerateChannels(sid2, oid)[0]
    assert(channel["ID"] == cid)

    members = flow.EnumerateChannelMembers(sid2, cid)
    print("- members=")
    for member in members:
        print("  %s" % member["EmailAddress"])

    time.sleep(3)

    messages = flow.EnumerateMessages(sid2, oid, cid)
    print("- messages:")
    for message in messages:
        print("  %s" % message["Text"])

    # Create an extra organization and channel
    org_name = "Team-" + \
        "".join(random.choice(string.ascii_uppercase + string.digits)
                for _ in range(10))
    channel_name = "Channel-" + \
        "".join(random.choice(string.ascii_uppercase + string.digits)
                for _ in range(10))
    org2 = flow.NewOrg(sid, org_name, True)
    oid2 = org2["ID"]
    channel_id2 = flow.NewChannel(sid, oid2, channel_name)

    # Proactively Account 1 adds Account 2 to newly created Org
    flow.OrgAddMember(sid, oid2, account_id_2, "m")

    # Proactively Account 1 adds Account 2 to newly created Channel
    flow.ChannelAddMember(sid, oid2, channel_id2, account_id_2, "m")

    # Close sessions for the two accounts
    flow.Close(sid)
    flow.Close(sid2)

    account1_thread.join()
    account2_thread.join()

    flow.Terminate()

    print("Finished.")


if __name__ == '__main__':
    main()
