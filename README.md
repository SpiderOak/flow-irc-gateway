# flow-irc-gateway

## Description

Local gateway to enable IRC clients to communicate with the Flow API.
By running this gateway you can use your IRC client of preference and connect to the Flow service.

## Features

- On startup, the gateway starts the `flowappglue` REST server to interact with the Flow service.
- Upon an IRC client connection/re-connection, Teams + Channels + Messages are loaded from Flow and shown to the IRC client. The user can then use the IRC client just like on any IRC network.
- Teams and channels are listed in the MOTD (Message Of The Day).
- The IRC nickname is defined by the gateway upon registration and cannot be changed.
- Channels and Direct Conversation the user becomes a member of, show up automatically on the IRC client.
- Direct Conversations can be started from the IRC client (see "IRC Clients Configuration and Commands" section below).
- Supported IRC commands: 'LIST', 'PRIVMSG', 'WHOIS', 'WHO', 'MOTD' & 'LUSERS'.
- Tested with weechat, irssi and xchat/hexchat.
- The gateway uses UTF-8 encoding.
- Makes use of the [flow-python](https://github.com/SpiderOak/flow-python) module.

## Installation

Run the following on the command line (this will be modified in the future when available in pypi):
```
$ git clone https://github.com/SpiderOak/flow-python.git
$ cd flow-python
$ sudo python setup.py install
$ cd -
$ git clone https://github.com/SpiderOak/flow-irc-gateway.git
$ cd flow-irc-gateway
$ sudo python setup.py install
```

## Run

You can just run it without arguments:
```
# To run it without config/args first you need to run semaphor and log in with an account.
$ flow-irc-gateway
...
# You can now connect your IRC client to localhost:6667
```
or you can override the defaults with a config file and a specific username:
```
$ flow-irc-gateway --config config.cfg --username username@site.com
...
# You can now connect your IRC client to localhost:6667
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

Normally you won't need a config file to run the gateway. But you can see a sample configuration file under [config/config.example.cfg](config/config.example.cfg). 

## IRC Clients Configuration and Commands

- Channels are displayed as `#ChannelName(TeamName)`, if there are channel name collisions, then a '-' and the first 5 characters of the ChannelID are appended.
- Members are displayed as `MemberName(TeamName)`
- Direct Conversation started from the IRC client (in-session) are displayed as `MemberName(TeamName)`, see below on how you can start one from each IRC client.
- Loaded Direct Conversations are displayed as `MemberName(TeamName)-$ID`, where ID are the first 5 characters of the ChannelID. This is so you can have more than one Direct Conversation with the same member.

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
    - Create new teams/channels.
    - Join existing teams/channels.
    - Request to join teams.
  - Start two Direct Conversations with the same member within the same session.
- The gateway can only be used with one IRC client at a time.
- With xchat/hexchat, if you are a member of several Channels (40+), then you may notice that it takes many seconds 
for the gateway to start-up. Both IRC clients do not execute user actions until all "MODE" commands for all the channels are received (this does not happen with irssi or weechat).
More research on this is underway.
- IRC channels are identified by name, Flow channels within a team can have the same name. 
The gateway currently adds the five first chars of the ChannelID as a suffix to the name to overcome this limitation.

## TODO

- Combine SpiderOak's license with miniircd's author license.
- Make the following configurable:
 - nickname space character and "," replacement (see [src/common.py](src/common.py)).
 - timestamp format (see [src/common.py](src/common.py)).
- Add unit/integration tests to flow-irc-gateway.
- Process "org-member-event" notifications to notify of other member joining teams the user is part of.
- Print debug output to a log file (use python's `logging`)
- Many sections of the code assume the existence of simultaneuos IRC client connections (see variable self.clients in [src/flow_irc_gateway.py](src/flow_irc_gateway.py)). This needs to be cleaned up, the gateway only support one IRC client connection at a time.
- Gracefully handle Flow.FlowError exceptions.
- Handle banned channel/org members

