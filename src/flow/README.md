# Python Flow API Module

## Description

This simple Python module allows you to interact with the Flow API from Python scripts.

## Usage

You must perform the operations in the following order:

1. Create the Flow object:
  ```
  from flow.flow_api import Flow
  ...
  # This will start the flowappglue server as a subprocess
  flow = Flow("/path/to/flowappglue")
  ```

2. Run Flow.Config():
  ```
  flow.Config("1.2.3.4", 443, "/path/to/db/", "/path/to/schemas/")
  ```

3. Start your session:
  ```
  sid = flow.NewSession(email="account@test.com", uri="flow.spideroak.com")
  ```

4. Use the sid to perform operations using account "account@test.com"
  ```
  orgs = flow.EnumerateOrgs(sid)
  # orgs now contains an array of "Org" dicts.
  ```

5. To finish performing API operations with "account@test.com" you should log-off:
  ```
  flow.Close(sid)
  ```

6. Once you are done using the Flow API you need to call Flow.Terminate():
  ```
  # This will kill the flowappglue subprocess started on Flow.Flow()
  flow.Terminate()
  ```

## Examples

- [scripts/gen_data.py](../scripts/gen_data.py): Creates two accounts and a few orgs and channels.
- [scripts/gen_dc.py](../scripts/gen_dc.py): Starts a Direct Conversation from one account to another.
