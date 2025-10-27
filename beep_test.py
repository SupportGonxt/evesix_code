from gpiozero import Buzzer
from time import sleep
from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout

BUZZER_PIN = 0  # GPIO pin for the buzzer

# Initialize the Buzzer
buzzer = Buzzer(BUZZER_PIN)

class BuzzerApp(App):
    def build(self):
        layout = BoxLayout(orientation='vertical')

        start_button = Button(text='Start Beeping')
        stop_button = Button(text='Stop Beeping')

        start_button.bind(on_press=self.start_beeping)
        stop_button.bind(on_press=self.stop_beeping)

        layout.add_widget(start_button)
        layout.add_widget(stop_button)

        return layout

    def start_beeping(self, instance):
        print("Beeping started!")
        self.running = True
        while self.running:
            buzzer.on()
            sleep(0.2)
            buzzer.off()
            sleep(0.2)

    def stop_beeping(self, instance):
        print("Beeping stopped!")
        self.running = False
        buzzer.off()

try:
    BuzzerApp().run()

except KeyboardInterrupt:
    print("\nProgram stopped by user")

finally:
    buzzer.off()  # Ensure the buzzer is turned off
    print("Buzzer has been turned off")
