from kivy.lang import Builder
from kivy.properties import StringProperty, ListProperty, NumericProperty, BooleanProperty
from kivymd.theming import ThemeManager
from kivymd.app import MDApp
from kivymd.theming import ThemableBehavior
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.list import OneLineIconListItem, MDList, ThreeLineIconListItem
from kivymd.uix.screen import MDScreen
from kivymd.uix.snackbar import Snackbar
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Line, Rectangle
from kivy.metrics import dp
from kivymd import icon_definitions
import utils
import numpy as np
import time
import sqlite3

# Window.size = (1280,800)
    
class ContentNavigationDrawer(MDBoxLayout):
    pass

class ItemDrawer(OneLineIconListItem):
    icon = StringProperty()
    text_color = ListProperty((0, 0, 0, 1))
    screen = StringProperty()

class DrawerList(ThemableBehavior, MDList):
    def set_color_item(self, instance_item):
        """Called when tap on a menu item."""

        # Set the color of the icon and text for the menu item.
        for item in self.children:
            if item.text_color == self.theme_cls.primary_color:
                item.text_color = self.theme_cls.text_color
                break
        instance_item.text_color = self.theme_cls.primary_color

class ToolbarScreen(MDScreen):
    title = StringProperty()

class EkgListItem(ThreeLineIconListItem):
    # name = StringProperty("EKG-DDMMAA-HHMM")
    icon = StringProperty("alert")

class Plot(Widget):
    sample_rate = 120
    run_samples = BooleanProperty(False)
    ekg_samples = ListProperty([])
    last_point = []
    sample_gen = utils.Signal(2.5, sample_rate, 100, 150, 'square')
    MARGINS = 16
    GRID_SUBDIVS = 5
    SEC_PER_SUBDIV = 0.04
    MV_PER_SUBDIV = 0.1
    GRID_SUBDIV_LINE_WIDTH = 0.5
    GRID_DIV_LINE_WIDTH = 1.2

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Clock.schedule_interval(self.update_plot,1/60.0)
        self.time_generator = utils.time_gen(self.sample_rate)

    def on_size(self,*args):
        try:
            self.grid_y_divs = 8 if self.height > 360 else 6

            self.y_subdiv_count = self.grid_y_divs*self.GRID_SUBDIVS
            self.subdiv_size = int((self.height - self.MARGINS)//(self.y_subdiv_count))
            self.div_size = self.subdiv_size*self.GRID_SUBDIVS

            self.grid_height = self.div_size*self.grid_y_divs
            self.grid_y = self.y + (self.height - self.grid_height)/2
            self.grid_top = self.grid_y + self.grid_height

            self.grid_x_divs = int((self.width - self.MARGINS)//(self.div_size))
            self.grid_width = self.grid_x_divs*self.div_size
            self.grid_x = self.x + self.MARGINS
            self.grid_right = self.grid_x + self.grid_width
            self.plot_grid()
        except ZeroDivisionError:
            pass

    def on_ekg_samples(self,*args):
        self.width = max((len(self.ekg_samples)*self.subdiv_size/(self.sample_rate*self.SEC_PER_SUBDIV))+4*self.MARGINS, self.width)

    def on_run_samples(self, *args):
        print("RUN SAMPLES MODIFIED")
        if self.run_samples:
            self.sample_gen.start(10)
            self.update_plot_event = Clock.schedule_interval(self.update_plot,1/60.0)
        else:
            try:
                self.update_plot_event.cancel()
                self.sample_gen.stop()
            except Exception as e:
                print("Something went wrong with the signal generato. ", e)
 
    def plot_grid(self, *args):
        with self.canvas.before:
            Color(rgba=[1.0, 0.85, 0.85, 0.8])
            Rectangle(pos=self.pos, size=self.size)
        with self.canvas:
            # eff_height = round(self.height/amp_divisions)*10 + 1
            Color(rgba=[0.86,0.59,0.59,0.9])
            try:
                for i in range(0, self.GRID_SUBDIVS*self.grid_x_divs + 1):
                    # vertical lines
                    pos = i*self.subdiv_size + self.grid_x
                    line_width = self.GRID_SUBDIV_LINE_WIDTH if (i % self.GRID_SUBDIVS > 0) else self.GRID_DIV_LINE_WIDTH
                    Line(points=[pos, self.grid_y, pos, self.grid_top], width=line_width)
                for i in range(0, self.y_subdiv_count + 1):
                    # horizontal lines
                    pos = i*self.subdiv_size + self.grid_y
                    line_width = self.GRID_SUBDIV_LINE_WIDTH if (i % self.GRID_SUBDIVS > 0) else self.GRID_DIV_LINE_WIDTH
                    Line(points=[self.grid_x, pos, self.grid_right, pos], width=line_width)
            except AttributeError:
                pass

    def update_plot(self, dt):
        if self.run_samples:
            next_samples = self.sample_gen.get_samples()
            if len(next_samples):
                self.ekg_samples.extend(next_samples)
                next_points = self.last_point + [(self.grid_x + next(self.time_generator)*self.subdiv_size/0.04,
                                                    np.interp(sample,[0,1023],[0,self.grid_height])) for sample in next_samples]
                self.last_point = [next_points[-1]]
                with self.canvas.after:
                    Color(rgba=[0.,0.,0.,1.0])
                    Line(points=next_points,width=1.25)
            else:
                self.run_samples = False
                print("Reached the end")

    def clear_ekg(self):
        self.last_point = []
        self.ekg_samples = []

class OpenKardioApp(MDApp):
    title = "OpenKardio"
    theme_cls = ThemeManager()

    def ekg_list_populate(self, *args):
        icons = {'M': 'human-male', 'F': 'human-female'}
        self.root.ids.ekg_list.clear_widgets()
        for i in range(10):
            self.root.ids.ekg_list.add_widget(
                EkgListItem(text=f"EKG-210621-1405 {i} ",
                secondary_text= "Fulano de Tal",
                tertiary_text= "Sex: M  Age: 32  ",
                icon = icons['M'])
            )
    def do_nothing(self, *args):
        pass

    def build(self):
        # con = sqlite3.connect('test.db')
        # cur = con.cursor()
        return Builder.load_file("ok.kv")

    def on_start(self):
        drawer_items = {
            "account": {"text": "Usuario", "target": "screen1","callback": self.do_nothing},
            "heart-pulse": {"text": "Electrocardiogramas", "target": "screen2", "callback": self.ekg_list_populate},
            "hospital-box": {"text": "Unidad de Salud", "target": "screen3", "callback": self.do_nothing},
            "folder-account": {"text": "Expedientes", "target": "screen4", "callback": self.do_nothing},
            "cog": {"text": "Configuración", "target": "screen5", "callback": self.do_nothing},
        }
        for item_name in drawer_items.keys():
            self.root.ids.content_drawer.ids.md_list.add_widget(
                ItemDrawer(icon=item_name, text=drawer_items[item_name]["text"], screen=drawer_items[item_name]["target"], on_release=drawer_items[item_name]["callback"])
            )
    
    def go_back(self, previous):
        self.root.ids.screen_manager.current = previous
        self.root.ids.screen_manager.transition.direction = "right"
    
OpenKardioApp().run()