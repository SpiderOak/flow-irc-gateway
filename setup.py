from setuptools import setup, find_packages

setup(name = "Flow-IRC-Gateway",
      version = "0.1",
      package_dir = { "": "src" },
      py_modules = [ "common", "irc_client", "channel", "flow.flow_api", "notification" ],
      scripts = [ "src/flow-irc-gateway" ], 
      install_requires = [ "requests" ],
      keywords = [ "spideroak", "irc", "flow", "gateway", "semaphor" ],
      author = "Lucas Manuel Rodriguez",
      author_email = "lucas@spideroak-inc.com",
      description = "flow-irc-gateway is a small IRC gateway to SpiderOak Flow (based off of miniircd)",
)
