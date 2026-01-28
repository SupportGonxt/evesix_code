from kivy.graphics import Rectangle
from kivy.uix.recyclegridlayout import defaultdict
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.uix.dropdown import DropDown
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from gpiozero import MotionSensor
from time import sleep
from rpi5_ws2812.ws2812  import Color, WS2812SpiDriver
import time
import lgpio
from datetime import datetime
from kivy.uix.floatlayout import FloatLayout
from gpiozero import DistanceSensor
import mysql.connector
import platform
import shared
import subprocess
import glob
from gpiozero import Buzzer
from time import sleep
from threading import Thread
from pin_manager import buzzer, sensor
from kivy.uix.widget import Widget
from kivy.uix.image import Image
import sys
import os
from version import VERSION



# Define the command to run the external script
#command = ['python', 'Master.py']

#try:
    # Execute the external script
    #result = subprocess.run(command, capture_output=True, text=True, check=True)
    #process = subprocess.Popen(['python', 'LocalStor.py'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # Print the output from the external script
    #print("Background script started.")
    #print("Output from the called script:")
    #print(result.stdout)
#except subprocess.CalledProcessError as e:
    #print("An error occurred while trying to run the script:", e)

#BUZZER_PIN = 0  # Change this if using a different GPIO pin

# Initialize the Buzzer
#buzzer = Buzzer(BUZZER_PIN)



#distance, threshold,count,c_time = shared.get_values()
#pir = MotionSensor(22)
#trigger_pin = 23
#echo_pin = 24
# Create a DistanceSensor object
#sensor = DistanceSensor(echo=echo_pin, trigger=trigger_pin, max_distance=int(float(shared.get_distance())))


