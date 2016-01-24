from setuptools import setup, find_packages

setup(name = "Flow-IRC-Gateway",
      version = "1.0",
      package_dir = { "": "src" },
      py_modules = [ "common", "irc_client", "channel", "flow.flow_api", "notification" ],
      scripts = [ "src/flow-irc-gateway" ], 
      install_requires = [ "requests" ],
      keywords = [ "spideroak", "irc", "flow", "gateway" ],
      author = "Lucas Manuel Rodriguez",
      author_email = "lucarodriguez@gmail.com",
      description = "flow-irc-gateway is a small IRC gateway to SpiderOak Flow (based off of miniircd)",
)
