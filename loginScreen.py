from kivy.app import App
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.screenmanager import ScreenManager, Screen
import mysql.connector
import shared


#import pageOne from pageOne
from pages import PageTwo, PageThree, FormPage
from pageOne import PageOne
#from dashboard import Dashboard

class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.lay = FloatLayout()
        self.laykey = FloatLayout()
        self.layVali = FloatLayout()
        self.add_widget(self.lay)
        self.add_widget(self.layVali)
        self.login()
        #self.user_inputs = {}

    def login(self):
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

        self.add_widget(self.send)
        self.add_widget(self.usercode)
        self.layVali.add_widget(self.validateInputs)
        
        
        #self.lay.add_widget(self.username)

        
        # Get the value from the text input and pass it to the next screen
        



        #first row
        return self.laykey
     
        

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
            self.lay.add_widget(button)
        self.back = Button(text='C', pos_hint={"x": 0.24, "y": 0.1}, size_hint=(0.15, 0.15))
        self.sub = Button(text = 'O K',pos_hint = {"x": 0.59, "y": 0.1}, size_hint = (0.15, 0.15))
        self.lay.add_widget(self.back)
        self.lay.add_widget(self.sub)
        self.back.bind(on_press=self.cancel)
        self.sub.bind(on_press=self.ok_btn)
        self.remove_widget(self.send)

        # Restrict to 4 digits



    def on_button_press(self, instance):
        self.usercode.text += instance.text

    def cancel(self, instance):
        self.usercode.text = ''

    def ok_btn(self, instance):
        self.lay.clear_widgets()
        self.add_widget(self.send)

    def on_back(self,instance):
        self.usercode.text -= instance.text

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
            self.manager.current = 'page_one'
            self.validateInputs.text = ' '
        else: 
            self.validateInputs.text = 'Failed to login'
            print("Login Failed")
        
        cursor.execute('SELECT Operator_Id FROM operator WHERE code = %s AND Role = %s' , (self.usercode.text,"Developer")) 
        Admin_Operator_Id = cursor.fetchone()
        if Admin_Operator_Id:
            shared.set_admin_usercode(Admin_Operator_Id[0])
            self.manager.current = 'page_three'
            self.validateInputs.text = ' '
        else: 
            self.validateInputs.text = 'Failed to login'
            print("Login Failed")

    #def keyboard(self, instance):
      #  self.keySmall = [('q',{"x": 0.54, "y": 0.49},(0.08, 0.1)),('w',{"x": 0.54, "y": 0.49},(0.08, 0.1))]
       # self.keyAlpha = ['Q','W','E','R','T','Y','U','I','O','P','A','s','D','F','G','H','J','K','L','Z','X','C','V','B','N','M']
       # self.letterA = Button(text = self.keySmall[3],pos_hint={"x":0.5,"y":0.5},size_hint=(0.5,0.5))
        #self.lay.add_widget(self.letterA)
