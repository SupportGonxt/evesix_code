from gpiozero import OutputDevice
from time import sleep

relay = OutputDevice(20)

try:
    while True:
        relay.on()   # Turn relay on
        sleep(2)     # Wait for 2 seconds
        print("the relay is down")
        relay.off()  # Turn relay off
        sleep(2)     # Wait for 2 seconds
        print("the relay is up")
except KeyboardInterrupt:
    pass

