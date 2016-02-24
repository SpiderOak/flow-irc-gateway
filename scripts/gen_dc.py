#! /usr/bin/env python
"""
A Python Script that looks for organizations and channels and starts a direct conversation with the first user in the list using the Python Flow module.

Usage:

    ./gen_data.py \
        --debug \
        --server=45.55.26.105 \
        --port=4443 \
        --db=/home/john/.config/flow-alpha/ \
        --schema=/home/john/FlowAlpha/resources/app/schema/ \
        --flowappglue=/home/john/FlowAlpha/resources/app/flowappglue \
        --attachment=/home/john/.config/semaphor/downloads/
        --uri=flow.spideroak.com \
        --email=A@testing.com
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
        help="Flow Local Attachments Directory",
        required=True)
    parser.add_argument(
        "--uri",
        default="flow.spideroak.com",
        type=str,
        help="Flow URI Hostname")
    parser.add_argument(
        "--email",
        type=str,
        help="Flow email")
    parser.set_defaults(debug=True)

    args = parser.parse_args()

    flow = Flow(args.flowappglue, args.debug)

    flow.Config(
        args.server,
        args.port,
        args.db,
        args.schema,
        args.attachment)

    email = args.email

    # Log in
    sid = flow.NewSession()
    flow.StartUp(sid, email, args.uri)

    # Start WaitForNotification thread for new account
    account1_thread = threading.Thread(
        target=wait_for_notifications, args=(sid, flow))
    account1_thread.start()

    email2_found = False
    orgs = flow.EnumerateOrgs(sid)
    for org in orgs:
        oid = org["ID"]
        channels = flow.EnumerateChannels(sid, oid)
        for channel in channels:
            cid = channel["ID"]
            members = flow.EnumerateChannelMembers(sid, cid)
            print("- members=")
            email2 = ""
            for member in members:
                acc_email = member["EmailAddress"]
                print("  %s" % acc_email)
                if email != acc_email:
                    email2 = acc_email
                    account_id_2 = member["AccountID"]
                    email2_found = True
                    break
            if email2_found:
                break
        if email2_found:
            break

    if not email2:
        print("Peer to start conversation could not be found")
    else:    
        # Start a new direct conversation and send a message
        cid3 = flow.NewDirectConversation(sid, oid, account_id_2)
        print("Direct Conversation Channel ID: '%s'" % cid3)
        flow.SendMessage(sid, oid, cid3, "A Personal Message!")

    # Close session
    flow.Close(sid)

    account1_thread.join()

    flow.Terminate()

    print("Finished.")


if __name__ == '__main__':
    main()
