from kivy.uix.popup import Popup
from kivy.uix.label import Label
import subprocess
from kivy.app import App
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.uix.textinput import TextInput
from gpiozero import DistanceSensor
import warnings
from gpiozero.exc import PWMSoftwareFallback, DistanceSensorNoEcho
from time import sleep
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.clock import Clock
from gpiozero import  Device,Buzzer
from pin_manager import buzzer, sensor
import psutil
from datetime import datetime
from kivy.uix.gridlayout import GridLayout
import mysql.connector
import platform
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics import Color, Rectangle
import socket



# Suppress specific warnings
warnings.filterwarnings("ignore", category=PWMSoftwareFallback)
warnings.filterwarnings("ignore", category=DistanceSensorNoEcho)




#sensor_available = False

# Sensor pins
#trigger_pin = 23
#echo_pin = 24
#BUZZER_PIN = 0  # Change this if using a different GPIO pin

# Initialize the Buzzer
#buzzer = Buzzer(BUZZER_PIN)

class ColoredBoxLayout(BoxLayout):
    def __init__(self, **kwargs):
        super(ColoredBoxLayout, self).__init__(**kwargs)
        with self.canvas.before:
            Color(1, 1, 1, 1)  # White
            self.rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_rect, size=self.update_rect)

    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size


