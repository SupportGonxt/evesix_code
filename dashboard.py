from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.graphics import Color, Rectangle
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.label import Label
from pin_manager import cleanup
import shared
import psutil
import mysql.connector
import platform
import time
import socket
import threading



# Import pages from pages.py
from pages import PageTwo, PageThree, FormPage
from pageOne import PageOne
from loginScreen import LoginScreen
from diagnose import Diagnose
import os
try:
    from version import VERSION
except Exception:
    VERSION = "v1.5"  # fallback if version module missing

class SplashScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Window.size = (400, 200)
        self.add_widget(Image(source='images/logo1.png', size_hint=(1, 1)))
        self.splash_time = 7  # 5 seconds
        Clock.schedule_interval(self.update_splash_screen, 1)

    def update_splash_screen(self, dt):
        self.splash_time -= 1
        if self.splash_time <= 0:
            Clock.unschedule(self.update_splash_screen)
            self.manager.current = 'login_screen'  # Switch to PageOne after splash

class Dashboard(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.current_signal_strength = 0  # Track signal strength
        # Verify image assets early
        self._verify_images([
            'logo1.png',
            'signal_0.png','signal_1.png','signal_2.png','signal_3.png','signal_4.png'
        ])

        # Set the main background to white
        with self.canvas.before:
            Color(1, 1, 1, 1)  # White color
            self.rect = Rectangle(size=self.size, pos=self.pos)
            self.bind(size=self._update_rect, pos=self._update_rect)

        # Header layout with white background
        header = BoxLayout(orientation='horizontal', size_hint_y=0.1, padding=1, spacing=1)
        with header.canvas.before:
            Color(1, 1, 1, 1)  
            self.header_rect = Rectangle(size=header.size, pos=header.pos)
            header.bind(size=self._update_header_rect, pos=self._update_header_rect)

        logo = Image(source='images/logo1.png', size_hint=(1, 1))  # Logo size
        header.add_widget(logo)
        # Version label (top-left inside header)
        try:
            from version import VERSION as _DASH_VERSION
        except Exception:
            _DASH_VERSION = "v1.5"
        ver_label = Label(text=f"[color=888888]{_DASH_VERSION}[/color]",
                          markup=True,
                          size_hint=(None, None),
                          font_size='8sp',
                          halign='left',
                          valign='middle')
        # Force texture update so width/height are correct
        ver_label.bind(texture_size=lambda *_: None)
        header.add_widget(ver_label)

        header_right = BoxLayout(orientation='horizontal', size_hint=(0.8, 1), spacing=1)
        
        self.signal_icon = Image(source="images/signal_0.png", size_hint=(None, None), size=(50, 50), pos_hint={'right': 1, 'top': 1})
        
        self.signal_label = Label(text="Strength: Checking...", size_hint=(None, None), size=(200, 50), 
                                  pos_hint={'right': 0.9, 'top': 0.92})
        
        start_time = time.localtime() 
        # Local MySQL database connection
        local_conn = mysql.connector.connect(
            host='localhost',
            user='root',
            password='Robot123#',
            database='robotdb'
        )

        # Create cursor
        mycursor = local_conn.cursor()

        # SQL query
        sql = """
        INSERT INTO data_q (
            D_Number, Start_date, End_date, Diagnostic, Code, Serial, Operator_Id, Bed_Id,Side,
            Update_status, Insert_date
        )
        SELECT 
            d.D_Number, d.Start_date, d.End_date, d.Diagnostic, d.Code, d.Serial, d.Operator_Id, d.Bed_Id, d.Side,
            'no', NOW()
        FROM device_data d
        WHERE NOT EXISTS (
            SELECT 1 
            FROM data_q q
            WHERE q.D_Number = d.D_Number AND q.Serial = d.Serial
        );
        """

        # Execute and commit
        mycursor.execute(sql)

        count = mycursor.rowcount
        if count > 0:
            mycursor.execute("""
                SELECT D_Number FROM data_q
                ORDER BY Insert_date DESC
                LIMIT %s
            """, (count,))
            new_rows = mycursor.fetchall()
            start_record = new_rows[0][0]
            end_record = new_rows[-1][0]
            end_time = time.localtime() 

            sync_insert_query = """
                INSERT INTO sync_log (
                    Sync_log_Id, Operation_type, Start_date, End_date, Number_Of_Records, Start_record,
                    End_record, Output
                )   VALUES (CONCAT(%s, ' ', %s), %s, %s, %s, %s, %s, %s, %s)
            """
            values = (platform.node(), end_time,'Data Copy', start_time, end_time, count,start_record, end_record,'Copy Completed')
            mycursor.execute(sync_insert_query, values)
            print(f"Also inserted  into sync table.")    

        local_conn.commit()

        # Close cursor and connection
        mycursor.close()
        local_conn.close()
    
        off_btn = Button(
            text='Off',
            size_hint=(0.1, 1),
            font_size=20,
            color=(1, 1, 1 , 1),  # Text color
            background_color=(0.57, 2, 6.5, 1) # Background color
        )
        off_btn.bind(on_release=self.stop_app)
        header_right.add_widget(self.signal_icon)
        # Schedule updates to the signal strength
        Clock.schedule_interval(self.update_signal, 2)  # Update every 2 seconds

        header.add_widget(header_right)
        self.screen_manager = ScreenManager()
        self.screen_manager.add_widget(SplashScreen(name='splash_screen'))
        self.screen_manager.add_widget(PageOne(name='page_one'))
        self.screen_manager.add_widget(PageTwo(name='page_two'))
        self.screen_manager.add_widget(PageThree(name='page_three'))
        diagnose_screen = Screen(name='diagnose')
        diagnose_screen.add_widget(Diagnose())
        self.screen_manager.add_widget(diagnose_screen)
        self.screen_manager.add_widget(LoginScreen(name='login_screen'))

        side_menu = BoxLayout(orientation='vertical', size_hint_x=0.2, padding=0, spacing=0)
        side_menu_buttons = [
            #('page_one', 'Robot'),
            ('page_two', 'Help', self.switch_page),
            ('page_three', 'Settings', self.check_setting_login),
            ('diagnose', 'Diagnose', self.switch_page),
        ]

        btnBegin = Button(text='Robot',
                          size_hint=(1, 0.2),
                          background_color=(0.57, 2, 6.5, 1),
                          on_release=self.check_login)
        side_menu.add_widget(btnBegin)

        for page, text, callback in side_menu_buttons:
            btn = Button(
                text=text,
                size_hint=(1, 0.2),
                background_color=(0.57, 2, 6.5, 1),
                on_release=lambda btn, cb=callback, pg=page: cb(pg)
            )
            side_menu.add_widget(btn)




        main_layout = BoxLayout(orientation='horizontal', size_hint_y=0.8)
        main_layout.add_widget(side_menu)
        main_layout.add_widget(self.screen_manager)

        self.add_widget(header)
        self.add_widget(main_layout)
        
        
    def update_signal(self, dt):
        # Run connectivity check in background thread to avoid blocking UI
        threading.Thread(target=self._check_connectivity, daemon=True).start()
    
    def _check_connectivity(self):
        try:
            # Check real internet connectivity
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            signal_strength = 4  # Connected
        except (socket.error, socket.timeout):
            signal_strength = 0  # Not connected
        except Exception as e:
            print(f"Signal check error: {e}")
            signal_strength = 0
        
        # Update UI on main thread
        self.current_signal_strength = signal_strength
        Clock.schedule_once(lambda _: self._update_signal_ui(signal_strength))
    
    def _update_signal_ui(self, signal_strength):
        self.signal_icon.source = f"images/signal_{signal_strength}.png"
        self.signal_label.text = f"Strength: {signal_strength}/4"

    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

    def callBegin(self, instance):
        self.screen_manager.current = 'login_screen'

    def _update_header_rect(self, instance, value):
        self.header_rect.pos = instance.pos
        self.header_rect.size = instance.size
        
    def check_login(self, instance):
        if shared.get_usercode() == '':
         print('not found')
         self.screen_manager.current = 'login_screen'
         
        else:
            print('found')
            self.screen_manager.current = 'page_one'
            
    def check_setting_login(self, instance):
        if shared.get_admin_usercode() == '':
         print('not found')
         self.screen_manager.current = 'login_screen'
         
        else:
            print('found')
            self.screen_manager.current = 'page_three'
       
    def switch_page(self, page_name):
        self.screen_manager.current = page_name

    def stop_app(self, *args):
        App.get_running_app().stop()

    def _verify_images(self, filenames):
        base = os.path.join(os.path.dirname(__file__), 'images')
        missing = [f for f in filenames if not os.path.exists(os.path.join(base, f))]
        if missing:
            print(f"[IMAGE WARNING] Missing image files: {', '.join(missing)} in 'images/' directory.")
            print(f"Ensure directory exists: {base}")
            print("Widgets using these images will appear blank.")



class DashboardApp(App):
    def build(self):
        return Dashboard()
        
    def on_stop(self):
        # Cleanup GPIO resources when the app stops
        cleanup()
        print("Resources cleaned up.")
   

if __name__ == '__main__':
    DashboardApp().run()
