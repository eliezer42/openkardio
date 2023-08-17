import utils.localdb as ldb
from kivy.logger import Logger
from datetime import datetime
from kivy.properties import StringProperty, ObjectProperty, BooleanProperty
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.textfield import MDTextField
from kivymd.toast import toast
from sqlalchemy.exc import SQLAlchemyError

class PatientList(MDBoxLayout):
    def populate(self, text="", search=False):
        '''Builds a list of icons for the screen MDIcons.'''

        def add_item(instance):
            self.ids.rv.data.append(
                {
                    "viewclass": "OKListItem",
                    "object_id": instance.id,
                    "text": instance.first_name + " " + instance.last_name,
                    "secondary_text": f"Expediente no.: {instance.record}",
                    "tertiary_text": f"Edad: {instance.age()} años",
                    "avatar":"",
                    "icon": "face-man" if instance.sex == "M" else "face-woman",
                    "screen": "patient_detail_view",
                    "propagate": True
                }
            )

        self.ids.rv.data = []
        app_session = MDApp.get_running_app().session
        for instance in app_session.query(ldb.Patient).order_by(ldb.Patient.id):
            if search:
                if text in instance.first_name or text in instance.last_name or text in instance.record:
                    add_item(instance)
            else:
                add_item(instance)

class PatientDetail(MDBoxLayout):
    patient = ObjectProperty(ldb.Patient())
    sex_icon = StringProperty("face-man")

    def populate(self, patient_id):
        app_session = MDApp.get_running_app().session
        try:
            self.patient = app_session.query(ldb.Patient).get(patient_id)
            self.sex_icon = "face-woman" if self.patient.sex == 'F' else "face-man"
            self.ids.name.text = "Nombres: " + self.patient.first_name + "\n" + "Apellidos: " + self.patient.last_name
            self.ids.age.text = "Edad: " + str(self.patient.age()) + " años"
            self.ids.identification.text = "Cédula: " + self.patient.identification
            self.ids.record.text = "Expediente: " + self.patient.record
            self.ids.address.text = "Domicilio: " + self.patient.address
            self.ids.contact.text = "Contacto de emergencia: "  + self.patient.emergency_contact
        except SQLAlchemyError as e:
            Logger.error(e)
            toast('Hubo un error al buscar el paciente.')



class FormField(MDBoxLayout):
    label = StringProperty()
    text = StringProperty()
    error = BooleanProperty(False)
    value = ObjectProperty()

class PatientForm(MDBoxLayout):
    sex_menu = ObjectProperty()
    date_dialog = ObjectProperty()
    editing = BooleanProperty()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def set_sex(self, dropdown_item_text):
        self.ids.sex.text = dropdown_item_text
        self.sex_menu.dismiss()
    
    def on_save(self, instance, value, date_range):
        self.ids.birth_date.text = value.strftime("%d/%m/%Y")
        self.ids.birth_date.value = value

    def clear_fields(self):
        for widget in self.children:
            if isinstance(widget, MDTextField):
                widget.text = ''

    def populate_fields(self, patient_id):
        pass

    def save_form(self):
        patient_data = {}
        Logger.debug("Date:" + self.ids.birth_date.text)
        self.ids.birth_date.value = datetime.strptime(self.ids.birth_date.text,"%d/%m/%Y").date()
        for field in self.ids.keys():
            patient_data[field] = self.ids[field].value
        new_patient = ldb.Patient(**patient_data)
        app_session = MDApp.get_running_app().session
        app_session.add(new_patient)
        app_session.commit()
        Logger.warning('New Patient ID is %s', new_patient.id)
        return new_patient.id