class Diagnose(TabbedPanel):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'diagnose'
        self.do_default_tab = False
        self.tab_pos = 'top_mid'
        self.tab_width = 130
        self._last_distance = None
        self._same_distance_count = 0
        self._max_same_count = 10  # How many times in a row before we suspect a disconnect

      

        # Tab 1: Voltage Usage
        tab1 = TabbedPanelItem(text="PI Voltage Usage", background_color=(0.57, 2, 6.5, 1))
        self.v_text_area = TextInput(hint_text="Command output will appear here", readonly=True, size_hint=(1, 1))
        tab1.add_widget(self.v_text_area)
        self.add_widget(tab1)
        self.default_tab = tab1  # Make this the default selected tab
        Clock.schedule_once(self.voltage_report, 0.1)

        # Tab 2: Sensor
        tab2 = TabbedPanelItem(text="Sensor", background_color=(0.57, 2, 6.5, 1))

        # Main vertical layout
        sensor_layout = BoxLayout(orientation='vertical', spacing=10, padding=10)

        # Sensor distance display (Top row)
        self.sen_text_area = TextInput(
            hint_text="Distance will appear here",  
            readonly=True,
            size_hint=(1, None),
            height=50,
            halign="center",
            padding=(10, 10)
        )

        # Wrapper layout to center image horizontally
        image_wrapper = ColoredBoxLayout(orientation='horizontal', size_hint=(1, 1))


        self.sensor_image = Image(
            source="images/logo1.png",
            size_hint=(None, None),
            size=(100, 100),
            allow_stretch=True,
            keep_ratio=True
        )

        # Add image to the wrapper
        image_wrapper.add_widget(BoxLayout())  # Spacer to push image to center
        image_wrapper.add_widget(self.sensor_image)
        image_wrapper.add_widget(BoxLayout())  # Spacer to push image to center

        # Add widgets to vertical layout
        sensor_layout.add_widget(self.sen_text_area)
        sensor_layout.add_widget(image_wrapper)

        # Add to tab and root
        tab2.add_widget(sensor_layout)
        self.add_widget(tab2)

        # Start sensor updates
        Clock.schedule_interval(self.sensor_report, 0.1)

        # Tab 3: Beeper
        tab3 = TabbedPanelItem(text="Beeper", background_color=(0.57, 2, 6.5, 1))
        
        button_layout = BoxLayout(orientation='vertical', spacing=10, size_hint=(1, 1))

        self.start_button = Button(text="Start Beep", size_hint=(1, 0.5))
        self.start_button.bind(on_release=self.start_beep)
        button_layout.add_widget(self.start_button)

        self.stop_button = Button(text="Stop Beep", size_hint=(1, 0.5))
        self.stop_button.bind(on_release=self.stop_beep)
        button_layout.add_widget(self.stop_button)

        tab3.add_widget(button_layout)
        self.add_widget(tab3)

        # Tab 4: Network Signal
        tab4 = TabbedPanelItem(text="Network Signal", background_color=(0.57, 2, 6.5, 1))
        self.signal_icon = Image(source="images/signal_0.png", size_hint=(1, 1))
        tab4.add_widget(self.signal_icon)
        self.add_widget(tab4)
        Clock.schedule_interval(self.signal_report, 2)
        
        # Tab 5: Network Signal
        tab5 = TabbedPanelItem(text="Bulb Replacement", background_color=(0.57, 2, 6.5, 1))
        # Create the GridLayout: 7 rows (1 header + 6 data), 3 columns
        table = GridLayout(cols=3, rows=7, size_hint=(1, None))
        table.height = 7 * 30  # Adjust height per row if needed
        table.bind(minimum_height=table.setter('height'))

        # Add header row
        headers = ["Bulb Number", "Number of bulbs replaced", "Current Bulb Usage"]
        for title in headers:
            table.add_widget(Label(text=title, bold=True))
        
        mydb = mysql.connector.connect(
        host='localhost',
        user='root',
        password="Robot123#",
        database="robotdb"
        )
        mycursor = mydb.cursor()
        
        # Add data rows (fill in your own values or logic)
        for i in range(6):
            bulb_num = i + 1
            host =  platform.node(); 

            query ='select COUNT(Bulb_Num) from bulb_replace where Bulb_Num =%s AND Serial = %s'
            mycursor.execute(query, (bulb_num, host))
            result = mycursor.fetchone()[0]
            table.add_widget(Label(text=f"Bulb {bulb_num}"))
            table.add_widget(Label(text=f"{result} "))
            # Get the last replacement date for the bulb
            queryUsage = '''
            SELECT Replacement_date 
            FROM bulb_replace 
            WHERE Serial = %s AND Bulb_Num = %s 
            ORDER BY Replacement_Date DESC 
            LIMIT 1
            '''
            mycursor.execute(queryUsage, (host, bulb_num))
            last_record = mycursor.fetchone()
            last_record_value = last_record[0] if last_record else 0
            print(f"Bulb '{bulb_num} Last number is{last_record_value}")



            if last_record_value == 0:
                # No replacement record found, calculate total usage hours
                queryHours = '''
                SELECT ROUND(SUM(LEAST(TIMESTAMPDIFF(MINUTE, Start_date, End_date), 10)) / 60.0, 2) AS used_hours 
                FROM device_data 
                WHERE Serial = %s  
                '''
                mycursor.execute(queryHours, (host,))
                result = mycursor.fetchone()
                used_hours = result[0] if result and result[0] is not None else 0.0
                print(f"Bulb {bulb_num} used hours{used_hours}")
            else:
                queryHours = '''
                SELECT ROUND(SUM(LEAST(TIMESTAMPDIFF(MINUTE, Start_date, End_date), 10)) / 60.0, 2) AS used_hours 
                FROM device_data 
                WHERE Serial = %s AND Start_date > %s
  
                '''
                mycursor.execute(queryHours, (host,last_record_value))
                result = mycursor.fetchone()
                used_hours = result[0] if result and result[0] is not None else 0.0
                
                # Replacement record exists, calculate hours since last replacement
                ##SELECT End_date 
                #FROM device_data 
                #WHERE Serial = %s 
                #ORDER BY End_date DESC 
                #LIMIT 1
                #'''
                #mycursor.execute(queryHours, (host,))
                #last_end_date = mycursor.fetchone()
                #last_end_date_value = last_end_date[0] if last_end_date else None
                #print(f"Bulb {bulb_num} Last number is{last_end_date_value}")

                #if last_end_date_value:
                    #try:
                        #start_time = datetime.strptime(str(last_record_value), '%Y-%m-%d %H:%M:%S')
                        #end_time = datetime.strptime(str(last_end_date_value), '%Y-%m-%d %H:%M:%S')
                        #time_diff = end_time - start_time
                        #used_hours = round(time_diff.total_seconds() / 3600, 2)
                    #except ValueError as e:
                        #print(f"Date parsing error: {e}")
                        #used_hours = 0.0
                #else:
                    #used_hours = 0.0

            print(f"Used hours: {used_hours:.2f}")

                
            
            table.add_widget(Label(text=f"{used_hours} "))

        mycursor.close()
        mydb.close()
        # Add the table to your tab
        tab5.add_widget(table)
        self.add_widget(tab5)
    
       
       
                
       
        
        
        
          # Initialize sensor with error handling
        #try:
            #self.init_sensor()
            #if not sensor_available:
                #raise RuntimeError("Sensor not available. The app cannot proceed with Sensor functionality.")
        #except DistanceSensorNoEcho as e:
            #print(f"[Error] {e}")
            #self.show_error_popup("Sensor Error", "Sensor not connected. Please connect the sensor and restart the app.")
            #return  # Stop further initialization of the app
       

    #def cleanup(self):
        #"""Close all GPIO resources (sensor, buzzer, etc.)"""
        #global buzzer, sensor
        #if sensor is not None:
            #sensor.close()
            #print("Sensor closed successfully.")
        #if buzzer is not None:
            #buzzer.close()
            #print("Buzzer closed successfully.")

    #def init_sensor(self):
        #global sensor, sensor_available
        #try:
            #sensor = DistanceSensor(echo=echo_pin, trigger=trigger_pin, max_distance=4)
            #sensor_available = True
            #print("Sensor initialized successfully.")
        #except Exception as e:
            #sensor = None
            #sensor_available = False
            #print(f"[Warning] Could not initialize sensor: {e}")


    def show_error_popup(self, title, message):
        popup = Popup(title=title,
                      content=Label(text=message),
                      size_hint=(0.8, 0.4))
        popup.open()

    def voltage_report(self, dt=None):
        try:
            result = subprocess.check_output(['vcgencmd pmic_read_adc'], shell=True, text=True)
            self.v_text_area.text = result
        except subprocess.CalledProcessError as e:
            self.v_text_area.text = f"Error: {e.output}"

    def signal_report(self, dt):
        try:
            # Check real internet connectivity
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            signal_strength = 4  # Connected
        except (socket.error, socket.timeout):
            signal_strength = 0  # Not connected
        except Exception as e:
            print(f"Signal check error: {e}")
            signal_strength = 0
        
        self.signal_icon.source = f"images/signal_{signal_strength}.png"

   
    def sensor_report(self, dt):

    # Check if the sensor is not connected or failed to initialize
        #if not sensor_available or sensor is None:
            #self.sen_text_area.text = "Sensor not connected or failed to initialize."
        
            # Ensure cleanup in case of failed initialization
            #if sensor is not None:
                #sensor.close()
            #return

        try:
            # Read the distance from the sensor
            distance = sensor.distance * 100

            # --- Disconnect detection logic ---
            if self._last_distance is not None:
                if abs(distance - self._last_distance) < 0.1:
                    self._same_distance_count += 1
                else:
                    self._same_distance_count = 0
            self._last_distance = distance

            if distance == 0.0 or distance >= 401.0:
                self.sen_text_area.text = "⚠️ Sensor appears to be disconnected or not responding."
                return

            if self._same_distance_count >= self._max_same_count:
                self.sen_text_area.text = "⚠️ Sensor is likely reporting stale or repeated distance data."
                return


            # --- Otherwise, print actual value ---
            self.sen_text_area.text = f"Distance: {distance:.2f} cm"
            # Map distance to scale (adjust the multiplier and clamp range as needed)
            new_size = max(50, min(300, distance))  # Clamp size between 50 and 300 pixels

            # Apply new size to the image
            self.sensor_image.size = (new_size, new_size)

        except DistanceSensorNoEcho:
            self.sen_text_area.text = "❌ No echo received."

            # Ensure cleanup in case of sensor error
            #if sensor is not None:
                #sensor.close()

        except Exception as e:
            self.sen_text_area.text = f"Sensor read error: {str(e)}"

            # Ensure cleanup in case of a general error
            #if sensor is not None:
                #sensor.close()

        #finally:
            # Cleanup resources to prevent pin locking
            #if sensor is not None:
                #sensor.close()


    def start_beep(self, instance):
        if not hasattr(self, "beep_event"):
            self.beep_event = Clock.schedule_interval(self._beep_callback, 0.4)

    def stop_beep(self, instance):
        if hasattr(self, "beep_event"):
            self.beep_event.cancel()
            del self.beep_event
            buzzer.off()

    def _beep_callback(self, dt):
        buzzer.on()
        sleep(0.2)
        buzzer.off()