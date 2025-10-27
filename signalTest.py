import psutil
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.clock import Clock

class NetworkSignalApp(App):
    def build(self):
        self.layout = FloatLayout()

        # Signal strength icon
        self.signal_icon = Image(source="images/signal_0.png", size_hint=(None, None), size=(50, 50), pos_hint={'right': 1, 'top': 1})
        self.layout.add_widget(self.signal_icon)

        # Signal strength label
        self.signal_label = Label(text="Strength: Checking...", size_hint=(None, None), size=(200, 50), 
                                  pos_hint={'right': 0.9, 'top': 0.92})
        self.layout.add_widget(self.signal_label)

        # Schedule updates to the signal strength
        Clock.schedule_interval(self.update_signal, 2)  # Update every 2 seconds
        return self.layout

    def update_signal(self, dt):
        try:
            # Simulate signal strength (Replace with real logic)
            stats = psutil.net_io_counters()
            signal_strength = int(stats.bytes_recv / 1e6) % 5  # Simulated strength (0 to 4)

            # Update the icon and label
            self.signal_icon.source = f"images/signal_{signal_strength}.png"
            self.signal_label.text = f"Strength: {signal_strength}/4"
        except Exception as e:
            self.signal_label.text = f"Error: {str(e)}"

if __name__ == '__main__':
    NetworkSignalApp().run()