import logging
import sqlalchemy
import utils.localdb as ldb
import numpy as np
import utils.utils as utils
from kivy.uix.widget import Widget
from kivy.clock import Clock
from kivy.graphics import Color, Line, Rectangle, RoundedRectangle
from kivy.metrics import dp
from kivy.properties import DictProperty, StringProperty, ListProperty, ObjectProperty, BooleanProperty, NumericProperty, ColorProperty
from kivymd.app import MDApp
from kivymd.uix.list import MDList
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.toast import toast
from okwidgets import OKListItem
import pickle

class Plot(Widget):
    sample_rate = NumericProperty(120)
    top_of_scale = NumericProperty(26400)
    run_samples = BooleanProperty(False)
    ekg_samples = ListProperty([])
    last_point = ListProperty([])
    next_samples = ListProperty([])
    line = ObjectProperty(Line())
    bpm = NumericProperty(80)
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
        with self.canvas.after:
            Color(0, 0, 0, 1)
            self.line = Line(points=[10,10,20,20], width = 1)

    def on_sample_rate(self, instance, value):
        self.time_generator = utils.time_gen(self.sample_rate)

    def on_size(self,*args):
        try:
            self.grid_y_divs = 8 if self.height > 480 else 6

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
        logging.info(f"Samples received: {len(self.ekg_samples)}")

    def on_next_samples(self, *args):
        if len(self.next_samples):
            next_points = [point for sample in self.next_samples for point in [self.grid_x + next(self.time_generator)*self.subdiv_size/self.SEC_PER_SUBDIV,
                                                np.interp(sample,[0,self.top_of_scale],[0,self.grid_height])]]
            self.line.points += next_points
            self.ekg_samples.extend(self.next_samples)

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

    def populate(self, ekg_id):
        self.time_generator = utils.time_gen(self.sample_rate)
        self.ekg_samples = []
        self.line.points = []
        app_session = MDApp.get_running_app().session
        try:
            ekg = app_session.query(ldb.Ekg).filter(ldb.Ekg.id == ekg_id).one()
            self.next_samples = pickle.loads(ekg.signal)
        except sqlalchemy.orm.exc.NoResultFound as e:
            logging.error(e)
            toast('Hubo un error al buscar el EKG.')

    def get_ekg(self):
        if len(self.ekg_samples):
            return {
                'bpm':self.bpm,
                'sample_rate':self.sample_rate,
                'gain':1,
                'signal':pickle.dumps(self.ekg_samples)
            }
        return {
                'bpm':self.bpm,
                'sample_rate':self.sample_rate,
                'gain':1,
                'signal':pickle.dumps([item*16 for item in [959,958,957,955,954,954,953,954,953,951,949,951,950,952,951,947,
        947,948,950,949,949,947,945,946,947,945,945,943,942,942,943,944,
        944,942,942,942,943,943,943,944,944,944,947,947,948,943,943,945,
        945,947,951,950,954,957,958,960,961,958,957,960,962,966,966,963,
        961,964,968,966,966,964,960,959,955,955,956,954,955,956,960,959,
        956,951,947,946,948,947,945,941,938,938,935,935,933,933,933,935,
        937,937,934,931,930,932,934,935,936,935,933,933,934,935,934,933,
        929,921,910,904,907,917,930,952,990,1058,1131,1204,1267,1325,1361,
        1364,1325,1236,1122,1019,951,919,909,910,928,948,957,955,945,942,
        938,941,940,939,936,930,929,928,929,929,928,927,925,927,927,926,
        928,926,927,928,930,929,927,926,926,926,929,928,930,928,926,927,
        933,934,934,933,929,935,937,939,939,937,938,942,944,948,949,951,
        953,957,961,965,966,970,972,976,981,983,988,990,992,998,1003,1006,
        1010,1012,1013,1015,1019,1025,1026,1026,1027,1031,1032,1035,1036,
        1031,1030,1033,1031,1032,1030,1025,1022,1018,1016,1013,1005,1003,
        997,993,990,989,984,979,972,971,970,971,967,964,962,961,963,964,
        961,957,955,959,958,959,958,955,957,957,958,957,957,954,956,957,
        958,957,959,958,960,960,961,960,961,962,963,964,965,963,962,965,
        965,964,966,967,967,965,966,967,968,968,967,965,967,967,966,968,
        967,966,965,964]*2])
            }

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
                    "text": instance.name,
                    "secondary_text": instance.patient.first_name + " " + instance.patient.last_name,
                    "tertiary_text": f"Expediente no.: {instance.patient.record}",
                    "icon": MDApp.get_running_app().icons.get(instance.patient.sex),
                    "screen": "ekg_detail_view",
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

