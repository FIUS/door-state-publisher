import signal
import sys
from os import environ
import socket
from logging import Logger
import RPi.GPIO as GPIO
from paho.mqtt import client as mqtt_client

QOS = 1
RETAIN = True

logger = Logger(__name__)


def die(*args: object):
    raise SystemExit(args)


def load_from_env(name: str, default=None) -> str:
    return environ.get(name) or default or die(f"Need the {name} in env")


def signal_handler(sig, frame):
    GPIO.cleanup()
    sys.exit(0)


class Main():

    def __init__(self,
                 gpio_pin: int,
                 mqtt_broker: str,
                 mqtt_port: int,
                 mqtt_user: str,
                 mqtt_pw: str,
                 mqtt_topic: str) -> None:
        self.GPIO_PIN: int = gpio_pin
        self.MQTT_BROKER: str = mqtt_broker
        self.MQTT_PORT: int = mqtt_port
        self.MQTT_USER: str = mqtt_user
        self.MQTT_PW: str = mqtt_pw
        self.MQTT_TOPIC: str = mqtt_topic

        self.CLIENT_ID: str = f'door-state-publisher-{socket.gethostname()}-{self.GPIO_PIN}'

        # Connect to mqtt
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                logger.info("Connected to MQTT Broker!")
            else:
                logger.warn("Failed to connect to broker, return code %d\n", rc)
        self.client = mqtt_client.Client(self.CLIENT_ID)
        self.client.username_pw_set(self.MQTT_USER, self.MQTT_PW)
        self.client.on_connect = on_connect
        self.client.will_set(self.MQTT_TOPIC, "closed", qos=QOS, retain=RETAIN)
        self.client.connect(self.MQTT_BROKER, self.MQTT_PORT, keepalive=10)
        self.client.loop_start()

    def send_update(self, _=None):
        if not GPIO.input(self.GPIO_PIN):
            logger.debug("Button pressed!")
            self.client.publish(self.MQTT_TOPIC, "closed", qos=QOS, retain=RETAIN)
        else:
            logger.debug("Button released!")
            self.client.publish(self.MQTT_TOPIC, "open", qos=QOS, retain=RETAIN)

    def run(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.GPIO_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(self.GPIO_PIN, GPIO.BOTH,
                              callback=self.send_update, bouncetime=500)
        self.send_update()
        signal.signal(signal.SIGINT, signal_handler)
        signal.pause()


def main():
    GPIO_PIN: int = int(load_from_env("GPIO_PIN"))
    MQTT_BROKER: str = load_from_env("MQTT_BROKER")
    MQTT_PORT: int = int(load_from_env("MQTT_PORT", "1883"))
    MQTT_USER: str = load_from_env("MQTT_USER")
    MQTT_PW: str = load_from_env("MQTT_PW")
    MQTT_TOPIC: str = load_from_env("MQTT_TOPIC")
    main = Main(GPIO_PIN, MQTT_BROKER, MQTT_PORT, MQTT_USER, MQTT_PW, MQTT_TOPIC)
    main.run()


if __name__ == '__main__':
    main()
