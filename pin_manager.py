from gpiozero import Buzzer, DistanceSensor, MotionSensor

# Define GPIO pin assignments
BUZZER_PIN = 0
TRIGGER_PIN = 23
ECHO_PIN = 24
PIR_PIN = 22

# Initialize shared GPIO devices (global variables)
buzzer = Buzzer(BUZZER_PIN)
sensor = DistanceSensor(echo=ECHO_PIN, trigger=TRIGGER_PIN, max_distance=4)
pir = MotionSensor(PIR_PIN)

def cleanup():
    """Release all GPIO resources."""
    if buzzer is not None:
        buzzer.close()
        print("Buzzer cleaned up.")
    if sensor is not None:
        sensor.close()
        print("Sensor cleaned up.")
    if pir is not None:
        pir.close()
        print("Motion sensor cleaned up.")
        
        
