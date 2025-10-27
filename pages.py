from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.dropdown import DropDown
from kivy.uix.slider import Slider
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.graphics import Color, Rectangle
from kivy.clock import Clock
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.progressbar import ProgressBar
from kivy.uix.image import Image
import shared
import subprocess
import threading
import mysql.connector
import time
import platform



class PageTwo(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.toplay = FloatLayout()
        self.laybtn = FloatLayout()
        self.layout = FloatLayout()
        self.laybtn2 = FloatLayout()
        self.laybtn3 = FloatLayout()
        self.laybtn4 = FloatLayout()
        self.add_widget(self.toplay)
        self.add_widget(self.layout)
        self.add_widget(self.laybtn)
        self.add_widget(self.laybtn3)
        self.add_widget(self.laybtn4)
        self.add_widget(self.laybtn2)
        with self.canvas.before:
            self.rect = Rectangle(size=self.size, pos=self.pos)
            self.bind(size=self._update_rect, pos=self._update_rect)



        self.learn = Label(text="L E A R N   H O W", font_size=48, pos_hint = {"x":-0.0,"y":0.2}, color=(0, 153/255, 1, 1),bold=True)
        self.use = Label(text="T O  U S E", font_size=48, pos_hint = {"x":-0.0,"y":0.0}, color=(0, 153/255, 1, 1),bold=True)
        self.rob = Label(text="R O B O T", font_size=48, pos_hint = {"x":-0.0,"y":-0.2}, color=(0, 153/255, 1, 1),bold=True)
        self.btn = Button(text  = 'Next >>',size_hint = (0.2,0.1),pos_hint = {"x":0.8,"y":0.0})
        self.btn2 = Button(text  = 'Next >>',size_hint = (0.2,0.1),pos_hint = {"x":0.8,"y":0.0})
        self.btn3 = Button(text  = 'Next >>',size_hint = (0.2,0.1),pos_hint = {"x":0.8,"y":0.0})
        self.btn4 = Button(text  = 'Next >>',size_hint = (0.2,0.1),pos_hint = {"x":0.8,"y":0.0})
        self.btn5 = Button(text  = 'Next >>',size_hint = (0.2,0.1),pos_hint = {"x":0.8,"y":0.0})
        self.btn7 = Button(text  = 'Next >>',size_hint = (0.2,0.1),pos_hint = {"x":0.8,"y":0.0})
        #self.btn6 = Button(text  = 'Done',size_hint = (0.2,0.1),pos_hint = {"x":0.8,"y":0.0})
        self.bckbtn = Button(text  = '<< Back',size_hint = (0.2,0.1),pos_hint = {"x":0.0,"y":0.0},on_release = self.first_photo)
        self.bckbtn2 = Button(text  = '<< Back',size_hint = (0.2,0.1),pos_hint = {"x":0.0,"y":0.0},on_release = self.second_photo)
        self.bckbtn3 = Button(text  = '<< Back',size_hint = (0.2,0.1),pos_hint = {"x":0.0,"y":0.0},on_release = self.third_photo)
        self.bckbtn4 = Button(text  = '<< Back',size_hint = (0.2,0.1),pos_hint = {"x":0.0,"y":0.0},on_release = self.fourth_photo)
        self.bckbtn5 = Button(text  = '<< Back',size_hint = (0.2,0.1),pos_hint = {"x":0.0,"y":0.0},on_release = self.fifth_photo)
        #self.bckbtn1 = Button(text  = '<< Back',size_hint = (0.2,0.1),pos_hint = {"x":0.0,"y":0.0},on_release = self.)
        self.layout.add_widget(self.btn)
        self.toplay.add_widget(self.learn)
        self.toplay.add_widget(self.use)
        self.toplay.add_widget(self.rob)
        #pictures discription


        self.btn.bind(on_press = self.first_photo)
        self.btn2.bind(on_press = self.second_photo)
        self.btn3.bind(on_press = self.third_photo)
        self.btn4.bind(on_press = self.fourth_photo)
        self.btn5.bind(on_press = self.fifth_photo)
        self.btn7.bind(on_press = self.six_photo)
        #self.btn6.bind(on_press = self.finisher)
        
        

    def _update_rect(self, instance, value):
        self.rect.size = instance.size
        self.rect.pos = instance.pos

    def first_photo(self, instance):
        self.toplay.clear_widgets()
        self.layout.clear_widgets()
        self.img1 = Image(source='images/loginScreen.jpg',size_hint = (0.90,0.70), pos_hint={"x": 0.02, "y": 0.1})
        self.begin =  Label(text="Login to begin the robot",
                  font_size=30, pos_hint={"x": 0.0, "y": 0.4}, color=(0, 153 / 255, 1, 1),
                  bold=False)
        self.layout.add_widget(self.begin)
        self.layout.add_widget(self.img1)
        self.layout.add_widget(self.btn2)
    #self.layout.add_widget(self.bckbtn1)
        

    def second_photo(self, instance):
        self.layout.clear_widgets()
        self.img2 = Image(source='images/begin.jpg', size_hint=(0.80, 0.60), pos_hint={"x": 0.02, "y": 0.13})
        self.hos =  Label(text="Tap the screen to begin the robot",
                  font_size=30, pos_hint={"x": 0.0, "y": 0.4}, color=(0, 153 / 255, 1, 1),
                  bold=False)
        self.layout.add_widget(self.hos)
        self.layout.add_widget(self.btn3)
        self.layout.add_widget(self.img2)
        self.layout.add_widget(self.bckbtn)

    def third_photo(self, instance):
        self.layout.clear_widgets()
        self.img3 = Image(source='images/selectedButtons.jpg', size_hint=(0.80, 0.60), pos_hint={"x": 0.02, "y": 0.13})
        self.hosSelected = Label(text="Select the ward and the bed then click submit",
                         font_size=20, pos_hint={"x": 0.0, "y": 0.4}, color=(0, 153 / 255, 1, 1),
                         bold=False)
        self.layout.add_widget(self.hosSelected)
        self.layout.add_widget(self.btn4)
        self.layout.add_widget(self.img3)
        self.layout.add_widget(self.bckbtn2)
        

    def fourth_photo(self, instance):
        self.layout.clear_widgets()
        self.img4 = Image(source='images/bc.jpg', size_hint=(0.80, 0.60), pos_hint={"x": 0.02, "y": 0.13})
        self.ward = Label(text="Summary of your input",
                                 font_size=30, pos_hint={"x": 0.0, "y": 0.4}, color=(0, 153 / 255, 1, 1),
                                 bold=False)
        
        self.ward1 = Label(text="-click back for re-select-",
                                 font_size=30, pos_hint={"x": 0.0, "y": 0.3}, color=(0, 153 / 255, 1, 1),
                                 bold=False)
        
        self.layout.add_widget(self.ward)
        self.layout.add_widget(self.ward1)
        self.layout.add_widget(self.btn5)
        self.layout.add_widget(self.img4)
        self.layout.add_widget(self.bckbtn3)

    def fifth_photo(self, instance):
        self.layout.clear_widgets()
        self.img5 = Image(source='images/submit.jpg', size_hint=(0.80, 0.60), pos_hint={"x": 0.02, "y": 0.13})
        self.wardSelected = Label(text="Click start button to beggin the robot",
                          font_size=30, pos_hint={"x": 0.0, "y": 0.4}, color=(0, 153 / 255, 1, 1),
                          bold=False)
        self.layout.add_widget(self.bckbtn4)
        #self.layout.add_widget(self.btn6)
        self.layout.add_widget(self.img5)
        self.layout.add_widget(self.wardSelected)
        
    def six_photo(self,instance):
        self.layout.clear_widgets()
        self.wardSelected = Label(text="Click stop for pause and resume",
                          font_size=30, pos_hint={"x": 0.0, "y": 0.4}, color=(0, 153 / 255, 1, 1),
                          bold=False)
        self.img6 = Image(source='images/stop.jpg', size_hint=(0.80, 0.60), pos_hint={"x": 0.02, "y": 0.13})
        self.layout.add_widget(self.bckbtn5)
        self.layout.add_widget(self.btn7)
        self.layout.add_widget(self.img6)
        self.layout.add_widget(self.wardSelected)
        
        #16799
    def finisher(self, instance):
        self.layout.clear_widgets()
        self.manager.current = 'login_screen'
        
class PageThree(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.lay = FloatLayout()
        lays = FloatLayout()
        self.laysend = FloatLayout()
        self.blay = BoxLayout(orientation='vertical')
        self.glay = GridLayout(cols=3, rows=2)
        self.lay_admin = FloatLayout()
        self.keylay = FloatLayout()
        self.add_widget(self.lay)
        self.add_widget(lays)
        self.add_widget(self.keylay)
        self.add_widget(self.blay)
        self.add_widget(self.laysend)
        self.add_widget(self.lay_admin)
        self.lay = FloatLayout()
        self.laykey = FloatLayout()
        self.add_widget(self.lay)
        # Set the background color to white
        with self.canvas.before:
            self.rect = Rectangle(size=self.size, pos=self.pos)
            self.bind(size=self._update_rect, pos=self._update_rect)



        #self.add_widget(Label(text="Config Page", font_size=32, color=(0, 153/255, 1, 1), bold=True))  # Text color black for contrast

        #admin = Button(text='admin', size_hint=(0.55,0.2),pos_hint={"x":0.24,"y":0.5},color=(0, 153/255, 1, 1)
                            #,on_release=self.login)
        #sync = Button(text='sync', size_hint=(0.55, 0.2), pos_hint={"x": 0.24, "y": 0.28}, color=(0, 153 / 255, 1, 1),on_release=self.sync_data)
        #self.lay.add_widget(admin)
        #self.lay.add_widget(sync)
        
        admin = Button(text='admin', size_hint=(0.55,0.2), pos_hint={"x":0.24, "y":0.5}, color=(0, 153/255, 1, 1))
        admin.bind(on_release=self._admin)
        sync = Button(text='sync', size_hint=(0.55, 0.2), pos_hint={"x":0.24, "y":0.28}, color=(0, 153/255, 1, 1), on_release=self.sync_data)
        bulb_replacement = Button(text='bulb replacement', size_hint=(0.55, 0.2), pos_hint={"x":0.24, "y":0.06}, color=(0, 153/255, 1, 1), on_release=self.replace_bulb)

        self.lay.add_widget(admin)
        self.lay.add_widget(sync)
        self.lay.add_widget(bulb_replacement)

        
      

        
    #def keyboard(self, instance):
        
  

    def sync_data(self, instance):
        # Create the ProgressBar
        self.progress_bar = ProgressBar(max=100)
    
        # Create the popup
        progress_popup = Popup(
            title='Syncing Data',
            content=self.progress_bar,
            size_hint=(0.6, 0.3)
        )
        progress_popup.open()

        # Start progress simulation in a thread
        threading.Thread(target=self.run_scripts_with_progress, args=(progress_popup,), daemon=True).start()

    def run_scripts_with_progress(self, popup):
        try:
            # Step 1: Run Master.py and update progress to 50%
            result = subprocess.run(['python', 'Master.py'], capture_output=True, text=True, check=True)
            Clock.schedule_once(lambda dt: self.update_progress(50), 0)

            # Step 2: Run LocalStor.py and update to 100%
            process = subprocess.Popen(['python', 'cloudSync.py'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            Clock.schedule_once(lambda dt: self.update_progress(100), 0)

            # Optional: Print outputs for debugging
            print("Output from Master.py:", result.stdout)
            print("Output from LocalStor.py:", stdout.decode())

        except subprocess.CalledProcessError as e:
            print("An error occurred:", e)

        # Close popup once completed
        Clock.schedule_once(lambda dt: popup.dismiss(), 1)

    def update_progress(self, value):
        # Ensure the UI update is safely scheduled on the main thread
        Clock.schedule_once(lambda dt: setattr(self.progress_bar, 'value', value), 0)
        
    def login(self, instance):
        self.lay.clear_widgets()
        self.validateInputs = Label(text='',
                           font_size=30,
                           underline=True,
                           bold=True,
                           color=(0, 153 / 255, 1, 1),
                           halign='center',
                           pos_hint={"x": 0.24, "y": 0.3},
                           size_hint=(0.5, 0.1)
                           )
        self.usercode = TextInput(multiline=False,
                             #halign='center',
                             hint_text = 'code',
                             input_filter='int',
                             #max_length = 4,
                             font_size=20,
                             pos_hint={"x": 0.24, "y": 0.7},
                                  size_hint = (0.5,0.2))
        self.send = Button(text='Login',color=(0, 153 / 255, 1, 1),
                           pos_hint={"x": 0.24, "y": 0.40},
                           halign='center',
                           size_hint = (0.5,0.2),
                           )
        self.send.bind(on_release = self.login_user)
        self.usercode.bind(focus = self.call_keyboard)


        self.laysend.add_widget(self.send)
        self.lay.add_widget(self.usercode)

        #first row
        return self.laykey
        
    def login_user(self, instance):
        shared.set_usercode(self.usercode.text)
        print(self.usercode.text)
        
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='Robot123#',
            database='robotdb'
        )
        
        cursor = connection.cursor()
        cursor.execute('SELECT Operator_Id FROM operator WHERE code = %s', (self.usercode.text,)) 
        Operator_Id = cursor.fetchone()
       
        if Operator_Id:
            shared.set_operatorId(Operator_Id[0])
            self.lay.clear_widgets()
            self._admin(instance)
            self.validateInputs.text = ' '
        else: 
            self.validateInputs.text = 'Failed to login'
            print("Login Failed")
        
    def submit_value(self,v1,v2,v3,v4):
        print("Fetched values before:",shared.get_values())
        shared.set_values(v1,v2,v3,v4)
        print(v1,v2,v3,v4)
        print("Fetched values after update:",shared.get_values())
        self.manager.current = 'page_one'
           
    def clear_send(self, instance):
        self.lay.clear_widgets()
        self._admin(instance)

    def call_keyboard(self, instance, value):
        self.validateInputs.text = ' '
        self.keySmall = [('1', {"x": 0.24, "y": 0.55}, (0.15, 0.15)), ('3', {"x": 0.59, "y": 0.55}, (0.15, 0.15)),
                         ('2', {"x": 0.41, "y": 0.55}, (0.15, 0.15)),
                         ('4', {"x": 0.24, "y": 0.4}, (0.15, 0.15)), ('6', {"x": 0.59, "y": 0.4}, (0.15, 0.15)),
                         ('5', {"x": 0.41, "y": 0.4}, (0.15, 0.15)),
                         ("7",{"x": 0.24, "y": 0.25}, (0.15, 0.15)), ('9', {"x": 0.59, "y": 0.25}, (0.15, 0.15)),
                          ('8', {"x": 0.41, "y": 0.25}, (0.15, 0.15)),
                        ('0', {"x":       0.41, "y": 0.1}, (0.15, 0.15))
                         ]

        for text, pos_hint, size_hint in self.keySmall:
            button = Button(text=text, size_hint=size_hint, pos_hint=pos_hint)
            button.bind(on_press=self.on_button_press)
            #button[self.keySmall(10)].bind(on_press=self.on_back)
            self.keylay.add_widget(button)
        self.back = Button(text='C', pos_hint={"x": 0.24, "y": 0.1}, size_hint=(0.15, 0.15))
        self.sub = Button(text = 'O K',pos_hint = {"x": 0.59, "y": 0.1}, size_hint = (0.15, 0.15))
        self.keylay.add_widget(self.back)
        self.keylay.add_widget(self.sub)
        self.back.bind(on_press=self.cancel)
        self.sub.bind(on_press=self.ok_btn)
        self.laysend.clear_widgets()

        # Restrict to 4 digits
    
        
    def on_button_press(self, instance):
        self.usercode.text += instance.text

    def cancel(self, instance):
        self.usercode.text = ''

    def ok_btn(self, instance):
        self.keylay.clear_widgets()
        self.laysend.add_widget(self.send)
        
    def save_bulb_replacement_data(self,bulb_num):
        
        mydb = mysql.connector.connect(
            host="localhost",
            user="root",
            password="Robot123#",
            database="robotdb"
        )
        mycursor = mydb.cursor()
        replaement_date = time.localtime()
        sql = """
        INSERT INTO bulb_replace (BR_ID, Bulb_Num, Replacement_date, Serial,Sync_status)
        VALUES (CONCAT(%s, ' ', %s), %s, %s, %s, %s)
        """
        values = (
            platform.node(),
            replaement_date,
            bulb_num,
            replaement_date,
            platform.node(),
            'no'
        )
        mycursor.execute(sql, values)
        print("Database updated bulb table successfully")
        mydb.commit()
        mycursor.close()
        mydb.close()
        
        
   
    def show_popup(self, button_text):
        main_layout = BoxLayout(orientation='vertical', spacing=10)

        # Display the pressed number
        message = Label(text=f"Are you replacing : {button_text}", font_size=20)

        # Horizontal layout for buttons
        button_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint=(1, None), height=50)

        # Cancel button (red)
        cancel_button = Button(
            text="Cancel",
            size_hint=(0.5, 1),
            background_color=(1, 0, 0, 1)
        )

        # Confirm button
        confirm_button = Button(
            text="Confirm",
            size_hint=(0.5, 1)
        )

        # Add buttons to horizontal layout
        button_layout.add_widget(cancel_button)
        button_layout.add_widget(confirm_button)

        # Initialize popup before binding
        popup = Popup(
            title="Confirmation",
            content=main_layout,
            size_hint=(None, None),
            size=(400, 200)
        )

        last_value = button_text[-1] if isinstance(button_text, (list, str)) else button_text

        # Bind actions
        confirm_button.bind(on_release=lambda instance: (popup.dismiss(), self.save_bulb_replacement_data(last_value)))
        cancel_button.bind(on_release=lambda instance: (popup.dismiss(), self.replace_bulb))

        # Add widgets to main layout
        main_layout.add_widget(message)
        main_layout.add_widget(button_layout)

        popup.open()



   
    def replace_bulb(self, instance):
        self.laysend.clear_widgets()
        self.lay.clear_widgets()

        # Create a new GridLayout instead of reusing self.glay
        glay = GridLayout(cols=3, rows=2, spacing=10, padding=10)

        for i in range(1, 7):
            btn = Button(text=f"BULB NUMBER {i}")
            btn.bind(on_release=lambda instance: self.show_popup(instance.text))
            glay.add_widget(btn)

        # Create a vertical layout to hold the grid and back button
        layout = BoxLayout(orientation='vertical', spacing=20, padding=20)

        layout.add_widget(glay)
    
        back_btn = Button(
            text='Back',
            size_hint=(0.5, None),
            height=50,
            pos_hint={'center_x': 0.5},
            color=(0, 153 / 255, 1, 1),
            on_release=self.go_back
        )

        layout.add_widget(back_btn)

        self.lay.add_widget(layout)
        return self.lay
        
    def go_back(self, instance):
        # Clear admin layout
        self.lay_admin.clear_widgets()
        self.blay.clear_widgets()
        self.laysend.clear_widgets()

        # Optional: hide or reset other layouts if needed
        # Redisplay main layout with the original buttons
        self.lay.clear_widgets()

        admin = Button(text='admin', size_hint=(0.55, 0.2), pos_hint={"x": 0.24, "y": 0.5}, color=(0, 153 / 255, 1, 1))
        admin.bind(on_release=self._admin)

        sync = Button(text='sync', size_hint=(0.55, 0.2), pos_hint={"x": 0.24, "y": 0.28}, color=(0, 153 / 255, 1, 1))
        sync.bind(on_release=self.sync_data)

        bulb_replacement = Button(text='bulb replacement', size_hint=(0.55, 0.2), pos_hint={"x": 0.24, "y": 0.06}, color=(0, 153 / 255, 1, 1))
        bulb_replacement.bind(on_release=self.replace_bulb)

        self.lay.add_widget(admin)
        self.lay.add_widget(sync)
        self.lay.add_widget(bulb_replacement)    

    def _admin(self, instance):
        self.laysend.clear_widgets()
        #self.laysend.remove_widget(self.send)
        self.lay.clear_widgets()
        self.sliderdistance = Slider(min=1, max=4, value=2)
        self.sliderthreshold = Slider(min=0, max=50, value=17.5)
        self.slidercount = Slider(min=20, max=60, value=30)
        self.slidertime = Slider(min=5, max=30, value=10)
        self.sliderdistance.bind(value=self.on_valuedis)
        self.sliderthreshold.bind(value=self.on_valuethresh)
        self.slidercount.bind(value=self.on_count)
        self.slidertime.bind(value=self.on_time)
        self.distance = Label(text=f'maximum distance: {self.sliderdistance.value}', color=(0, 153 / 255, 1, 1))
        self.submit = Button(text='submit changes',color=(0, 153 / 255, 1, 1),on_release=lambda _: self.submit_value(shared.get_distance(), shared.get_threshold(), shared.get_count(), shared.get_time()))
        self.back = Button(text='Back',color=(0, 153 / 255, 1, 1),on_release=self.go_back )
        button_row = BoxLayout(orientation='horizontal', size_hint=(1, None), height=50)
        button_row.add_widget(self.back)
        button_row.add_widget(self.submit)

        self.threshold = Label(text=f'movement threshold: {self.sliderthreshold.value}',  color=(0, 153 / 255, 1, 1))
        self.count = Label(text=f'Countdown seconds: {self.slidercount.value}',  color=(0, 153 / 255, 1, 1))
        self.time = Label(text=f'Time: {self.slidertime.value}',  color=(0, 153 / 255, 1, 1))
        self.blay.add_widget(self.distance)
        self.blay.add_widget(self.sliderdistance)
        self.blay.add_widget(self.threshold)
        self.blay.add_widget(self.sliderthreshold)
        self.blay.add_widget(self.count)
        self.blay.add_widget(self.slidercount)
        self.blay.add_widget(self.time)
        self.blay.add_widget(self.slidertime)
        self.blay.add_widget(button_row)
        
        self.distance.bind(on_touch_up=self.on_distance_stop)
        self.sliderthreshold.bind(on_touch_up=self.on_threshold_stop)
        self.slidercount.bind(on_touch_up=self.on_count_stop)
        self.slidertime.bind(on_touch_up=self.on_time_stop)

    
        


    def on_distance_stop(self, instance, touch):
        # Check if the touch event happened on the slider
        if instance.collide_point(*touch.pos):
            # Update the label with the final value of the slider when the touch ends
            dis = self.distance.text = f"{instance.value:.2f}"
            print(dis)
            shared.set_distance(dis)
            
            
            
    def on_threshold_stop(self, instance, touch):
        if instance.collide_point(*touch.pos):
            thres = self.threshold.text = f"{instance.value:.2f}"
            print(thres)
            shared.set_threshold(thres)
            
    def on_count_stop(self, instance, touch):
        if instance.collide_point(*touch.pos):
            count = self.count.text = f"{instance.value:.2f}"
            print(count)
            shared.set_count(count)
        
    def on_time_stop(self, instance, touch):
        if instance.collide_point(*touch.pos):
            ti = self.time.text = f"{instance.value:.2f}"
            print(ti)
            shared.set_time(ti)
    
    def on_valuethresh(self, instance, value):
        self.threshold.text = f'Movement threshold: {value:.2f} cm'
        
        
    def on_count(self, instance, value):
        self.count.text = f'Countdown seconds: {value:.2f} sec'
        
    def on_time(self, instance, value):
        self.time.text = f'Time: {value:.2f} min' 

    def on_valuedis(self, instance, value):
        self.distance.text = f'Maximum distance: {value:.2f} m'        
        


    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

class FormPage(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=10)
        form_title = Label(
            text="Inspection Form",
            font_size=35,
            color=(0, 153/255, 1, 1), 
            bold=True,
        )
        layout.add_widget(form_title)
        
        self.responses = {}
        self.create_form(layout)
        self.add_widget(layout)

    def create_form(self, layout):
        questions = [
            ("Did you visually inspect the bed for any visible biohazards (blood, vomit, etc.)?", ["Yes", "No"]),
            ("If you answered yes to question 1, did you remove and dispose of the biohazards properly according to infection control protocols?", ["Yes", "No"]),
            ("Did you remove all linens and personal belongings from the bed?", ["Yes", "No"]),
            ("Did you ensure the entire bed surface is unobstructed for the robot's operation?", ["Yes", "No"]),
        ]

        for index, (question_text, options) in enumerate(questions):
            question_label = Label(text=question_text, font_size=20, color=(0, 153/255, 1, 1))
            question_dropdown = DropDown()
            question_button = Button(text='Select', size_hint_y=None, height=44, font_size=25, background_color=(0, 153/255, 1, 1))
            question_button.bind(on_release=question_dropdown.open)
            question_dropdown.bind(on_select=lambda instance, x, index=index: self.update_response(x, index))
            
            for option in options:
                btn = Button(text=option, size_hint_y=None, height=44, background_color=(0, 153/255, 1, 1),)
                btn.bind(on_release=lambda btn: question_dropdown.select(btn.text))
                question_dropdown.add_widget(btn)
                
            layout.add_widget(question_label)
            layout.add_widget(question_button)

        submit_button = Button(text="Submit", size_hint=(None, None), size=(100, 50))
        submit_button.bind(on_release=self.validate_and_submit_form)
        layout.add_widget(submit_button)

    def update_response(self, selected_option, question_index):
        self.responses[question_index] = selected_option

    def validate_and_submit_form(self, instance):
        if len(self.responses) < 4:
            self.show_error_popup("Please answer all questions.")
            return
        
        valid = True
        for response in self.responses.values():
            if response == "No":
                valid = False
                break
        
        if not valid:
            self.show_error_popup("Please inspect the room accordingly.")
        else:
            print("Form submitted!")
            # Handle form submission logic here

    def show_error_popup(self, message):
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        error_message = Label(text=message, font_size=14)
        content.add_widget(error_message)
        
        close_button = Button(text="Close", size_hint_y=None, height=50)
        close_button.bind(on_release=lambda x: self.popup.dismiss())
        content.add_widget(close_button)
        
        self.popup = Popup(title="Validation Required", content=content, size_hint=(None, None), size=(300, 200))
        self.popup.open()