class PageOne(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = FloatLayout() 
        self.laytext = FloatLayout() 
        self.layoutback = FloatLayout() 
        self.layoutHead = FloatLayout()
        self.main_layout = BoxLayout(orientation='vertical', padding=10)
        self.lay = BoxLayout(orientation='vertical', padding=10)
        self.create_main_content()
        self.add_widget(self.main_layout)
        self.add_widget(self.layout)
        self.add_widget(self.layoutback)
        self.add_widget(self.laytext)
        self.add_widget(self.lay)
        self.add_widget(self.layoutHead)
        self.user_inputs = {}

        # Initialize the WS2812 strip with 38 LEDs and SPI channel 0, CE0
        self.strip = WS2812SpiDriver(spi_bus=0, spi_device=0, led_count=67).get_strip()


        self.strip.set_all_pixels(Color(0, 255, 0))
        self.strip.show()
        # Hardcoded absolute path for cloud sync script (robot deployment environment).
        # Adjust if the directory changes on the target device.
        self.CLOUD_SYNC_PATH = '/home/gonxt/evesix_code/cloudSync.py'


    # ---------------- Logging Helpers ----------------
    def log_step(self, step_num, phase, msg):
        """Structured step logging for cycle operations.
        phase: 'WARMUP', 'CYCLE', 'MOTION', 'SUCCESS' etc."""
        print(f"[CycleLog][{phase}][Step {step_num}] {msg}")

    def log_error(self, step_num, phase, msg, exc=None):
        details = f": {exc}" if exc else ""
        print(f"[ERROR][CycleLog][{phase}][Step {step_num}] {msg}{details}")

    def log_info(self, phase, msg):
        print(f"[CycleLog][{phase}] {msg}")

    # ---------------- Save Start Record ----------------
    def save_start_record(self):
        """
        Save the start record to database immediately when cycle begins.
        End_date is NULL - will be updated on restart if machine is switched off.
        """
        print("\n" + "="*60)
        print("[START RECORD] Saving cycle start to database...")
        print("="*60)
        try:
            host_N = platform.node()
            opID = shared.get_operatorId()
            bed_id = shared.get_bedId()
            
            print(f"[START] Machine: {host_N}")
            print(f"[START] Start Time: {time.strftime('%Y-%m-%d %H:%M:%S', self.start_time)}")
            print(f"[START] Operator ID: {opID}")
            print(f"[START] Bed ID: {bed_id}")
            print(f"[START] Side: {self.side_selected}")
            
            mydb = mysql.connector.connect(
                host="localhost",
                user="root",
                password="Robot123#",
                database="robotdb"
            )
            mycursor = mydb.cursor()
            print("[START] Database connected")
            
            # Insert record with NULL End_date
            sql = """
            INSERT INTO device_data (D_Number, Serial, Start_date, End_date, Diagnostic, Code, Operator_Id, Bed_Id, Side)
            VALUES (CONCAT(%s, ' ', %s), %s, %s, NULL, %s, %s, %s, %s, %s)
            """
            values = (host_N, self.start_time, host_N, self.start_time, 'in_progress', 'Emergency Stop Activated', opID, bed_id, self.side_selected)
            mycursor.execute(sql, values)
            mydb.commit()
            
            print(f"[START] ✓ Start record saved")
            print(f"[START] End_date is NULL - will be completed on restart if power loss occurs")
            
            mycursor.close()
            mydb.close()
            print("="*60 + "\n")
            
        except Exception as e:
            print(f"[START] ✗ ERROR saving start record: {e}")
            import traceback
            print(f"[START] Traceback:\n{traceback.format_exc()}")
            print("="*60 + "\n")

    # ---------------- USB Port Refresh ----------------
    def refresh_usb_ports(self):
        """
        Refresh USB input devices to clear touchscreen freezing issues.
        This is called at the end of a successful cycle.
        Focuses on refreshing input devices (touchscreen/HID) rather than all USB ports.
        """
        self.log_info('SUCCESS', 'Refreshing USB input devices...')
        
        try:
            # Method 1: Rebind USB input devices directly via /sys/bus/usb/drivers
            # This is more targeted and less disruptive than full port cycling
            result = subprocess.run(
                ['bash', '-c', 'for device in /sys/bus/usb/drivers/usb/*/authorized; do echo 0 > "$device" 2>/dev/null; sleep 0.1; echo 1 > "$device" 2>/dev/null; done'],
                timeout=5,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                self.log_info('SUCCESS', 'USB input devices reset via sysfs')
                time.sleep(0.5)
                return True
        except Exception as e:
            self.log_error(0, 'SUCCESS', f'sysfs reset failed: {e}')
        
        try:
            # Method 2: Reload USB HID driver (specifically for touchscreen/input devices)
            self.log_info('SUCCESS', 'Reloading USB HID driver for input devices...')
            result = subprocess.run(
                ['sudo', 'modprobe', '-r', 'usbhid'],
                timeout=5,
                capture_output=True,
                text=True
            )
            time.sleep(0.5)
            result = subprocess.run(
                ['sudo', 'modprobe', 'usbhid'],
                timeout=5,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                self.log_info('SUCCESS', 'USB HID driver reloaded - input devices refreshed')
                time.sleep(0.5)
                return True
        except Exception as e:
            self.log_error(0, 'SUCCESS', f'USB HID reload failed: {e}')
        
        try:
            # Method 3: Restart input event devices
            result = subprocess.run(
                ['sudo', 'systemctl', 'restart', 'input.target'],
                timeout=5,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                self.log_info('SUCCESS', 'Input devices restarted via systemd')
                time.sleep(0.5)
                return True
        except Exception as e:
            self.log_error(0, 'SUCCESS', f'systemd input restart failed: {e}')
        
        # If we get here, methods failed but log it
        self.log_error(0, 'SUCCESS', 'USB input device refresh failed - touchscreen may need manual intervention')
        return False

    # ---------------- Cloud Sync Trigger ----------------
    def trigger_cloud_sync(self, phase='SUCCESS', start_step=11):
        """Run cloudSync.py in a blocking subprocess (inside a background thread) with
        an internet connectivity pre-check and post-check.
        phase: logging phase label ('SUCCESS' or 'MOTION').
        start_step: base step number for logging so each branch can have contiguous steps.
        Steps used:
          start_step     -> network pre-check
          start_step + 1 -> launching cloudSync
          start_step + 2 -> completion status
        """

        def _quick_net_check(host='8.8.8.8', port=53, timeout=2):
            import socket
            try:
                sock = socket.create_connection((host, port), timeout=timeout)
                sock.close()
                return True
            except OSError:
                return False

        start = time.time()
        # Resolve absolute path to cloudSync.py in case working directory differs under systemd/cron.
        script_path = self.CLOUD_SYNC_PATH
        if not os.path.isfile(script_path):
            self.log_error(start_step, phase, f'Hardcoded cloudSync.py missing at {script_path}')
            return
        self.log_step(start_step, phase, f'Using hardcoded cloudSync path: {script_path}')
        online = _quick_net_check()
        # Adjust subsequent steps because we used start_step for path resolution logging
        net_step = start_step + 0.1  # fractional to keep ordering visible
        if online:
            self.log_step(f'{net_step}', phase, 'Internet check: ONLINE (proceeding with sync)')
        else:
            self.log_step(f'{net_step}', phase, 'Internet check: OFFLINE (cloudSync will internally wait)')
        try:
            self.log_step(start_step + 1, phase, f'Launching cloudSync.py for data upload (path={script_path})')
            result = subprocess.run([sys.executable, script_path], capture_output=True, text=True)
            duration = round(time.time() - start, 2)
            # Post-run connectivity insight (may have come online during script)
            online_after = _quick_net_check()
            net_status_after = 'ONLINE' if online_after else 'OFFLINE'
            if result.returncode == 0:
                self.log_step(start_step + 2, phase, f'cloudSync.py completed in {duration}s (post-run net: {net_status_after})')
                if result.stdout:
                    print('[cloudSync stdout]\n' + result.stdout)
                if result.stderr:
                    print('[cloudSync stderr]\n' + result.stderr)
            else:
                self.log_error(start_step + 2, phase, f'cloudSync.py exited with code {result.returncode} (post-run net: {net_status_after})', result.stderr)
            
            # After cloud sync completes, refresh USB ports to prevent touchscreen freezing
            if phase == 'SUCCESS':
                self.log_step(start_step + 3, phase, 'Refreshing USB ports after cloud sync')
                self.refresh_usb_ports()
        except Exception as e:
            self.log_error(start_step + 2, phase, 'cloudSync invocation failed', e)


    # def add_back_button(self, callback):
        # """Add a back button to the top left of the layout."""
        # back_button = Button(
            # text="< Back",
            # size_hint=(None, None),
            # background_color=(0, 153/255, 1, 1),
            # size=(150, 100),
            # pos_hint={'x': 0, 'top': 1}
        # )
        # back_button.bind(on_release=callback)
        #self.main_layout.add_widget(back_button)

    def create_main_content(self):
        self.main_layout.clear_widgets()

        # Create "BEGIN ROBOT" label as a button to make it clickable
        begin_label = Button(
            text="BEGIN ROBOT",
            font_size=40,
            color=(0, 153/255, 1, 1),
            background_normal='',
            background_color=(0.1, 0.1, 0.1, 0.1),  # Transparent background
            bold=True,
            size_hint=(1, 0.3)
        )
        begin_label.bind(on_release=self.show_hospital_selection)
        self.main_layout.add_widget(begin_label)
        
        # Add version label at the bottom
        version_label = Label(
            text=f"Version: {VERSION}",
            font_size=20,
            color=(0, 153/255, 1, 1),
            size_hint=(1, 0.1),
            halign='center'
        )
        self.main_layout.add_widget(version_label)

    #def submitVali(self, instance):
        #if self.hospital_button.text == 'Select a ward number':  
        #    self.textValid.text = 'please select a ward'
           # if self.bed_button.text == 'Select a bed number':
        #    self.textValid.text = 'please select a ward'
         #   print('please select a ward')
        #else:
            


    def show_bed(self, instance,value):
        dropdown1 = DropDown()
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='Robot123#',
            database='robotdb'
        )
        
        cursor = connection.cursor()
            # Define a query to fetch data
        query = 'SELECT Ward_Id FROM ward WHERE Ward_Name = %s AND Hospital_Id = %s'
        print("hospital Id is")
        print(shared.get_hospitalId())
        param = (value,shared.get_hospitalId(),) # Use a tuple for the parameter
        cursor.execute(query, param)
        result = cursor.fetchone()
        wardId = result[0]
        shared.set_wardId(wardId)
        print(wardId)
            
        
        query2 = 'SELECT Distinct Space FROM bed WHERE Ward_Id = %s'
        param = (wardId,) # Use a tuple for the parameter
            
        cursor.execute(query2, param)
            # Fetch all rows from the executed query
        beds = cursor.fetchall()
            
            # Loop through the rows and add each one to the dropdown
        for bed in beds:
            btn = Button(text=bed[0], size_hint_y=None, height=70)
            btn.bind(on_release=lambda btn: dropdown1.select(btn.text))
            dropdown1.add_widget(btn)

        
        connection.close()
        
        # Remove old bed_button if it exists to prevent duplicate widgets
        if hasattr(self, 'bed_button') and self.bed_button in self.layout.children:
            self.layout.remove_widget(self.bed_button)
        
        self.bed_button = Button(
            text='Select a bed',
            size_hint=(0.70, 0.15),
            background_color=(0, 153 / 255, 1, 1),
            # height=77,
            pos_hint={"x": 0.15, "y": 0.3}
        )
        self.bed_button.bind(on_release=dropdown1.open)
        
        # Single binding for dropdown selection
        def on_select(instance, value):
            self.bed_button.text = value 
            self.handle_bed_selection(instance) 
        dropdown1.bind(on_select=on_select)
        
        self.layout.add_widget(self.bed_button)
        
    def handle_bed_selection(self, instance):
        # Clear previous content
        self.main_layout.clear_widgets()
        self.layout.clear_widgets()

        # Main vertical layout
        main_layout = BoxLayout(orientation='vertical', spacing=10, size_hint=(1, 0.9))

        # Header
        header = Label(text="Select Side of Bed", size_hint=(1, 0.2), font_size=20)
        main_layout.add_widget(header)

        # FloatLayout to layer image and buttons
        float_layout = FloatLayout(size_hint=(1, 0.6))

        # Background image
        bed_image = Image(source='images/hosBed4.webp', allow_stretch=True, keep_ratio=False,
                      size_hint=(1, 1), pos_hint={'x': 0, 'y': 0})
        float_layout.add_widget(bed_image)

        # GridLayout for buttons (overlayed on top of image)
        button_grid = GridLayout(cols=3, rows=3, spacing=10, size_hint=(1, 1), pos_hint={'x': 0, 'y': 0})

        # Create buttons and spacers
        buttons = [
            Button(text="Top Left", background_color=(0, 153 / 255, 1, 1)),
            Widget(),
            Button(text="Top Right", background_color=(0, 153 / 255, 1, 1)),
            Widget(),
            Button(text="Center", background_color=(0, 153 / 255, 1, 1)),
            Widget(),
            Button(text="Bottom Left", background_color=(0, 153 / 255, 1, 1)),
            Widget(),
            Button(text="Bottom Right", background_color=(0, 153 / 255, 1, 1)),
        ]

        # Bind actions
        labels = ["Top Left", None, "Top Right", None, "Center", None, "Bottom Left", None, "Bottom Right"]
        for btn, label in zip(buttons, labels):
            if label:
                btn.size_hint = (1, None)
                btn.height = 50
                btn.bind(on_press=lambda instance, val=label: self.submit_selection(instance, val))
            button_grid.add_widget(btn)

        float_layout.add_widget(button_grid)
        main_layout.add_widget(float_layout)

        # Back button layout
        back_layout = BoxLayout(orientation='horizontal', size_hint=(1, 0.2), padding=[10, 10])
        back_button = Button(text="Back", size_hint=(0.3, 1), pos_hint={'x': 0})
        back_button.bind(on_release=self.show_hospital_selection)
        back_layout.add_widget(back_button)
        main_layout.add_widget(back_layout)

        # Display updated layout
        self.layout.add_widget(main_layout)

    def show_submit(self, popup):
        popup.dismiss()  # Close the popup
       

        # Create a horizontal layout for buttons
        button_bar = BoxLayout(orientation='horizontal', spacing=10, size_hint=(1, None), height=70)

         # Back button
        self.back_btn = Button(
            text="Back",
            size_hint=(0.5, 1),
            background_normal='',
            background_color=(0, 153/255, 1, 1)
        )
        self.back_btn.bind(on_press=self.show_hospital_selection)  
        button_bar.add_widget(self.back_btn)
        
        # Submit button
        self.submit_btn = Button(
            text="Submit",
            size_hint=(0.5, 1),
            background_normal='',
            background_color=(0, 153/255, 1, 1)
        )
        self.submit_btn.bind(on_press=lambda instance: self.submit_selection(instance, 'None'))
        button_bar.add_widget(self.submit_btn)

       

        # Add button layout to main layout
        self.layout.add_widget(button_bar)

    def side_selection(self, popup):
        popup.dismiss()  # Close the popup
        
        self.main_layout.clear_widgets()
        self.layout.clear_widgets()
        #self.laytext.clear_widgets()
        #self.layoutHead.clear_widgets()
        main_layout = BoxLayout(orientation='vertical', spacing=10, size_hint=(1, 1))
        # Add blue background using canvas
        
        header = Label(text="Select Side of Bed", size_hint=(1, 0.2), font_size=20)
        main_layout.add_widget(header)

        button_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint=(1, 0.5))

        self.left_button = Button(text="Left Hand Side of Bed", size_hint=(0.5, 1),background_color=(0, 153 / 255, 1, 1))
        self.left_button.bind(on_press=lambda instance: self.submit_selection(instance, 'Left'))
        button_layout.add_widget(self.left_button)
        

        self.right_button = Button(text="Right Hand Side of Bed", size_hint=(0.5, 1),background_color=(0, 153 / 255, 1, 1))
        self.right_button.bind(on_press=lambda instance: self.submit_selection(instance, 'Right'))
        button_layout.add_widget(self.right_button)
        

        main_layout.add_widget(button_layout)
        # Add back button layout at the bottom
        back_layout = BoxLayout(orientation='horizontal', size_hint=(1, 0.2), padding=[10, 10])
        back_button = Button(text="Back", size_hint=(0.3, 1), pos_hint={'x': 0})
        back_button.bind(on_release=self.show_hospital_selection) 
        back_layout.add_widget(back_button)
        main_layout.add_widget(back_layout)


        # Now you can use main_layout as your widget, for example: 
        
        self.layout.add_widget(main_layout)
    
    def call_back(self, instance):
        # Stop the initial countdown timer if it's running
        if hasattr(self, 'timer_event') and self.timer_event is not None:
            self.timer_event.cancel()
            self.timer_event = None
            print("Initial countdown timer stopped")
        
        # Set LEDs to green when going back
        try:
            self.strip.set_all_pixels(Color(0, 255, 0))
            self.strip.show()
            print("LEDs turned green when going back")
        except Exception as e:
            print(f"Error changing LEDs: {e}")
        
        #self.sensor.close()
        self.show_hospital_selection(instance)

    def show_hospital_selection(self, instance):
        self.beep_thread = None
        self.beeping = False
        #self.sensor = DistanceSensor(echo=echo_pin, trigger=trigger_pin, max_distance=int(float(shared.get_distance())))

        self.main_layout.clear_widgets()
        self.layoutback.clear_widgets()
        self.layout.clear_widgets()
        self.layoutHead.clear_widgets()  # Clear header layout to remove old labels
        self.laytext.clear_widgets()      # Clear text layout to remove old validation labels

        self.textValid = Label(
            text=' ',
            font_size=18,
            underline=False,
            bold=False,
            color=(1, 0, 0, 1),
            halign='center',
            pos_hint={"x": 0.0, "y": -0.25}
        )
        self.laytext.add_widget(self.textValid)


        # Add back button
        # self.add_back_button(self.create_main_content)

        # Create a BoxLayout for the dropdown to center align it
        center_layout = BoxLayout(orientation='vertical', size_hint=(None, None), size=(400, 300), spacing=20, pos_hint={'center_x': 0.5, 'center_y': 0.5})


        host_Name = platform.node()
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='Robot123#',
            database='robotdb'
        )
        
        cursor = connection.cursor()
            # Define a query to fetch data
        query1 = 'SELECT Hospital_Id FROM robot WHERE Serial = %s'
        param = (host_Name,) # Use a tuple for the parameter
        cursor.execute(query1, param)
        resultHosId = cursor.fetchone()
        print(resultHosId[0])
        hosId = resultHosId[0]
        shared.set_hospitalId(hosId)
        
        query2 = 'SELECT Hospital_Name, Hospital_Group_Id FROM hospital WHERE Hospital_Id = %s'
        param = (hosId,) # Use a tuple for the parameter
        cursor.execute(query2, param)
        resultHosName = cursor.fetchall()
        for row in resultHosName: 
            print(row[0], row[1])
            hosName = row[0]
            groupId = row[1]
        
        query3 = 'SELECT Group_Name FROM hospital_group WHERE Hospital_Group_Id = %s'
        param = (groupId,) # Use a tuple for the parameter
        cursor.execute(query3, param)
        resultHosGroup = cursor.fetchone()
        print(resultHosGroup[0])
        groupName = resultHosGroup[0]
        cursor.close()
        connection.close()
        
        # Add instruction label
        self.instruction_label = Label(
            text= groupName,
            font_size=35,
            underline = True,
            bold=True,
            color=(0, 153/255, 1, 1),
            halign='center',
            pos_hint = {"x":0.0,"y":0.4}
        )

        self.instruction_label1 = Label(
            text= hosName,
            font_size=30,
            underline=True,
            bold=True,
            color=(0, 153 / 255, 1, 1),
            halign='center',
            pos_hint={"x": 0.0, "y": 0.30}
        )
        self.layoutHead.add_widget(self.instruction_label)
        self.layoutHead.add_widget(self.instruction_label1)

        # Create dropdown for hospital selection
        dropdown = DropDown()
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='Robot123#',
            database='robotdb'
        )
        
        cursor = connection.cursor()
            # Define a query to fetch data
        query = 'SELECT Distinct Ward_Name FROM ward WHERE Hospital_Id = %s'
        param = (hosId,) # Use a tuple for the parameter
            
        cursor.execute(query, param)
            
            # Fetch all rows from the executed query
        wards = cursor.fetchall()
        cursor.close()
        connection.close()
            
            # Loop through the rows and add each one to the dropdown
        for ward in wards:
            btn = Button(text=ward[0], size_hint_y=None, height=70)
            btn.bind(on_release=lambda btn: dropdown.select(btn.text))
            dropdown.add_widget(btn)

        # Remove old hospital_button if it exists to prevent duplicate widgets
        if hasattr(self, 'hospital_button'):
            # Unbind all previous events
            self.hospital_button.unbind(on_release=self.hospital_button.dispatch)
            if self.hospital_button in self.layout.children:
                self.layout.remove_widget(self.hospital_button)
        
        # Store dropdown as instance variable to prevent garbage collection
        self.ward_dropdown = dropdown
        
        self.hospital_button = Button(
            text='Select a ward',
            size_hint=(0.70, 0.15),
            background_color=(0, 153/255, 1, 1),
            #height=77,
            pos_hint = {"x":0.15,"y":0.5}
        )
        self.hospital_button.bind(on_release=self.ward_dropdown.open)
        
        # Single binding for dropdown selection
        def on_select(instance, value):
            self.hospital_button.text = value 
            self.handle_selection(instance, value) 
        self.ward_dropdown.bind(on_select=on_select)

        self.layout.add_widget(self.hospital_button)
        
    def handle_selection(self, instance, value): 
        # Your method that gets called with the selected value 
        print(f'Selected value: {value}') 
        # Additional logic based on the selected value
        self.show_bed(instance, value) 

        # Add Submit button

    def select_hospital(self, text, dropdown):
        self.hospital_button.text = text
        dropdown.dismiss()

    def select_bed(self, text, dropdown1):
        self.bed_button.text = text
        self.labelBed.text = text
        dropdown1.dismiss()


    def submit_bed_selection(self, instance):
        selected_bed = self.bed_button.text
        if selected_bed.startswith('Select a bed number'):
            print("Please select a bed.")
        else:
            self.user_inputs['bed'] = selected_bed
            
            temp =selected_bed
            
            mydb = mysql.connector.connect(
            host="localhost",
            user="root",
            password="Robot123#",
            database="robotdb"
            )
            mycursor = mydb.cursor()
            query = 'SELECT Bed_Id FROM bed WHERE Space = %s AND Ward_Id = %s'
            param = (temp,shared.get_wardId(),) # Use a tuple for the parameter
            mycursor.execute(query, param)
            result = mycursor.fetchone()
            shared.set_bedId(result[0])
            
            mydb.close()
            
      

    def submit_selection(self, instance,side):  
        self.side_selected = side
        if self.hospital_button.text == 'select a ward number' and self.hospital_button.text == 'select a bed number':
            print('please select the ward or bed')
        else:
            self.show_ward_selection(instance)
            self.submit_bed_selection(instance)
        

    def show_ward_selection(self, instance, *args):
        self.layout.clear_widgets()
        self.laytext.clear_widgets()
        self.layoutHead.clear_widgets()
        # Add back button
        #self.add_back_button(self.show_hospital_selection)
        
        # Create a BoxLayout for the dropdown to center align it
        #center_layout = BoxLayout(orientation='vertical', size_hint=(None, None), size=(400, 300), spacing=20, pos_hint={'center_x': 0.5, 'center_y': 0.5})
        self.instruction_labelGroup = Label(
            text="SUMMARY OF INPUTS",
            font_size=30,
            bold=True,
            markup=False,
                italic=False,
            color=(0, 153 / 255, 1, 1),
            halign='center',
            pos_hint={"x": 0.0, "y": 0.4}
        )
        self.instruction_labelHos = Label(
            text=self.instruction_label.text,
            font_size=30,
            bold=False,
            markup=False,
            italic=False,
            color=(0, 153 / 255, 1, 1),
            halign='center'

        )
        # Add instruction label
        self.instruction_label2 = Label(
            text=self.instruction_label1.text,
            font_size=30,
            bold=False,
            markup=False,
            italic = False,
            color=(0, 153 / 255, 1, 1),
            halign='center'

        )
        self.back = Button(text = '<<back',
                           size_hint = (0.49,0.2),
                           color=(0, 153 / 255, 1, 1),
                           pos_hint = {"x":0.0,"y":0.0})
        self.layoutback.add_widget(self.back)
        self.back.bind(on_press = self.call_back)
        self.main_layout.add_widget(self.instruction_labelHos)
        #self.layout.add_widget(self.instruction_labelGroup)
        self.main_layout.add_widget(self.instruction_label2)

        # display inputs
        labelBed = Label(
            text = "bed",
            font_size=30,
            bold=False,
            markup=False,
            italic = False,
            color=(0, 153 / 255, 1, 1),
            halign='center'

        )

        labelWard = Label(
            text="ward",
            font_size=30,
            bold=False,
            markup = False,
            italic=False,
            color=(0, 153 / 255, 1, 1),
            halign='center'
        )
        
        labelSpace = Label(
            text="      ",
            font_size=30,
            bold=False,
            markup = False,
            italic=False,
            color=(0, 153 / 255, 1, 1),
            halign='center'
        )


        labelWard.text = f"Ward: {self.hospital_button.text}"
        labelBed.text = f"Bed: { self.bed_button.text}"
        self.main_layout.add_widget(labelWard)
        self.main_layout.add_widget(labelBed)
        self.main_layout.add_widget(labelSpace)

       # Add Submit button
        submit_button = Button(
            text="Start Robot",
            height=70,
            halign = 'center',
            color=(0, 153 / 255, 1, 1),
            size_hint = (0.49,0.2),
            pos_hint = {"x":0.5,"y":0.0},
            on_release=self.start_robot
        )


        if labelWard.text == 'Select a ward number':
          submit_button.bind(on_release = self.show_hospital_selection)
        else:
            self.layout.add_widget(submit_button)





        #self.layout.add_widget(center_layout)





    def show_bed_selection(self):
        self.main_layout.clear_widgets()

        # Add back button
        self.add_back_button(self.show_ward_selection)

        # Create a BoxLayout for the dropdown to center align it
        center_layout = BoxLayout(orientation='vertical', size_hint=(None, None), size=(400, 300), spacing=20, pos_hint={'center_x': 0.5, 'center_y': 0.5})



        self.main_layout.add_widget(center_layout)

    def select_bed(self, text, dropdown):
        self.bed_button.text = text
        dropdown.dismiss()


    def show_summary(self):
        self.main_layout.clear_widgets()

        # Add back button
        #self.add_back_button(self.show_bed_selection)

        # Display summary of user inputs
        summary_label = Label(
            text="Summary of Inputs:",
            font_size=50,
            color=(0, 153/255, 1, 1),
            bold=True,
            halign='center'
        )
        self.main_layout.add_widget(summary_label)

        for key, value in self.user_inputs.items():
            input_label = Label(
                text=f"{key}: {value}",
                font_size=40,
                color=(0, 153/255, 1, 1),
                halign='center'
            )
            self.main_layout.add_widget(input_label)

        # Add Start Robot button
        start_robot_button = Button(
            text="Start Robot",
            font_size=40,
            size_hint=(1, None),
            background_color=(0, 153/255, 1, 1),
            height=60,
            on_release=self.start_robot
        )
        self.main_layout.add_widget(start_robot_button)
        
        
        
    def start_robot(self, instance):
        print(f"handle_selection {shared.get_values()}")
        distance,threshold,count,c_time = shared.get_values()
        self.layout.clear_widgets()
        # Print the inputs (if needed)
        print("Robot started with the following inputs:")
        print(self.instruction_labelHos.text)
        print(self.instruction_label2.text)
        print (f"Ward: {self.hospital_button.text}")
        print (f"Bed: {self.bed_button.text}")

        # Start the initial countdown
        self.start_initial_countdown()
        
    def start_initial_countdown(self):
        self.main_layout.clear_widgets()
        
        self.stop_button = Button(
            text="Stop Robot",
            height=70,
            halign = 'center',
            color=(0, 153 / 255, 1, 1),
            size_hint = (0.49,0.2),
            pos_hint = {"x":0.5,"y":0.0},
            on_release=self.stop_countdown
        )
        
        self.resume_button = Button(
            text="Resume Robot",
            height=70,
            halign = 'center',
            color=(0, 153 / 255, 1, 1),
            size_hint = (0.49,0.2),
            pos_hint = {"x":0.5,"y":0.0},
            on_release=self.start_robot
        )
        
        self.countdown_label = Label(
            text=f"You have \n {int(float(shared.get_count()))} seconds \n to leave the room",
            font_size=65,
            color=(0, 153/255, 1, 1),
            bold=True
        )
        self.main_layout.add_widget(self.countdown_label)
        self.layout.add_widget(self.stop_button)
        self.resume_button.disable = True
        self.countdown_time = int(float(shared.get_count())) #leave the room count down
        self.timer_event = None
        self.timer_event = Clock.schedule_interval(self.update_initial_countdown, 1)

        # Set all LEDs to orange
        self.strip.set_all_pixels(Color(255, 165, 0))
        self.strip.show()
        print("ORANGE LED is activated")
        
    def stop_countdown(self, instance):
        #self.submit_button.disabled = True
        print("\n" + "="*60)
        print("[STOP COUNTDOWN] Button pressed")
        print("="*60)
        
        if self.timer_event  is not None:
            print("[STOP] Timer event exists, proceeding with stop")
            
            # Check if start_time exists
            if hasattr(self, 'start_time'):
                print(f"[STOP] start_time found: {self.start_time}")
                try:
                    host_N = platform.node()
                    opID = shared.get_operatorId()
                    reason = "emergency shutoff"
                    
                    print(f"[STOP] Machine: {host_N}")
                    print(f"[STOP] Operator ID: {opID}")
                    print(f"[STOP] Bed ID: {shared.get_bedId()}")
                    
                    # Check if side_selected exists
                    if hasattr(self, 'side_selected'):
                        print(f"[STOP] Side: {self.side_selected}")
                    else:
                        print("[STOP] WARNING: side_selected not found, using None")
                        self.side_selected = None
                    
                    self.log_step('STOP', 'EMERGENCY', 'Recording emergency shutoff to database (no end_time yet)')
                    
                    # Turn off relay before saving to DB
                    if hasattr(self, 'h'):
                        lgpio.gpio_write(self.h, 20, True)
                        lgpio.gpiochip_close(self.h)
                        print("[STOP] Relay 20 deactivated due to emergency shutoff")
                    
                    # Save to database without end_time (will be updated when machine restarts)
                    print("[STOP] Connecting to database...")
                    mydb = mysql.connector.connect(
                        host="localhost",
                        user="root",
                        password="Robot123#",
                        database="robotdb"
                    )
                    mycursor = mydb.cursor()
                    print("[STOP] Database connected")
                    
                    sql = """
                    INSERT INTO device_data (D_Number, Serial, Start_date, End_date, Diagnostic, Code, Operator_Id, Bed_Id, Side)
                    VALUES (CONCAT(%s, ' ', %s), %s, %s, NULL, %s, %s, %s, %s, %s)
                    """
                    values = (host_N, self.start_time, host_N, self.start_time, 'stopped', reason, opID, shared.get_bedId(), self.side_selected)
                    print(f"[STOP] Executing SQL with values: {values}")
                    mycursor.execute(sql, values)
                    mydb.commit()
                    print(f"[STOP] Record inserted, rows affected: {mycursor.rowcount}")
                    
                    mycursor.close()
                    mydb.close()
                    print("[STOP] ✓ Emergency shutoff recorded to database (end_time will be set on restart)")
                    self.log_step('STOP', 'EMERGENCY', 'Database record saved - end_time pending restart')
                    
                except Exception as e:
                    print(f"[STOP] ✗ ERROR recording emergency shutoff: {e}")
                    import traceback
                    print(f"[STOP] Traceback:\n{traceback.format_exc()}")
                    self.log_error('STOP', 'EMERGENCY', 'Failed to record emergency shutoff', e)
            else:
                print("[STOP] WARNING: start_time NOT FOUND - cannot record to database")
                print("[STOP] This usually means stop was pressed during initial countdown before main cycle started")
            
            self.layout.clear_widgets()
            self.layout.add_widget(self.resume_button)            
            self.timer_event.cancel()
            self.timer_event  = None
            self.strip.set_all_pixels(Color(0, 255, 0))
            self.strip.show()
            print("[STOP] Timer stopped, LEDs set to green")
        else:
            print("[STOP] WARNING: timer_event is None")
            self.countdown_time = self.timer_event
        
        print("="*60 + "\n") 
    
    
    def long_beep(self,duration):
        buzzer.on()
        sleep(duration)    
    
    def beep(self,duration):
        buzzer.on()
        sleep(duration)
        buzzer.off()
        sleep(duration)
        
    def start_long_beeping(self):
        """Start the beeping process in a background thread."""
        if not self.beeping:
            self.beeping = True
            self.beep_thread = Thread(target=self.beep_long_loop)
            self.beep_thread.daemon = True  # Ensure the thread stops when the app closes
            self.beep_thread.start()
            
    def start_beeping(self):
        """Start the beeping process in a background thread."""
        if not self.beeping:
            self.beeping = True
            self.beep_thread = Thread(target=self.beep_loop)
            self.beep_thread.daemon = True  # Ensure the thread stops when the app closes
            self.beep_thread.start()

    def stop_beeping(self):
        """Stop the beeping process."""
        self.beeping = False  # Signal the thread to stop
        #buzzer.close()
        print("Stopping beep...")

    def stop_long_beeping(self):
        """Stop the long beeping process."""
        self.beeping = False  # Signal the thread to stop
        buzzer.off()
        #buzzer.close()
        print("Stopping beep...")
    
    def beep_long_loop(self):
        """Background thread for beeping."""
        while self.beeping:
            self.long_beep(0.2)
            sleep(0.2)
            
    def beep_loop(self):
        """Background thread for beeping."""
        while self.beeping:
            self.beep(0.2)
            sleep(0.2)
            self.beep(0.2)
            sleep(1)  # Pause before repeating
    
        
    def update_initial_countdown(self, dt):
        if self.countdown_time > 0:
            self.countdown_label.text = f"You have \n {self.countdown_time} seconds \n to leave the room"
            self.countdown_time -= 1
        else:
            Clock.unschedule(self.update_initial_countdown)
            # No longer tracking previous_distance - using fixed 10cm threshold
            self.start_ten_minute_countdown()
            # Turn off all LEDs     turn red
            self.strip.set_all_pixels(Color(255, 0, 0))
            self.strip.show()          
            print("RED LED is activated")
            
    def cleanup_cycle(self):
        """Clean up resources after cycle completion or interruption"""
        try:
            # Turn off relay
            if hasattr(self, 'h'):
                lgpio.gpio_write(self, 20, True)
                lgpio.gpiochip_close(self.h)
                print("Relay 20 deactivated in cleanup")
        except Exception as e:
            print(f"Error during cleanup: {e}")
    
    def start_ten_minute_countdown(self):
        self.main_layout.clear_widgets()
        self.layoutback.clear_widgets()
        self.layout.clear_widgets()
        self.countdown_label = Label(
            text=f"{int(float(shared.get_time()))}:00",
            font_size=200,
            color=(0, 153/255, 1, 1),
            bold=True
        )
        print("timer")
        self.main_layout.add_widget(self.countdown_label)
        self.countdown_time = int(float(shared.get_time())) *60  # 10 minutes in seconds
        # Warm-up window: ignore motion checks for the first 15 seconds (was 30, previously 60)
        self.motion_detection_enabled_at = time.time() + 15
        Clock.schedule_interval(self.update_ten_minute_countdown, 1)
        # Set all LEDs to red
        self.log_step(1, 'WARMUP', 'Initializing cycle countdown and setting RED LEDs')
        self.strip.set_all_pixels(Color(255, 0, 0))
        self.strip.show()
        print("RED LED is activated after interval")
        self.start_time = time.localtime()
        print(self.start_time)
        
        # Save start record to database immediately (in case of power loss)
        self.save_start_record()
        
        # Fixed motion detection threshold - 10cm
        self.MOTION_THRESHOLD_CM = 10.0
        self.log_step(1, 'INIT', f'Motion detection threshold set to fixed {self.MOTION_THRESHOLD_CM}cm')
        print(f"Motion detection threshold: {self.MOTION_THRESHOLD_CM}cm")
        # Initialize the relay
        self.h = lgpio.gpiochip_open(0)
        lgpio.gpio_claim_output(self.h, 20)
        lgpio.gpio_write(self.h, 20, False)  # Turn relay on when countdown starts
        print("Relay 20 is activated")
        #initialize Sensor
        

    # (Removed stray early GREEN LED block; LEDs stay RED during warm-up.)

    
        
        
        
    def update_ten_minute_countdown(self, dt):
        
        # Change this if using a different GPIO pin
        PIR_PIN = 22
        print("RCWL-0516 Sensor Active")
        host_N = platform.node()
        print(host_N)
        # Fixed 10cm motion detection threshold
        # No longer using variable distance or baseline tracking
        

