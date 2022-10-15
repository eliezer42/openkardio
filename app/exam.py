import logging
import sqlalchemy
import utils.localdb as ldb
import numpy as np
import utils.utils as utils
from kivy.uix.widget import Widget
from kivy.clock import Clock
from kivy.graphics import Color, Line, Rectangle, RoundedRectangle
from kivy.metrics import dp
from kivy.properties import DictProperty, StringProperty, ListProperty, ObjectProperty, BooleanProperty, NumericProperty
from kivymd.app import MDApp
from kivymd.uix.list import MDList
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.toast import toast
from okwidgets import OKListItem, OKCard

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

class MiniPlot(Widget):
    line = ObjectProperty()
    samples = ListProperty([])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
    def on_size(self, *args):
        with self.canvas.before:
            Color(rgba=[0.96,0.9,0.87, 0.83])
            RoundedRectangle(pos=self.pos, size=self.size, radius = [(20, 20), (20, 20), (20, 20), (20, 20)])
            Color(rgba=[0,0,0,1])
            Line(points=[self.x, self.height/2, self.right, self.height/2], width=1)

    def clear_line(self):
        self.canvas.after.clear()
    
    def update(self, sample_list):
        line = Line()

class ExamList(MDBoxLayout):
    def populate(self, text="", search=False):
        '''Builds a list of icons for the screen MDIcons.'''

        def add_item(instance):
            self.ids.rv.data.append(
                {
                    "viewclass": "OKListItem",
                    "object_id": instance.id,
                    "text": f'EKG-{instance.created.strftime("%Y%m%d")}-{instance.id}',
                    "secondary_text": instance.patient.first_name + " " + instance.patient.last_name,
                    "tertiary_text": f"Expediente no.: {instance.patient.record}",
                    "icon": MDApp.get_running_app().icons.get(instance.patient.sex),
                    "screen": "ekg_create_view",
                    "propagate": True
                }
            )

        self.ids.rv.data = []
        app_session = MDApp.get_running_app().session
        for instance in app_session.query(ldb.Exam).order_by(ldb.Exam.id):
            if search:
                if text in instance.patient.first_name or\
                    text in instance.patient.last_name or\
                    text in instance.patient.record:
                    add_item(instance)
            else:
                add_item(instance)

class PatientSelector(MDBoxLayout):
    def populate(self, text="", search=False):
        '''Builds a list of icons for the screen MDIcons.'''

        def add_patient_item(instance):
            self.ids.rv.data.append(
                {
                    "viewclass": "OKSelectorItem",
                    "object_id": instance.id,
                    "text": instance.first_name + " " + instance.last_name,
                    "secondary_text": f"Expediente no.: {instance.record}",
                    "icon": MDApp.get_running_app().icons.get(instance.sex),
                    "screen": "ekg_create_view"
                }
            )

        self.ids.rv.data = []
        app_session = MDApp.get_running_app().session
        for instance in app_session.query(ldb.Patient).order_by(ldb.Patient.id):
            if search:
                if text in instance.first_name or text in instance.last_name or text in instance.record:
                    add_patient_item(instance)
            else:
                add_patient_item(instance)

class ExamMetadataForm(OKCard):
    data = DictProperty({})
    def populate(self, patient_id):
        app_session = MDApp.get_running_app().session
        try:
            self.patient = app_session.query(ldb.Patient).filter(ldb.Patient.id == patient_id).one()
            self.ids.info.text = f"{self.patient.first_name} {self.patient.last_name}"
            self.ids.info.icon = MDApp.get_running_app().icons.get(self.patient.sex[0])
        except sqlalchemy.orm.exc.NoResultFound:
            toast('Hubo un error al buscar el examen.')


class ExamMetadataDetail(OKCard):
    exam = ObjectProperty(ldb.Exam())

    def populate(self, exam_id):
        app_session = MDApp.get_running_app().session
        try:
            self.patient = app_session.query(ldb.Exam).filter(ldb.Patient.id == exam_id).one()
        except sqlalchemy.orm.exc.NoResultFound:
            toast('Hubo un error al buscar el examen.')
    
    def on_exam(self, instance, value):
        logging.warning(f"Exam ID: {value.id}")
        self.ids.info.icon = MDApp.get_running_app().icons.get(value.patient.sex)
        self.ids.info.text = "Nombres: " + value.patient.first_name + "\n" + "Apellidos: " + value.patient.last_name
        self.ids.age.text = "Edad: " + str(value.patient.age()) + " años"
        self.ids.spo2.text = f"{value.spo2} %"
        self.ids.weight.text = f"{value.weight_pd} lbs"
        self.ids.press.text = f"{value.sys_pres}/{value.dia_pres}"
        
class OKDevicePanel(OKCard):
    sample_rate = StringProperty("T. de muestreo: ")
    leads = StringProperty("Derivaciones: ")
    battery = StringProperty("Batería: ")
