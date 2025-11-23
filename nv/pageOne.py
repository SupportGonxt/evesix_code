from kivy.graphics import Rectangle
from kivy.uix.recyclegridlayout import defaultdict
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.uix.dropdown import DropDown
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
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

# Define the command to run the external script
command = ['python', 'Master.py']

try:
    # Execute the external script
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    #process = subprocess.Popen(['python', 'LocalStor.py'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # Print the output from the external script
    print("Background script started.")
    print("Output from the called script:")
    print(result.stdout)
except subprocess.CalledProcessError as e:
    print("An error occurred while trying to run the script:", e)


distance, threshold,count,c_time = shared.get_values()
pir = MotionSensor(22)
trigger_pin = 23
echo_pin = 24
# Create a DistanceSensor object
#sensor = DistanceSensor(echo=echo_pin, trigger=trigger_pin, max_distance=int(float(shared.get_distance())))
start_time = time.localtime()


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
        
        self.bed_button = Button(
            text='Select a bed',
            size_hint=(0.70, 0.15),
            background_color=(0, 153 / 255, 1, 1),
            # height=77,
            pos_hint={"x": 0.15, "y": 0.3}
        )
        self.bed_button.bind(on_release=dropdown1.open)
        dropdown1.bind(on_select=lambda instance, x: setattr(self.bed_button, 'text', x))
        
        def on_select(instance, value):
            self.bed_button.text = value 
            self.handle_bed_selection(instance) 
        # Bind the selection handler to the dropdown 
        dropdown1.bind(on_select=on_select)
        
        
        self.layout.add_widget(self.bed_button)
        
    def handle_bed_selection(self, instance): 
         
        self.submit_btn = Button(
            text="Submit",
            size_hint=(1, None),
            height=70,
            background_color=(0, 153/255, 1, 1),
            
            )
        self.submit_btn.bind(on_press=self.submit_selection)
        self.layout.add_widget(self.submit_btn)
    
    def call_back(self, instance):
        self.sensor.close()
        self.show_hospital_selection(instance)

    def show_hospital_selection(self, instance):
        self.sensor = DistanceSensor(echo=echo_pin, trigger=trigger_pin, max_distance=int(float(shared.get_distance())))

        self.main_layout.clear_widgets()
        self.layoutback.clear_widgets()
        self.layout.clear_widgets()

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

        self.hospital_button = Button(
            text='Select a ward',
            size_hint=(0.70, 0.15),
            background_color=(0, 153/255, 1, 1),
            #height=77,
            pos_hint = {"x":0.15,"y":0.5}
        )
        self.hospital_button.bind(on_release=dropdown.open)
        dropdown.bind(on_select=lambda instance, x: setattr(self.hospital_button, 'text', x))

        def on_select(instance, value):
            self.hospital_button.text = value 
            self.handle_selection(instance, value) 
        # Bind the selection handler to the dropdown 
        dropdown.bind(on_select=on_select)

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
            query = 'SELECT Bed_Id FROM bed WHERE Space = %s'
            param = (temp,) # Use a tuple for the parameter
            mycursor.execute(query, param)
            result = mycursor.fetchone()
            shared.set_bedId(result[0])
            
            mydb.close()
            
      

    def submit_selection(self, instance):  
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
        if self.timer_event  is not None:
            self.layout.clear_widgets()
            self.layout.add_widget(self.resume_button)            
            self.timer_event.cancel()
            self.timer_event  = None
            self.strip.set_all_pixels(Color(0, 255, 0))
            self.strip.show()
        else:
            self.countdown_time = self.timer_event 
        
       
        
        
    def update_initial_countdown(self, dt):
        if self.countdown_time > 0:
            self.countdown_label.text = f"You have \n {self.countdown_time} seconds \n to leave the room"
            self.countdown_time -= 1
        else:
            Clock.unschedule(self.update_initial_countdown)
            self.previous_distance = 0
            self.start_ten_minute_countdown()
            # Turn off all LEDs     turn red
            self.strip.set_all_pixels(Color(255, 0, 0))
            self.strip.show()
            
            print("RED LED is activated")
            
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
        Clock.schedule_interval(self.update_ten_minute_countdown, 1)
        # Set all LEDs to red
        self.strip.set_all_pixels(Color(255, 0, 0))
        self.strip.show()
        print("RED LED is activated after interval")
        start_time = time.localtime()
        print(start_time)
        # Initial distance reading
        self.previous_distance = self.sensor.distance * 100
        print("previous distance")
        print(self.previous_distance)
        # Initialize the relay
        self.h = lgpio.gpiochip_open(0)
        lgpio.gpio_claim_output(self.h, 20)
        lgpio.gpio_write(self.h, 20, False)  # Turn relay on when countdown starts
        print("Relay 20 is activated")
        #initialize Sensor
        