# Initialize detect variable        
        if self.countdown_time > 0:
                # During warm-up, skip motion detection but continue countdown
                if hasattr(self, 'motion_detection_enabled_at') and time.time() < self.motion_detection_enabled_at:
                    try:
                        remaining_warmup = int(self.motion_detection_enabled_at - time.time())
                        self.log_step(2, 'WARMUP', f'Sensor warmup period - motion detection disabled ({remaining_warmup}s remaining)')
                        distance_reading = sensor.distance
                        if distance_reading is None:
                            current_distance = 0.0
                        else:
                            current_distance = distance_reading * 100
                        self.log_step(2, 'WARMUP', f'Current distance reading: {current_distance:.2f}cm (monitoring only - NOT checking for motion yet)')
                    except Exception as e:
                        self.log_error(2, 'WARMUP', 'Sensor read failed during warmup', e)
                        print(f"Sensor read error during warmup: {e}")
                    minutes, seconds = divmod(self.countdown_time, 60)
                    self.countdown_label.text = f"{minutes:02}:{seconds:02}"
                    self.countdown_time -= 1
                    return
                
                try:
                    self.log_step(3, 'CYCLE', 'Reading sensor distance for motion detection')
                    distance_reading = sensor.distance
                    
                    # Handle None or very close readings (sensor returns None when object is too close)
                    if distance_reading is None or distance_reading < 0.02:  # Less than 2cm or None
                        current_distance = 0.0  # Treat as 0cm - definitely motion detected
                        self.log_step(3, 'CYCLE', 'Object extremely close or sensor blocked - treating as 0cm')
                    else:
                        current_distance = distance_reading * 100
                    
                    self.log_step(3, 'CYCLE', f'Current distance: {current_distance:.2f}cm | Threshold: {self.MOTION_THRESHOLD_CM}cm')
                except Exception as e:
                    self.log_error(3, 'CYCLE', 'Sensor read failed - skipping this cycle', e)
                    print(f"Sensor read error: {e}")
                    # Skip this cycle and continue countdown
                    minutes, seconds = divmod(self.countdown_time, 60)
                    self.countdown_label.text = f"{minutes:02}:{seconds:02}"
                    self.countdown_time -= 1
                    return
                print("current distance")
                print(current_distance)
                print(self.countdown_time)
                print("Motion Threshold (Fixed)")
                print(self.MOTION_THRESHOLD_CM)
                # Check if any motion detected below 10cm threshold
                if current_distance < self.MOTION_THRESHOLD_CM:
                    print("in motion loop")
                    self.log_step(4, 'MOTION', f'MOTION DETECTED! Distance {current_distance:.2f}cm is below {self.MOTION_THRESHOLD_CM}cm threshold')
                    
                    # Motion detected - no baseline tracking needed with fixed threshold
                    minutes, seconds = divmod(self.countdown_time, 60)
                    self.log_step(4, 'MOTION', f'Countdown was at {minutes:02}:{seconds:02} when motion detected')
                    self.countdown_label.text = "Error: Motion Detected"
                    self.countdown_label.font_size = '35pt'
                    end_time = time.localtime()
                    reason = f"Error: Motion Detected at {current_distance:.2f}cm (threshold: {self.MOTION_THRESHOLD_CM}cm)"
                    self.log_step(4, 'MOTION', f'Reason logged: {reason}')
                    
                    print(reason)  
                    print (end_time)
                    # Turn relay off
                    print(self.countdown_time)
                    print("Motion Relay 20 is deactivated")
                    lgpio.gpio_write(self.h, 20, True)
                    lgpio.gpiochip_close(self.h)
                    Clock.unschedule(self.update_ten_minute_countdown)
                    #motion_sensor.close()
                    # Set all LEDs to blue after motion detection
                    self.log_step(5, 'MOTION', 'Setting LEDs to BLUE for motion error state')
                    self.strip.set_all_pixels(Color(0, 0, 255))
                    self.strip.show()
                    print("LEDs turned BLUE after motion detection")
                    self.log_step(6, 'MOTION', 'Opening DB connection for failure record write')
                    mydb = mysql.connector.connect(
                    host="localhost",
                    user="root",
                    password="Robot123#",
                    database="robotdb"
                    )
                    mycursor = mydb.cursor()
                    end_time = time.localtime()
                    print(host_N)
                    opID =shared.get_operatorId()
                    
                    print("op ID is",opID)
                    #sensor.close()
                    
                    # Convert end_time to datetime string for MySQL compatibility
                    end_time_str = time.strftime('%Y-%m-%d %H:%M:%S', end_time)
                    
                    # UPDATE the placeholder record instead of INSERT to avoid duplicates
                    sql = """
                    UPDATE device_data 
                    SET D_Number = CONCAT(%s, ' ', %s), End_date = %s, Diagnostic = %s, Code = %s
                    WHERE Serial = %s AND Start_date = %s AND Diagnostic = 'in_progress'
                    """
                    values = (host_N, end_time_str, end_time_str, 'failed', reason, host_N, self.start_time)

                    mycursor.execute(sql, values)
                    rows_updated = mycursor.rowcount
                    self.log_step(7, 'MOTION', f'Updated placeholder record (rows affected: {rows_updated})')
                    
                    print("Error Working")
                    self.log_step(7, 'MOTION', 'Committing failure record to DB')
                    mydb.commit()
                    # Immediately queue this failure record into data_q so cloud sync sees it.
                    try:
                        self.log_step('7.1', 'MOTION', 'Queueing failure record into data_q')
                        q_cursor = mydb.cursor()
                        q_sql = ("INSERT IGNORE INTO data_q (D_Number, Serial, Start_date, End_date, Diagnostic, Code, Operator_Id, Bed_Id, Side, Update_status, Insert_date) "
                                 "VALUES (CONCAT(%s,' ',%s), %s, %s, %s, %s, %s, %s, %s, %s, 'no', NOW())")
                        q_values = (host_N, end_time_str, host_N, self.start_time, end_time_str, 'failed', reason, opID, shared.get_bedId(), self.side_selected)
                        q_cursor.execute(q_sql, q_values)
                        mydb.commit()
                        self.log_step('7.2', 'MOTION', f'data_q queued (rowcount={q_cursor.rowcount})')
                        q_cursor.close()
                    except Exception as e:
                        self.log_error('7.2', 'MOTION', 'Failed to queue failure record into data_q', e)
                    self.log_step(8, 'MOTION', 'Closing DB resources')
                    mycursor.close()
                    mydb.close()
                    print("Error DB written")
                    
                    #try:
                        # Execute the external script
                        #result = subprocess.run(command, capture_output=True, text=True, check=True)
                        #process = subprocess.Popen(['python', 'LocalStor.py'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        # Print the output from the external script
                        #print("Background script started.")
                        #print("Output from the called script:")
                        #print(result.stdout)
                    #except subprocess.CalledProcessError as e:
                        #print("An error occurred while trying to run the script:", e)
                    self.comp = Button(
                    text="Done",
                    height=70,
                    halign = 'center',
                    color=(0, 153 / 255, 1, 1),
                    size_hint = (0.98,0.2),
                    pos_hint = {"x":0.0,"y":0.0},
                    #on_release=self.show_hospital_selection
        )
                    
                    self.layout.add_widget(self.comp)
                    #self.comp.bind(on_release=self.show_hospital_selection)
                    self.comp.bind(on_release=lambda instance: (self.stop_long_beeping(), self.show_hospital_selection(instance)))
                    #self.layout.add_widget(self.back_button1)
                    self.log_step(9, 'MOTION', 'Starting long beeping alert thread')
                    self.start_long_beeping()
                    # Trigger cloud sync on failure as well (to flush any pending queued rows)
                    self.log_step(10, 'MOTION', 'Triggering asynchronous cloud sync after motion failure')
                    Thread(target=lambda: self.trigger_cloud_sync(phase='MOTION', start_step=11), daemon=True).start()
                    return  # Exit after handling motion detection to prevent further execution
                else:   
                    print("in else - no motion detected")
                    self.log_step(4, 'CYCLE', f'No motion detected - distance {current_distance:.2f}cm is above {self.MOTION_THRESHOLD_CM}cm threshold')
                    # No baseline tracking needed - just continue countdown
                    minutes, seconds = divmod(self.countdown_time, 60)
                    self.countdown_label.text = f"{minutes:02}:{seconds:02}"
                    print(f"Countdown: {minutes:02}:{seconds:02} ({self.countdown_time} seconds remaining)")
                    self.countdown_time -= 1
                    
        else:
                # Countdown has reached 0 or below - cycle completed successfully
                print("=" * 50)
                print("CYCLE COMPLETED SUCCESSFULLY - COUNTDOWN REACHED 0")
                print("=" * 50)
                self.log_step(1, 'SUCCESS', 'Unscheduling countdown and marking completion')
                Clock.unschedule(self.update_ten_minute_countdown)
                
                # CRITICAL: Turn LEDs green and update UI FIRST before database operations
                self.log_step(2, 'SUCCESS', 'Setting LEDs to GREEN for success state')
                self.strip.set_all_pixels(Color(0, 255, 0))  # Turn LEDs GREEN for success
                self.strip.show()
                print("LEDs turned GREEN after successful cycle")
                
                self.countdown_label.text = "SUCCESSFUL"
                self.countdown_label.font_size = '50pt'
                reason = "Success at end of 10 mins"
                opID =shared.get_operatorId()
                print(reason)
                self.log_step(3, 'SUCCESS', 'Turning relay off')
                lgpio.gpio_write(self.h, 20, True)  # Turn relay off
                print("Relay 20 is deactivated")
                lgpio.gpiochip_close(self.h)
                
                # Now do database operations (these might block)
                print("Starting database write...")
                self.log_step(4, 'SUCCESS', 'Opening DB connection')
                mydb = mysql.connector.connect(
                    host='localhost',
                    user='root',
                    password="Robot123#",
                    database="robotdb"
                    )
                self.log_step(5, 'SUCCESS', 'Creating cursor for success record insert')
                mycursor = mydb.cursor()
                end_time = time.localtime()
                
                opID =shared.get_operatorId()   
                 

    
                # Convert end_time to datetime string for MySQL compatibility
                end_time_str = time.strftime('%Y-%m-%d %H:%M:%S', end_time)

                # UPDATE the placeholder record instead of INSERT to avoid duplicates
                sql = """
                UPDATE device_data 
                SET D_Number = CONCAT(%s, ' ', %s), End_date = %s, Diagnostic = %s, Code = %s
                WHERE Serial = %s AND Start_date = %s AND Diagnostic = 'in_progress'
                """
                values = (host_N, end_time_str, end_time_str, 'ok', reason, host_N, self.start_time)

                mycursor.execute(sql, values)
                rows_updated = mycursor.rowcount
                self.log_step(6, 'SUCCESS', f'Updated placeholder record (rows affected: {rows_updated})')
                
                print("Success Working")
                self.log_step(6, 'SUCCESS', 'Committing success record to DB')
                mydb.commit()
                # Immediately queue this success record into data_q so cloud sync sees it in same run.
                try:
                    self.log_step('6.1', 'SUCCESS', 'Queueing success record into data_q')
                    q_cursor = mydb.cursor()
                    q_sql = ("INSERT IGNORE INTO data_q (D_Number, Serial, Start_date, End_date, Diagnostic, Code, Operator_Id, Bed_Id, Side, Update_status, Insert_date) "
                             "VALUES (CONCAT(%s,' ',%s), %s, %s, %s, %s, %s, %s, %s, %s, 'no', NOW())")
                    q_values = (host_N, end_time_str, host_N, self.start_time, end_time_str, 'ok', reason, opID, shared.get_bedId(), self.side_selected)
                    q_cursor.execute(q_sql, q_values)
                    mydb.commit()
                    self.log_step('6.2', 'SUCCESS', f'data_q queued (rowcount={q_cursor.rowcount})')
                    q_cursor.close()
                except Exception as e:
                    self.log_error('6.2', 'SUCCESS', 'Failed to queue success record into data_q', e)
                self.log_step(7, 'SUCCESS', 'Closing DB resources')
                mycursor.close()
                mydb.close()
                print("`Success` DB written - database operations complete")
                
                # Start beeping before creating button
                self.log_step(8, 'SUCCESS', 'Starting normal beeping thread')
                self.start_beeping()
                
                #try:
                    # Execute the external script
                    #result = subprocess.run(command, capture_output=True, text=True, check=True)
                    #process = subprocess.Popen(['python', 'LocalStor.py'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    # Print the output from the external script
                    #print("Background script started.")
                    #print("Output from the called script:")
                    #print(result.stdout)
                #except subprocess.CalledProcessError as e:
                    #print("An error occurred while trying to run the script:", e)
                # ... (rest of your UI update code)

            # Add a back button at the top left
#            motion_sensor.close(7)


                self.comp = Button(
                text="Done",
                height=70,
                halign = 'center',
                color=(0, 153 / 255, 1, 1),
                size_hint = (0.98,0.2),
                pos_hint = {"x":0.0,"y":0.0},
                #on_release=self.show_hospital_selection
                )
                #self.sensor.close()
                self.layout.add_widget(self.comp)
                #self.comp.bind(on_release=self.show_hospital_selection)
                self.comp.bind(on_release=lambda instance: (self.stop_beeping(), self.show_hospital_selection(instance)))
                #self.back_button.bind(on_release=self.go_to_begin_robot_page)
                #self.add_widget(self.back_button)
                self.log_step(9, 'SUCCESS', 'Added Done button to layout')
                
                # Auto-trigger cloud sync asynchronously after successful cycle.
                # USB ports will be refreshed after cloud sync completes.
                self.log_step(10, 'SUCCESS', 'Triggering asynchronous cloud sync (post-cycle)')
                Thread(target=self.trigger_cloud_sync, daemon=True).start()
    def go_to_begin_robot_page(self, instance):
        self.layout.clear_widgets()
        self.create_main_content()