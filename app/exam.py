import logging
import numpy as np
import utils.utils as utils
from kivy.uix.widget import Widget
from kivy.clock import Clock
from kivy.graphics import Color, Line, Rectangle
from kivy.metrics import dp
from kivy.properties import StringProperty, ListProperty, ObjectProperty, BooleanProperty, NumericProperty
from kivymd.uix.list import MDList
from oklistitem import OKListItem

class Plot(Widget):
    sample_rate = NumericProperty(120)
    top_of_scale = NumericProperty(26400)
    run_samples = BooleanProperty(False)
    ekg_samples = ListProperty([])
    last_point = ListProperty([])
    next_samples = ListProperty([])
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

    def on_sample_rate(self, instance, value):
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
            self.canvas.clear()
            self.plot_grid()
        except ZeroDivisionError:
            pass

    def on_ekg_samples(self,*args):
        self.width = max((len(self.ekg_samples)*self.subdiv_size/(self.sample_rate*self.SEC_PER_SUBDIV))+4*self.MARGINS, self.width)
        logging.info(f"sample received: {len(self.ekg_samples)}")

    def on_next_samples(self, *args):
        if len(self.next_samples):
            self.ekg_samples.extend(self.next_samples)
            next_points = self.last_point + [(self.grid_x + next(self.time_generator)*self.subdiv_size/self.SEC_PER_SUBDIV,
                                                np.interp(sample,[0,self.top_of_scale],[0,self.grid_height])) for sample in self.next_samples]
            self.last_point = [next_points[-1]]
            with self.canvas.after:
                Color(rgba=[0.,0.,0.,1.0])
                Line(points=next_points,width=1.25)

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

    def clear_ekg(self):
        self.last_point = []
        self.ekg_samples = []
        self.canvas.after.clear()
        self.time_generator = utils.time_gen(self.sample_rate)

class ExamList(MDList):
    sex_icons = {'M': 'face-man', 'F': 'face-woman'}

    def populate(self, *args):
        self.clear_widgets()
        for i in range(10):
            self.add_widget(
                OKListItem(
                    object_id = 0,
                    text=f"EKG-210621-1405 {i} ",
                    secondary_text= "Fulano de Tal",
                    tertiary_text= "Sex: M  Age: 32  ",
                    icon = self.sex_icons['M'],
                    screen = "ekg_detail_view")
            )