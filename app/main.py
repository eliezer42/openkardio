import firestore
from os.path import join, dirname, realpath
from datetime import date
from kivy.lang import Builder
from kivy.properties import StringProperty, ListProperty, ObjectProperty, BooleanProperty, NumericProperty
from kivy.uix.widget import Widget
from kivy.clock import Clock
from kivy.graphics import Color, Line, Rectangle
from kivy.metrics import dp
from kivy.config import Config
Config.set('modules','showborder','')
from kivymd.theming import ThemeManager
from kivymd.app import MDApp
from kivymd.theming import ThemableBehavior
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.list import OneLineIconListItem, MDList, ThreeLineIconListItem
from kivymd.uix.screen import MDScreen
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.pickers import MDDatePicker
from kivymd.uix.menu import MDDropdownMenu
from kivymd.toast import toast
from kivymd.uix.behaviors import RectangularElevationBehavior
from kivymd.uix.card import MDCard
import utils
import numpy as np
import array
import openkardio as ok
import sqlalchemy
import pickle
from kivy.logger import Logger
import logging
logging.Logger.manager.root = Logger
import asyncio
from plyer import notification
from plyer.utils import platform
import ble

class NotificationDemo(MDBoxLayout):
    pass

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
    action_items = ListProperty([])
    object_id = NumericProperty(0)

    def add_widget(self, *args, **kwargs):
        if 'container' in self.ids:
            return self.ids.container.add_widget(*args, **kwargs)
        else:
            return super().add_widget(*args, **kwargs)

class OKListItem(ThreeLineIconListItem):
    icon = StringProperty("alert")
    screen = StringProperty()
    object_id = NumericProperty()

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
    sex_icons = {'M': 'face', 'F': 'face-woman'}

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

class PatientList(MDList):
    sex_icons = {'M': 'face', 'F': 'face-woman'}

    def populate(self, *args):
        self.clear_widgets()
        app_session = MDApp.get_running_app().session
        for instance in app_session.query(ok.Patient).order_by(ok.Patient.id):
            self.add_widget(
                OKListItem(
                    object_id = instance.id,
                    text=f"{instance.first_name} {instance.last_name}",
                    secondary_text= f"Expediente no.: {instance.record}",
                    tertiary_text= f"Sexo: {instance.sex}  Edad: {instance.age()} años",
                    icon = self.sex_icons[instance.sex],
                    screen = "patient_detail_view"
                )
            )

class PatientDetail(MDBoxLayout):
    patient = ObjectProperty(ok.Patient())
    sex_icon = StringProperty("face")

    def populate(self, patient_id):
        app_session = MDApp.get_running_app().session
        try:
            self.patient = app_session.query(ok.Patient).filter(ok.Patient.id == patient_id).one()
        except sqlalchemy.orm.exc.NoResultFound:
            toast('Hubo un error al buscar el paciente.')

    def on_patient(self, instance, value):
        logging.warning(value.id)
        self.sex_icon = "face-woman" if value.sex == 'F' else "face"
        self.ids.name.text = "Nombres: " + value.first_name + "\n" + "Apellidos: " + value.last_name
        self.ids.age.text = "Edad: " + str(value.age()) + " años"
        self.ids.identification.text = "Cédula: " + value.identification
        self.ids.record.text = "Expediente: " + value.record
        self.ids.address.text = "Domicilio: " + value.address
        self.ids.contact.text = "Contacto de emergencia: "  + value.emergency_contact

class OKCard(MDCard, RectangularElevationBehavior):
    pass

class FormField(MDBoxLayout):
    label = StringProperty()
    text = StringProperty()
    error = BooleanProperty(False)
    value = ObjectProperty()