# Set all LEDs to GREEN
        self.strip.set_all_pixels(Color(0, 255, 0))
        self.strip.show()
        # Schedule the relay to turn off after 10 minutes
 #       self.turn_off_relay


    def update_ten_minute_countdown(self, dt):
        
        # Change this if using a different GPIO pin
        PIR_PIN = 22
        print("RCWL-0516 Sensor Active")
        host_N = platform.node()
        print(host_N)
        # Set a threshold for movement detection
        movement_threshold = int(float(shared.get_threshold()))  # Adjust this value as needed 
        
# Initialize detect variable        
        if self.countdown_time > 0:
                current_distance = self.sensor.distance * 100
                print("current distance")
                print(current_distance)
                print(self.countdown_time)
                print("previous distance")
                print(self.previous_distance)
                print("Threshold")
                print(self.previous_distance - movement_threshold)
                if  current_distance < self.previous_distance - movement_threshold or current_distance > self.previous_distance + movement_threshold:
                    print("in motion loop")
                    
                    self.previous_distance = current_distance
                    minutes, seconds = divmod(self.countdown_time, 60)
                    self.countdown_label.text = f"{minutes:02}:{seconds:02}"
                    self.countdown_time -= 1
                    self.countdown_label.text = "Error: Motion Detected"
                    self.countdown_label.font_size = '35pt'
                    end_time = time.localtime()
                    reason = "Error: Motion Detected"
                    current_distance=0
                    
                    print(reason)  
                    print (end_time)
                    # Turn relay off
                    print(self.countdown_time)
                    print("Motion Relay 20 is deactivated")
                    lgpio.gpio_write(self.h, 20, True)
                    lgpio.gpiochip_close(self.h)
                    Clock.unschedule(self.update_ten_minute_countdown)
#                    motion_sensor.close()
                    # Set all LEDs back to blue
                    self.strip.set_all_pixels(Color(0, 0, 255))
                    self.strip.show()
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
                    self.sensor.close()
                    
                    mycursor.execute('insert into device_data (Serial,Start_date,End_date, Diagnostic, Code,Operator_Id,Bed_Id) values (%s,%s,%s,%s,%s,%s,%s)', (host_N, start_time, end_time, 'Fail', reason,opID,shared.get_bedId() ))
                    mydb.commit()
                    mycursor.close()
                    mydb.close()
                    print("Error DB written")
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
                    self.comp.bind(on_release=self.show_hospital_selection)
                    #self.layout.add_widget(self.back_button1)
                else:   
                    print("in else")
                    minutes, seconds = divmod(self.countdown_time, 60)
                    self.countdown_label.text = f"{minutes:02}:{seconds:02}"
                    self.countdown_time -= 1
                    
        else:
                Clock.unschedule(self.update_ten_minute_countdown)
                self.countdown_label.text = "SUCCESSFUL"
                self.countdown_label.font_size = '50pt'
                reason = "Success at end of 10 mins"
                opID =shared.get_operatorId()
                print(reason)
                lgpio.gpio_write(self.h, 20, True)  # Turn relay off
                print("Relay 20 is deactivated")
                lgpio.gpiochip_close(self.h)
                mydb = mysql.connector.connect(
                    host='localhost',
                    user='root',
                    password="Robot123#",
                    database="robotdb"
                    )
                mycursor = mydb.cursor()
                end_time = time.localtime()
                
                opID =shared.get_operatorId()   
                    
                mycursor.execute('insert into device_data (Serial,Start_date,End_date, Diagnostic, Code,Operator_Id,Bed_Id) values (%s,%s,%s,%s,%s,%s,%s)', (host_N, start_time, end_time, 'ok', reason,opID,shared.get_bedId() ))
                
                mydb.commit()
                mycursor.close()
                mydb.close()
                print("`Success` DB written")
                
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
                self.sensor.close()
                self.layout.add_widget(self.comp)
                self.comp.bind(on_release=self.show_hospital_selection)
                #self.back_button.bind(on_release=self.go_to_begin_robot_page)
                #self.add_widget(self.back_button)

            # Set all LEDs back to red
                self.strip.set_all_pixels(Color(0, 255, 0))
                self.strip.show()

    def go_to_begin_robot_page(self, instance):
        self.layout.clear_widgets()
        self.create_main_content()