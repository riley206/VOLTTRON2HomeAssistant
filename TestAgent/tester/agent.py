"""
Agent documentation goes here.
"""

__docformat__ = 'reStructuredText'

import logging
import sys
from volttron.platform.agent import utils
from volttron.platform.vip.agent import Agent, Core, RPC
import requests
from requests import get
import json
_log = logging.getLogger(__name__)
utils.setup_logging()
__version__ = "0.1"



def tester(config_path, **kwargs):
    """
    Parses the Agent configuration and returns an instance of
    the agent created using that configuration.

    :param config_path: Path to a configuration file.
    :type config_path: str
    :returns: Tester
    :rtype: Tester
    """
    try:
        config = utils.load_config(config_path)
    except Exception:
        config = {}

    if not config:
        _log.info("Using Agent defaults for starting configuration.")
    ip_address = config.get('ip_address', "0.0.0.0")
    setting1 = config.get('setting1', "http://0.0.0.0:8123/api/states/sensor.message_sensor1")
    setting2 = config.get('setting2', "devices/fake-campus/fake-building/fake-device/all")
    access_token = config.get('access_token', "token")
    value_from_topic = config.get('value_from_topic', "OutsideAirTemperature1")

    return Tester(ip_address, setting1, setting2, access_token, value_from_topic, **kwargs)


class Tester(Agent):
    """
    Document agent constructor here.
    """

    def __init__(self, ip_address="0.0.0.0", setting1="0.0.0.0", setting2="some/random/topic", access_token="token", value_from_topic = "", **kwargs):
        super(Tester, self).__init__(**kwargs)
        _log.debug("vip_identity: " + self.core.identity)

        self.ip_address = ip_address
        self.setting1 = setting1
        self.setting2 = setting2
        self.access_token = access_token
        self.value_from_topic = value_from_topic



        self.default_config = {"ip_address": ip_address,
                               "setting1": setting1,
                               "setting2": setting2,
                               "access_token": access_token,
                               "value_from_topic": value_from_topic}

        # Set a default configuration to ensure that self.configure is called immediately to setup
        # the agent.
        self.vip.config.set_default("config", self.default_config)
        # Hook self.configure up to changes to the configuration file "config".
        self.vip.config.subscribe(self.configure, actions=["NEW", "UPDATE"], pattern="config")

    def configure(self, config_name, action, contents):
        """
        Called after the Agent has connected to the message bus. If a configuration exists at startup
        this will be called before onstart.

        Is called every time the configuration in the store changes.
        """
        config = self.default_config.copy()
        config.update(contents)

        _log.debug("Configuring Agent")

        try:
            ip_address = str(config['ip_address'])
            setting1 = str(config["setting1"])
            setting2 = str(config["setting2"])
            access_token = str(config["access_token"])
            value_from_topic = str(config["value_from_topic"])

        except ValueError as e:
            _log.error("ERROR PROCESSING CONFIGURATION: {}".format(e))
            return
        self.ip_address = ip_address
        self.setting1 = setting1
        self.setting2 = setting2
        self.access_token = access_token
        self.value_from_topic = value_from_topic

        self._create_subscriptions(self.setting2)

    def _create_subscriptions(self, topic):
        """
        Unsubscribe from all pub/sub topics and create a subscription to a topic in the configuration which triggers
        the _handle_publish callback
        """
        self.vip.pubsub.unsubscribe("pubsub", None, None)

        self.vip.pubsub.subscribe(peer='pubsub',
                                  prefix=topic,
                                  callback=self._handle_publish)

    def _handle_publish(self, peer, sender, bus, topic, headers, message):
        """
        Callback triggered by the subscription setup using the topic from the agent's config file
        """

        values_from_topics = self.value_from_topic.split("', '") 

        for member1 in values_from_topics:
            for element in message:
                if member1 in element:
                    print("member1", member1)
                    print(f"{member1} = {element}")
                    data1 = json.dumps(element[f"{member1}"])
                    print(f"{member1} ::: {data1}")
                    url = f"http://{self.ip_address}:8123/api/states/sensor.{member1}"
                    print(f"url {url}")
                    headers = {
                        "Authorization": f"Bearer {self.access_token}",
                        "Content-Type": "application/json",
                    }
                    data2 = f'{{"state": {data1}}}'
                    print(f"data2 {data2}")
                    response = requests.post(url, headers=headers, data=data2) # posted data to HA is data2.
                    response2 = requests.get(url, headers=headers, data=data2) # getting it back again
                    print(f"response2 {response2}")
                    print(f"retrieved data2 {data2}")
                    if response.status_code == 200:
                        print(f"----------Sent {data2} successfully----------")
                    else:
                        print(f"Failed to send {data2} to Home Assistant")
                    break
                else:
                    print(f"{member1} not in {element}")
            else:
                print(f"{element} not in message")        
        else:
            print(f"{member1} not in {values_from_topics}")        
  

    @Core.receiver("onstart")
    def onstart(self, sender, **kwargs):
        """
        This is method is called once the Agent has successfully connected to the platform.
        This is a good place to setup subscriptions if they are not dynamic or
        do any other startup activities that require a connection to the message bus.
        Called after any configurations methods that are called at startup.

        Usually not needed if using the configuration store.
        """
        # Example publish to pubsub
        self._create_subscriptions(self.setting2)
        self.vip.pubsub.publish('pubsub', "some/random/topic", message="HI!")

        # Example RPC call
        # self.vip.rpc.call("some_agent", "some_method", arg1, arg2)

    @Core.receiver("onstop")
    def onstop(self, sender, **kwargs):
        """
        This method is called when the Agent is about to shutdown, but before it disconnects from
        the message bus.
        """
        pass

    @RPC.export
    def rpc_method(self, arg1, arg2, kwarg1=None, kwarg2=None):
        """
        RPC method

        May be called from another agent via self.core.rpc.call
        """
        return self.setting1 + arg1 - arg2


def main():
    """Main method called to start the agent."""
    utils.vip_main(tester, 
                   version=__version__)


if __name__ == '__main__':
    # Entry point for script
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        pass
