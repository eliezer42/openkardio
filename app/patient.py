
import utils.remotedb as rdb
import utils.localdb as ldb
import sqlalchemy
import logging
from datetime import date
from oklistitem import OKListItem
from kivy.properties import StringProperty, ObjectProperty, BooleanProperty
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.list import MDList
from kivymd.uix.textfield import MDTextField
from kivymd.uix.pickers import MDDatePicker
from kivymd.uix.card import MDCard
from kivymd.uix.behaviors import RectangularElevationBehavior
from kivymd.toast import toast

class PatientList(MDList):
    sex_icons = {'M': 'face-man', 'F': 'face-woman'}

    def populate(self, *args):
        self.clear_widgets()
        app_session = MDApp.get_running_app().session
        for instance in app_session.query(ldb.Patient).order_by(ldb.Patient.id):
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
    patient = ObjectProperty(ldb.Patient())
    sex_icon = StringProperty("face")

    def populate(self, patient_id):
        app_session = MDApp.get_running_app().session
        try:
            self.patient = app_session.query(ldb.Patient).filter(ldb.Patient.id == patient_id).one()
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
        new_patient = ldb.Patient(**patient_data)
        app_session = MDApp.get_running_app().session
        app_session.add(new_patient)
        app_session.commit()
        logging.warning('New Patient ID is %s', new_patient.id)
        return new_patient.id