from kivy.logger import Logger
from sqlalchemy.exc import SQLAlchemyError
import utils.localdb as ldb
import utils.ble as ble
import numpy as np
import utils.utils as utils
from kivy.uix.widget import Widget
from kivy.core.text import Label as CoreLabel
from kivy.graphics import Color, Line, Rectangle
from kivy.properties import DictProperty, StringProperty, ListProperty, ObjectProperty, BooleanProperty, NumericProperty, ColorProperty
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.toast import toast
from kivy.metrics import dp
from kivy.utils import platform
import zlib
import array

class Plot(Widget):
    sample_rate = NumericProperty(480)
    top_of_scale = NumericProperty(26400)
    gain = NumericProperty(1)
    run_samples = BooleanProperty(False)
    ekg_samples = ListProperty([])
    next_samples = ListProperty([])
    bpm = NumericProperty(0)
    MARGINS = dp(16)
    GRID_SUBDIVS = 5
    SEC_PER_SUBDIV = 0.04
    MV_PER_SUBDIV = 0.1
    SEC_PER_DIV = GRID_SUBDIVS*SEC_PER_SUBDIV
    MV_PER_DIV = GRID_SUBDIVS*MV_PER_SUBDIV
    GRID_SUBDIV_LINE_WIDTH = 0.5
    GRID_DIV_LINE_WIDTH = 1.2
    app = MDApp.get_running_app()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Clock.schedule_interval(self.update_plot,1/60.0)
        self.time_generator = utils.time_gen(self.sample_rate)
        self.peaks = []
        with self.canvas.after:
            Color(0, 0, 0, 1)
            self.preamble = Line(points=[], width = 1.25 if platform == 'android' else 1)
            self.line = Line(points=[], width = 1.25 if platform == 'android' else 1)

    def on_sample_rate(self, instance, value):
        self.time_generator = utils.time_gen(self.sample_rate)

    def on_size(self,*args):
        try:
            self.grid_y_divs = 6

            self.y_subdiv_count = self.grid_y_divs*self.GRID_SUBDIVS
            self.subdiv_size = int((self.height - self.MARGINS)//(self.y_subdiv_count))
            self.div_size = self.subdiv_size*self.GRID_SUBDIVS

            self.grid_height = self.div_size*self.grid_y_divs
            self.grid_y_offset = (self.height - self.grid_height)/2
            self.grid_y = self.y + self.grid_y_offset
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
        self.width = max((len(self.ekg_samples)*self.subdiv_size/(self.sample_rate*self.SEC_PER_SUBDIV))+8*self.MARGINS, self.parent.width)

    def on_next_samples(self, *args):
        if len(self.next_samples):
            if len(self.preamble.points) == 0:
                pre_points = [float(point) for sample in range(193) for point in [self.grid_x + next(self.time_generator)*self.subdiv_size/self.SEC_PER_SUBDIV,
                                                self.grid_y_offset + np.interp(13200 if (sample <= 38 or sample > 96) else 19780,[0,self.top_of_scale],[0,self.grid_height])]]
                pre_points += [self.grid_x + next(self.time_generator)*self.subdiv_size/self.SEC_PER_SUBDIV,self.grid_y_offset + np.interp(13200,[0,self.top_of_scale],[0,self.grid_height])]
                self.preamble.points = pre_points
                self.line.points = pre_points

            next_points = [float(point) for sample in self.next_samples for point in [self.grid_x + next(self.time_generator)*self.subdiv_size/self.SEC_PER_SUBDIV,
                                                self.grid_y_offset + np.interp(sample/self.gain,[-(self.grid_y_divs*self.MV_PER_DIV)/2,(self.grid_y_divs*self.MV_PER_DIV)/2],[0,self.grid_height])]]
            
            if len(self.line.points) <= 2*4632: #max points per line
                self.line.points += next_points
            
            self.ekg_samples.extend(self.next_samples)
            self.next_samples = []

            if self.peaks:

                for peak in self.peaks:
                    x_peak = self.preamble.points[-2] + (peak/self.sample_rate)*self.subdiv_size/self.SEC_PER_SUBDIV
                    mylabel = CoreLabel(text=f"{int(400.0+peak*1000/self.sample_rate)} ms", font_size=dp(10), color=(0, 0, 0, 1))
                    mylabel.refresh()
                    texture = mylabel.texture
                    texture_size = list(texture.size)
                    with self.canvas:
                        Color(0.1,0.1,0.1,0.2)
                        Line(points=[x_peak,self.grid_y,x_peak,self.y_subdiv_count*self.subdiv_size + self.grid_y], width=2)
                        Color(0.1,0.1,0.1,1)
                        Rectangle(texture=texture, size=texture_size, pos=[x_peak,0])

                self.peaks = []
 
    def plot_grid(self, *args):
        mylabel = CoreLabel(text="0.2 s/div - 0.5 mV/div", font_size=dp(10), color=(0, 0, 0, 1))
        # Force refresh to compute things and generate the texture
        mylabel.refresh()
        # Get the texture and the texture size
        texture = mylabel.texture
        texture_size = list(texture.size)
        with self.canvas.before:
            Color(rgba=[1.0, 0.85, 0.85, 1])
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
                Rectangle(texture=texture, size=texture_size, pos=[self.grid_x,0])
            except AttributeError:
                pass

    def reset(self):
        self.canvas.clear()
        self.ekg_samples = []
        self.next_samples = []
        self.line.points = []
        self.preamble.points = []
        self.time_generator = utils.time_gen(self.sample_rate)
        self.plot_grid()

    def populate(self, ekg_id):
        self.reset()
        try:
            ekg = self.app.session.query(ldb.Ekg).filter(ldb.Ekg.id == ekg_id).one()
            self.sample_rate = ekg.sample_rate
            self.gain = ekg.gain
            signal = array.array('h',zlib.decompress(ekg.signal)).tolist()
            self.peaks = utils.christov_detector(signal,self.sample_rate)
            self.next_samples = signal
        except Exception as e:
            Logger.error(e)

    def get_ekg(self):
        if len(self.ekg_samples):
            Logger.info(f"EKG: {len(self.ekg_samples)} samples")
            return {
                'bpm': round(60/np.average(np.diff(utils.christov_detector(np.array(self.ekg_samples),self.sample_rate))/self.sample_rate)),
                'sample_rate': self.sample_rate,
                'gain': self.app.ble.conv_factor,
                'rpeaks': bytes(array.array('I',utils.christov_detector(self.ekg_samples,self.sample_rate))),
                'signal': zlib.compress(bytearray(array.array('h',list(self.ekg_samples)[:int(self.sample_rate*9.6)])))
            }
        return {
                'bpm': round(60/np.average(np.diff(utils.christov_detector(np.array([item*16 for item in
        utils.single_pulse*10])-936,self.sample_rate))/self.sample_rate)),
                'sample_rate': self.sample_rate,
                'gain': 8800,
                'rpeaks': bytes(array.array('I',utils.christov_detector([(item-936)*16 for item in 
        utils.single_pulse*10],self.sample_rate))),
                'signal': zlib.compress(bytearray(array.array('h',[(item-936)*16 for item in 
        utils.single_pulse*10])))
            }

class ExamList(MDBoxLayout):
    def populate(self, text="", search=False, diagnosed=False):
        '''Builds a list of icons for the screen MDIcons.'''

        def add_item(instance):
            self.ids.rv.data.append(
                {
                    "viewclass": "OKListItem",
                    "object_id": instance.id,
                    "text": instance.name,
                    "secondary_text": instance.patient.first_name + " " + instance.patient.last_name,
                    "tertiary_text": f"Global ID: {instance.remote_id}",
                    "avatar": "new-box" if instance.unopened else "",
                    "icon": "clipboard-pulse",
                    "screen": "ekg_detail_view",
                    "propagate": True
                }
            )

        self.ids.rv.data = []
        app = MDApp.get_running_app()
        field = ldb.Exam.destination_id if (app.store['app']['mode'] == 'H') else ldb.Exam.origin_id
        status_list = ["EVALUADO"] if diagnosed else ["GUARDADO","ENVIADO"]
        query = app.session.query(ldb.Exam)\
            .filter(field == app.store['user']['id'])\
            .filter(ldb.Exam.status.in_(status_list))\
            .order_by(-ldb.Exam.id)
        avatar = ""
        for instance in query:
            if search:
                if text.lower() in instance.patient.first_name.lower() or\
                    text.lower() in instance.patient.last_name.lower() or\
                    text.lower() in instance.patient.record.lower() or \
                    text.lower() in str(instance.remote_id):
                    add_item(instance)
            else:
                add_item(instance)
            if instance.unopened:
                avatar = "circle-small"
        return avatar
    
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
            self.ids.notes.text = ""
        except SQLAlchemyError as e:
            Logger.error(e)
            toast('Hubo un error al buscar el paciente.')

    def save(self):
        self.data["spo2"] = (lambda s: 0.0 if s == "" else (float(s) if s.replace('.', '', 1).isdigit() else None))(self.ids.spo2.text)
        self.data["weight_pd"] = (lambda s: 0.0 if s == "" else (float(s) if s.replace('.', '', 1).isdigit() else None))(self.ids.weight_pd.text)
        self.data["pressure"] = (lambda s: "--/--" if s == "" else (s if all(part.isdigit() for part in s.split('/')) else None))(self.ids.pressure.text)
        self.data["notes"] = self.ids.notes.text
        return self.data
    
class ExamMetadataDetail(MDBoxLayout):
    exam = ObjectProperty(ldb.Exam())
    title = StringProperty("Detalles")
    notes = StringProperty("")
    diagnostic = StringProperty("")


    def populate(self, exam_id):
        
        def exam_status_text_mapper():
            if self.exam.status == "GUARDADO":
                return self.exam.status + "\n" + self.exam.created.strftime("%d-%m-%Y")
            if self.exam.status == "ENVIADO":
                return self.exam.status + "\n" + self.exam.sent.strftime("%d-%m-%Y")
            if self.exam.status == "EVALUADO":
                return self.exam.status + "\n" + self.exam.diagnosed.strftime("%d-%m-%Y")
        
        def exam_satus_color_mapper():
            if self.exam.status == "GUARDADO":
                return [0.7, 0.05, 0.05, 1]
            if self.exam.status == "ENVIADO":
                return [0.05, 0.05, 0.7, 1]
            if self.exam.status == "EVALUADO":
                return [0.05, 0.7, 0.05, 1]

        try:
            Logger.debug(f"Local ID:{exam_id}")
            app = MDApp.get_running_app()
            self.exam = app.session.query(ldb.Exam).filter(ldb.Exam.id == exam_id).one()
            self.ids.info.icon = MDApp.get_running_app().icons.get(self.exam.patient.sex)
            self.ids.info.text = self.exam.patient.first_name + " " + self.exam.patient.last_name + "\n" + str(self.exam.patient.age()) + " años"
            self.ids.spo2.text = f"{self.exam.spo2} %"
            self.ids.weight_pd.text = f"{self.exam.weight_pd} lbs"
            self.ids.pressure.text = self.exam.pressure
            self.ids.bpm.text = str(self.exam.ekg.bpm) + " bpm"
            self.ids.sample_rate.text = str(self.exam.ekg.sample_rate) + " sps"
            self.ids.leads.text = str(self.exam.ekg.leads) + " leads"
            self.ids.status.text = exam_status_text_mapper()
            self.ids.status.text_color = exam_satus_color_mapper()
            app.root.ids.comment_label.text = f"Comentarios:\n[{self.exam.origin_id}]"
            app.root.ids.notes.text = self.exam.notes
            app.root.ids.diagnosis_label.text = f"Diagnóstico:\n[{self.exam.destination_id}]"
            app.root.ids.diagnostic.text = self.exam.diagnostic
            return self.exam.ekg_id
        except SQLAlchemyError as e:
            Logger.error(e)
            toast('Hubo un error al buscar el examen.')
        except Exception as e:
            Logger.critical(e)
            toast("Error desconocido")

class OKDevicePanel(MDBoxLayout):
    title = StringProperty("Title")
    sample_rate = NumericProperty(0)
    leads = NumericProperty(0)
    battery = NumericProperty(0)
    resolution = NumericProperty(0)
    fw_version = StringProperty("")
    button_color = ColorProperty("blue")
    button_text = StringProperty("CONECTAR")
    ble_state = ObjectProperty()
    status = StringProperty("Desconectado")
    duration = NumericProperty(10)
    app = MDApp.get_running_app()

    def set_state(self):
        if self.app.ble.state == ble.ConnState.IDLE:
            self.app.ble.transition(ble.ConnState.SCANNING)
        elif self.app.ble.state == ble.ConnState.SCANNING:
            pass
        elif self.app.ble.state == ble.ConnState.CONNECTED:
            self.app.ble.transition(ble.ConnState.RECEIVING)
        elif self.app.ble.state == ble.ConnState.RECEIVING:
            self.app.ble.transition(ble.ConnState.CONNECTED)

    def on_ble_state(self, instance, value):
        Logger.info(f"OKDevice: {self.ble_state}")
        if value == ble.ConnState.IDLE:
            self.button_text = "CONECTAR"
            self.button_color = "blue"
            self.status = "Desconectado"
        elif value == ble.ConnState.SCANNING:
            self.status = "Escaneando..."
        elif value == ble.ConnState.CONNECTED:
            self.button_text = "EMPEZAR"
            self.button_color = "green"
            self.status = "Conectado"
        elif value == ble.ConnState.RECEIVING:
            self.button_text = "DETENER"
            self.button_color = "red"
            self.status = "Transmitiendo"

    def on_sample_rate(self, instance, value):
        self.ids.sample_rate.text = str(value) + " sps"
    
    def on_leads(self, instance, value):
        self.ids.leads.text = str(value) + " leads"

    def on_battery(self, instance, value):
        self.ids.battery.text = str(value) + " %"
    
    def on_resolution(self, instance, value):
        self.ids.resolution.text = str(value) + " bits"

    def on_fw_version(self, instance, value):
        self.ids.fwv.text = "v" + value