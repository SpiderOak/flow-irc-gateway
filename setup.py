from setuptools import setup

setup(name = "flow-irc-gateway",
      version = "0.1",
      packages = [ 'src' ],
      entry_points = {
        "console_scripts": [
        "flow-irc-gateway=src.flow_irc_gateway:main",
        ],
      },
      # TODO: change as soon as flow-python is available at pypi
      # install_requires = [ "flow-python" ],  
      keywords = [ "spideroak", "irc", "flow", "gateway", "semaphor" ],
      author = "Lucas Manuel Rodriguez",
      author_email = "lucas@spideroak-inc.com",
      description = "flow-irc-gateway is a small IRC gateway to " \
                    "SpiderOak Flow (based off of miniircd)",
)
