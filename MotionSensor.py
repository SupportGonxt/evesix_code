from gpiozero import DigitalInputDevice
from time import sleep

# Pin number connected to the RCWL-0516 sensor's output pin
sensor_pin = 22  # Replace with your actual pin number


def main():
    sensor = DigitalInputDevice(sensor_pin, bounce_time=1.2)

    while True:
        if sensor.is_active:
            print("Motion detected!")
        else:
            print("No motion detected.")

        sleep(0.1)  # Adjust the delay as needed


if __name__ == "__main__":
    main()