class PatientForm(MDBoxLayout):
    header = StringProperty()
    sex_menu = ObjectProperty()
    date_dialog = ObjectProperty()
    editing = BooleanProperty()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.date_dialog = MDDatePicker(title="FECHA DE NAC")
        self.date_dialog.bind(on_save=self.on_save, on_cancel=self.on_cancel)

    def set_sex(self, dropdown_item_text):
        self.ids.sex.text = dropdown_item_text
    
    def on_save(self, instance, value, date_range):
        self.ids.birth_date.text = value.strftime("%d/%m/%Y")
        self.ids.birth_date.value = value

    def on_cancel(self, instance, value):
        self.date_dialog.close()

    def show_date_picker(self):
        if self.editing:
            date_to_show = date.today()
            self.date_dialog.day = date_to_show.day
            self.date_dialog.month = date_to_show.month
            self.date_dialog.year = date_to_show.year
        self.date_dialog.open()

    def clear_fields(self):
        for widget in self.children:
            if isinstance(widget, MDTextField):
                widget.text = ''

    def populate_fields(self, patient_id):
        pass

    def save_form(self):
        patient_data = {}
        for field in self.ids.keys():
            patient_data[field] = self.ids[field].value
        new_patient = ok.Patient(**patient_data)
        app_session = MDApp.get_running_app().session
        app_session.add(new_patient)
        app_session.commit()
        logging.warning('New Patient ID is %s', new_patient.id)
        return new_patient.id

class OpenKardioApp(MDApp):
    title = "OpenKardio"
    theme_cls = ThemeManager()

    def __init__(self):
        super().__init__()
        self.ble = ble.BleHandler(self.frame_handler)
        self.running = True
    
    def frame_handler(self, sender, data):
        """Simple notification handler which prints the data received."""
        logging.info("{0}: {1}".format(sender, data))
        if len(data) == 1:
            self.ble.stop_receiving()
            logging.error(f"Frame: Error while receiving frame.")
            toast("Ocurrió un error desconocido")
        else:
            try:
                samples = array.array('h', data).tolist()
                self.root.ids.new_ekg.next_samples = samples
            except Exception as e:
                logging.error(f"Frame: Error while decoding frame.")
                logging.error(f"Frame: {e}")

    def go_back(self, previous):
        self.root.ids.screen_manager.current = previous
        self.root.ids.screen_manager.transition.direction = "right"
    
    def do_notify(self):
        try:
            title = self.root.ids.demo.ids.notification_title.text
            message = self.root.ids.demo.ids.notification_text.text
            kwargs = {'title': title, 'message': message}
            if platform == 'android':
                kwargs['app_name'] = "OpenKardio"
                kwargs['app_icon'] = join(dirname(realpath(__file__)),
                                            'plyer-icon.png')
                notification.notify(**kwargs)
            elif platform == 'linux':
                print("***NOTIFICATION***")
                print(kwargs)
        except Exception as e:
            logging.warning(e)

    def create_obj(self):
        obj_str = firestore.create_random_object()
        self.root.ids.out.text = obj_str

    def build(self):
        logging.basicConfig(format='%(asctime)s %(message)s')
        self.session = ok.Session()
        return Builder.load_file("ok.kv")

    def on_start(self):
        sex_list = ["Femenino", "Masculino"]
        self.root.ids.patient_form.sex_menu = MDDropdownMenu(caller = self.root.ids.patient_form.ids.sex, 
                                        width_mult = 3, 
                                        items = [{"viewclass": "OneLineListItem",
                                                    "text": i,
                                                    "on_release": lambda x=i: self.root.ids.patient_form.set_sex(x)} for i in sex_list])
        drawer_items = {
            "home": {"text": "Inicio", "target": "homescreen"},
            "account": {"text": "Usuario", "target": "user_detail_view"},
            "heart-pulse": {"text": "Exámenes", "target": "ekg_list_view"},
            "folder-account": {"text": "Pacientes", "target": "patient_list_view"},
            "cog": {"text": "Configuración", "target": "config"},
            "help": {"text": "Ayuda", "target": "help"}
            }
        for item_name in drawer_items.keys():
            self.root.ids.content_drawer.ids.md_list.add_widget(
                ItemDrawer(icon=item_name, text=drawer_items[item_name]["text"], screen=drawer_items[item_name]["target"])
            )
        
    def on_stop(self):
        self.running = False

async def main(app):
    await asyncio.gather(app.async_run("asyncio"), app.ble.connection_handler())

if __name__ == "__main__":
    Logger.setLevel(logging.DEBUG)
    # app running on one thread with two async coroutines
    app = OpenKardioApp()
    asyncio.run(main(app))