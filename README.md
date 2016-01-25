# flow-irc-gateway

## Description

Local gateway to enable IRC clients to communicate with the Flow API.
By running this gateway you can use your IRC client of preference and connect to the Flow service.

## Features

- On startup, the gateway starts the `flowappglue` REST server to interact with the Flow service.
- Upon an IRC client connection, Organizations + Channels + Messages are loaded from Flow and shown to the IRC client.
The user can then use the IRC client just like on any IRC network.
- Organizations and channels are listed in the MOTD (Message Of The Day).
- The IRC nickname is defined by the gateway upon registration and cannot be changed.
- Channels and Direct Conversation the user becomes a member of, show up automatically on the IRC client.
- Direct Conversations can be started from the IRC client (see "IRC Clients Configuration and Commands" section below).
- Supported IRC commands: 'LIST', 'PRIVMSG', 'WHOIS', 'WHO', 'MOTD', 'MODE' & 'LUSERS'.
- Tested with weechat, irssi and xchat/hexchat.
- The gateway uses UTF-8 encoding.

## Installation

Run the following on the command line: (uses `python-setuptools`)
```
$ git clone https://github.com/SpiderOak/flow-irc-gateway.git
$ cd flow-irc-gateway
$ sudo python setup.py install
```

## Run

```
$ flow-irc-gateway --config config.cfg --username username@site.com
```

## Configuration

flow-irc-gateway takes a python config .cfg file as input with a section named `[flow-irc-gateway]`.

List of config variables:
- `username`: Flow username
- `server`: Flow service host/ip
- `port`: Flow service port
- `flowappglue`: Path to the flowappglue binary
- `db`: Flow database directory
- `schema`: Flow schema directory
- `uri`: Flow account gateway uri
- `show-timestamps`: If enabled, it prepends timestamps on messages (format: [Y-m-d H:M:S])
- `verbose`: Be verbose (print some progress messages to stdout)
- `debug`: Print debug messages to stdout
- `irc-ports`: IRC listen ports (a list separated by comma or whitespace)
- `daemon`: Fork and become a daemon.

See a sample configuration file under: `config/config.example.cfg`

## IRC Clients Configuration and Commands

### irssi:
```
# create windows for all channels at startup
/SET autocreate_windows ON

# hide irssi message timestamps
/SET timestamps OFF

# Set UTF-8
/set term_type utf-8

# To open a private message window with a person
/query <nick>
```

### weechat:
```
# remove client message timestamps
/SET weechat.look.buffer_time_format ""

# To open a private message window with a person
/query <nick>
```

### xchat/hexchat:
```
# Set UTF-8
/charset utf8

# To open a private message window with a person use "/query"
# You can also right-click on a member and then click on "Open Dialog Window"
/query <nick>

# To start a Direct Conversation by double-clicking a member, you must configure: 
Settings -> Preferences -> Interface -> User list -> Action Upon Double Click -> Enter "QUERY %s"

# Given that the gateway will forward all conversations every time you connect
# you can disable the display of messages from previous sessions
Chatting -> Logging -> Display scrollback from previous session
```

## Gateway Limitations

- The user is not able to:
  - Perform administrative tasks on the Flow service, like:
    - Create new organizations/channels.
    - Join existing organizations/channels.
    - Request to join organizations.
  - Start two Direct Conversations with the same member within the same session.
- The gateway can only be used with one IRC client at a time.
- With xchat/hexchat, if you are a member of several Channels (40+), then you may notice that it takes many seconds 
for the gateway to start-up. Both IRC clients do not execute user actions until all "MODE" commands for all the channels are received (this does not happen with irssi or weechat).
More research on this is underway.
- IRC channels are identified by name, Flow channels within an Organization can have the same name. 
The gateway currently adds the five first chars of the ChannelID as a suffix to the name to overcome this limitation.

## TODO

- Combine SpiderOak's license with miniircd's author license.
- Make the following configurable:
 - nickname space character and "," replacement (see [src/common.py](src/common.py)).
 - timestamp format (see [src/common.py](src/common.py)).
- Add unit test to the Flow module, and to flow-irc-gateway itself.
- Process "org-member-event" notifications to notify of other member joining organizations the user is part of.
- Print debug output to a log file.

