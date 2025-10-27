from gpiozero  import MotionSensor
from time import sleep


 
# Define the GPIO pin connected to the OUT pin of the RCWL-0516
PIR_PIN = 4  # Change this if using a different GPIO pin
motion_sensor = MotionSensor(PIR_PIN)
print("RCWL-0516 Sensor Active")
print(motion_sensor)
 
try:
    while True:
        motion_sensor.motion_detected()
        print("Motion Detected!")
        sleep(1)  # Delay to prevent multiple triggers
        motion_sensor.wait_for_no_motion()
        print("Motion Stopped")
except KeyboardInterrupt:
    print("Script stopped")
 