class ExamMetadataForm(MDBoxLayout):
    data = DictProperty({})
    title = StringProperty("Title")

    def populate(self, patient_id):
        app_session = MDApp.get_running_app().session
        self.title = "Datos complementarios"
        
        try:
            self.patient = app_session.query(ldb.Patient).filter(ldb.Patient.id == patient_id).one()
            self.ids.info.text = f"{self.patient.first_name} {self.patient.last_name}"
            self.ids.info.icon = MDApp.get_running_app().icons.get(self.patient.sex[0])
            self.data['patient_id'] = patient_id
            self.ids.spo2.text = ""
            self.ids.weight_pd.text = ""
            self.ids.pressure.text = ""
        except sqlalchemy.orm.exc.NoResultFound as e:
            logging.error(e)
            toast('Hubo un error al buscar el paciente.')

    def save(self):
        self.data["spo2"] = float(self.ids.spo2.text)
        self.data["weight_pd"] = float(self.ids.weight_pd.text)
        self.data["pressure"] = self.ids.pressure.text
        return self.data
    
class ExamMetadataDetail(MDBoxLayout):
    exam = ObjectProperty(ldb.Exam())
    title = StringProperty("Title")
    note = StringProperty("")

    def populate(self, exam_id):
        app_session = MDApp.get_running_app().session
        self.title = "Detalles"
        try:
            self.exam = app_session.query(ldb.Exam).filter(ldb.Exam.id == exam_id).one()
            return self.exam.ekg_id
        except sqlalchemy.orm.exc.NoResultFound as e:
            logging.error(e)
            toast('Hubo un error al buscar el examen.')
    
    def on_exam(self, instance, value):

        def exam_status_text_mapper():
            if value.status == "GUARDADO":
                return value.status + "\n" + value.created.strftime("%d-%m-%Y")
            if value.status == "ENVIADO":
                return value.status + "\n" + value.sent.strftime("%d-%m-%Y")
            if value.status == "DIAGNOSTICADO":
                return value.status + "\n" + value.diagnosed.strftime("%d-%m-%Y")
        
        def exam_satus_color_mapper():
            if value.status == "GUARDADO":
                return [0.7, 0.05, 0.05, 1]
            if value.status == "ENVIADO":
                return [0.05, 0.05, 0.7, 1]
            if value.status == "DIAGNOSTICADO":
                return [0.05, 0.7, 0.05, 1]
            
        logging.warning(f"Exam ID: {value.id}")
        self.ids.info.icon = MDApp.get_running_app().icons.get(value.patient.sex)
        self.ids.info.text = "Nombre: " + value.patient.first_name + " " + value.patient.last_name + "\n" + "Edad: " + str(value.patient.age()) + " años"
        self.ids.spo2.text = f"{value.spo2} %"
        self.ids.weight_pd.text = f"{value.weight_pd} lbs"
        self.ids.pressure.text = value.pressure
        self.ids.bpm.text = str(value.ekg.bpm) + " bpm"
        self.ids.sample_rate.text = str(value.ekg.sample_rate) + " sps"
        self.ids.gain.text = str(value.ekg.gain)
        self.ids.status.text = exam_status_text_mapper()
        self.ids.status.text_color = exam_satus_color_mapper() 
        
class OKDevicePanel(MDBoxLayout):
    title = StringProperty("Title")
    sample_rate = StringProperty("T. de muestreo: ")
    leads = StringProperty("Derivaciones: ")
    battery = StringProperty("Batería: ")
    status = StringProperty("Desconectado")
    button_color = ColorProperty("blue")
    button_text = StringProperty("CONECTAR")

    def set_status(self):
        if self.status == "Desconectado":
            self.status = "Conectando..."
        elif self.status == "Conectando...":
            self.status = "Conectado"
        elif self.status == "Conectado":
            self.status = "Transmitiendo"
        elif self.status == "Transmitiendo":
            self.status = "Desconectado"

    def set_button_status(self):
        if self.status == "Desconectado" or self.status == "Conectando...": 
            self.button_text = "CONECTAR"
            self.button_color = "blue"
        elif self.status == "Conectado":
            self.button_text = "EMPEZAR"
            self.button_color = "green"
        elif self.status == "Transmitiendo":
            self.button_text = "DETENER"
            self.button_color = "red"