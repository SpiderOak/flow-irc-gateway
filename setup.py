from setuptools import setup, find_packages

setup(name = "flow-irc-gateway",
      version = "0.1",
      package_dir = { "": "src" },
      py_modules = [ "common", "irc_client", "channel", "notification" ],
      scripts = [ "src/flow-irc-gateway" ], 
      # TODO: change as soon as flow-python is available at pypi
      # install_requires = [ "flow-python" ],  
      keywords = [ "spideroak", "irc", "flow", "gateway", "semaphor" ],
      author = "Lucas Manuel Rodriguez",
      author_email = "lucas@spideroak-inc.com",
      description = "flow-irc-gateway is a small IRC gateway to " \
                    "SpiderOak Flow (based off of miniircd)",
)
