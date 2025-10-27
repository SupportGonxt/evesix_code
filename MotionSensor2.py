from gpiozero import DistanceSensor
from time import sleep

# Sensor pins
trigger_pin = 23
echo_pin = 24

# Create a DistanceSensor object
sensor = DistanceSensor(echo=echo_pin, trigger=trigger_pin, max_distance=4)

while True:
    distance = sensor.distance * 100  # Convert to centimeters
    print("Distance:", distance, "cm")
    sleep(0.01)  # Adjust the delay as needed