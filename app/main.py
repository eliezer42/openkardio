import logging
import asyncio
import array
from venv import create
import utils.remotedb as rdb
import utils.localdb as ldb
import utils.ble as ble
from datetime import date
from os.path import join, dirname, realpath
from kivy.config import Config
Config.set('modules','showborder','')
from kivy.logger import Logger
from kivy.lang import Builder
from kivy import __version__ as kivy_version
from kivymd import __version__ as kivymd_version
from kivy.storage.jsonstore import JsonStore
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget
from kivymd.app import MDApp
from kivymd.theming import ThemeManager
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.list import OneLineListItem
from kivymd.toast import toast
from plyer import notification
from plyer.utils import platform
from navdrawer import ItemDrawer
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from okwidgets import OKHospitalSelectorItem, OKCommentWidget
from kivymd.uix.textfield import MDTextField
from sqlalchemy.exc import SQLAlchemyError

logging.Logger.manager.root = Logger

class OpenKardioApp(MDApp):
    title = "OpenKardio"
    theme_cls = ThemeManager()
    icons = {'M': 'face-man', 'F': 'face-woman'}
    dialog = None

    def __init__(self):
        super().__init__()
        self.ble = ble.BleHandler(self.frame_handler)
        self.running = True

    def build(self):
        logging.basicConfig(format='%(asctime)s %(message)s')
        self.theme_cls.material_style = "M3"
        self.session = ldb.Session()
        self.store = JsonStore("okconfig.json")
        if __name__ == '__main__':
            if self.session.query(ldb.Patient).first() is None:
                self.store["app"] = {"mode":"CS"}
                self.store["user"] = {"id":"CS1"}
                patient1 = ldb.Patient(first_name="Pedro", last_name="Perez", sex="M", birth_date=date(1998, 3, 28), record="123-456-789")
                patient2 = ldb.Patient(first_name="Juanita", last_name="Lopez", sex="F", birth_date=date(1970, 12, 13), record="123-456-789")
                self.session.add_all([patient1, patient2])
                self.session.commit()
                hosp1 = ldb.HealthCenter(name = "Hospital Regional Cesar Amador Molina", location="Matagalpa")
                hosp2 = ldb.HealthCenter(name = "Hospital Escuela Oscar Danilo Rosales", location="León")
                self.session.add_all([hosp1, hosp2])
                self.session.commit()
            return Builder.load_file("main.kv")

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
                                            'assets/plyer-icon.png')
                notification.notify(**kwargs)
            elif platform == 'linux':
                print("***NOTIFICATION***")
                print(kwargs)
        except SQLAlchemyError as e:
            logging.warning(e)
    
    def retrieve_cases():
        pass

    def show_comment_dialog(self):

        self.dialog = MDDialog(
            title="Comentario",
            type="custom",
            content_cls=OKCommentWidget(hint="Agregue comentarios"),
            buttons=[
                MDFlatButton(
                    text="CANCELAR",
                    on_release=lambda _: self.dialog.dismiss()
                ),
                MDRaisedButton(
                    text="GUARDAR",
                    on_release=lambda _: self.save_exam(self.dialog.content_cls.ids.text_field.text)
                )
            ]
        )
        self.dialog.open()
         
    
    def save_exam(self, notes:str):
        logging.debug(notes)
        try:
            metadata = self.root.ids.new_exam_metadata.save()
            ekg = self.root.ids.new_ekg.get_ekg()
            new_ekg = ldb.Ekg(**ekg)
            self.session.add(new_ekg)
            self.session.commit()
            exam_data = {
                'name':'EKG-' + date.today().strftime("%Y%m%d") + '-' + str(new_ekg.id),
                'ekg_id':new_ekg.id,
                'created':date.today(),
                'origin_id':'CS1',
                'notes':notes,
            }
            exam_data.update(metadata)
            new_exam = ldb.Exam(**exam_data)
            self.session.add(new_exam)
            self.session.commit()
            logging.info(new_exam)
            self.root.ids.origin_note.text = new_exam.notes
            self.root.ids.screen_manager.get_screen("ekg_detail_view").object_id = new_exam.id
            self.root.ids.screen_manager.current = "ekg_detail_view"
            self.dialog.dismiss()
        except Exception as e:
            logging.exception(f'Something happened in python!\n{e}')
            self.session.rollback()

    def send_exam(self, exam_id):
        exam = self.session.query(ldb.Exam).filter(ldb.Exam.id == exam_id).one()
        
        def send_to_firestore(global_id:str):
            remote_exam_id = None
            try:
                logging.info('Sending case')
                remote_exam_id = rdb.create_object({
                    'origin_id':exam.origin_id,
                    'origin_exam_id':exam.id,
                    'destination_id':global_id,
                    'created':exam.created.strftime("%Y-%m-%d"),
                    'sent':date.today().strftime("%Y-%m-%d"),
                    'diagnosed':'',
                    'patient_name': exam.patient.name(),
                    'patient_age': exam.patient.age(),
                    'pressure': exam.pressure,
                    'spo2':exam.spo2,
                    'weight_pd':exam.weight_pd,
                    'sample_rate':exam.ekg.sample_rate,
                    'bpm':exam.ekg.bpm,
                    'leads':1,
                    'signal':exam.ekg.signal,
                    'notes':exam.notes,
                    'diagnostic':exam.diagnostic
                },
                "test1")
                exam.status = "ENVIADO"
                exam.sent = date.today()
                self.session.commit()
                logging.info(f"Sent with id: {remote_exam_id}")
            except SQLAlchemyError as e1:
                self.session.rollback()
                logging.error(f"SQL Error: {e1}")
            except Exception as e:
                self.session.rollback()
                logging.error(e)
            return remote_exam_id

        def send_callback(global_id:str):
            remote_id = send_to_firestore(global_id=global_id)
            if remote_id is not None:
                self.dialog.dismiss()
                self.root.ids.screen_manager.get_screen("ekg_detail_view").title = exam.name
                self.root.ids.exam_metadata_detail.populate(exam_id)
                logging.info("FINISHED CALLBACK")
                return
            toast("Algo salió mal.")
            self.dialog.dismiss()
            

        if "GUARDADO" != exam.status:
            toast(f"Este examen ya fue enviado.")
            return

        self.dialog = MDDialog(
            title="Hospital de destino",
            type="simple",
            items=[
                OKHospitalSelectorItem(text=item.name, secondary_text=item.location, on_release=lambda _: send_callback(item.global_id)) for item in self.session.query(ldb.HealthCenter).order_by(ldb.HealthCenter.name)
            ]
        )
        self.dialog.open()

    
    def delete_exam(self, exam_id):
        
        def delete_from_db():
            obj = self.session.query(ldb.Exam).get(exam_id)
            try:
                self.session.delete(obj)
                self.session.commit()
                logging.info(f"Exam {exam_id} deleted successfully.")
            except SQLAlchemyError as e:
                self.session.rollback()
                logging.exception(f'Something happened in python!\n{e}')

        def delete_callback():
            delete_from_db()
            self.dialog.dismiss()
            self.go_back("ekg_list_view")
        
        self.dialog = MDDialog(
            text="¿Estás seguro(a) que deseas borrar este examen?",
            buttons=[
                MDFlatButton(
                    text="CANCELAR",
                    on_release= lambda _: self.dialog.dismiss()
                ),
                MDRaisedButton(
                    text="ACEPTAR",
                    on_release= lambda _: delete_callback()
                ),
            ],
        )
        self.dialog.open()

    def on_start(self):
        sex_list = ["Femenino", "Masculino"]
        self.root.ids.patient_form.sex_menu = MDDropdownMenu(caller = self.root.ids.patient_form.ids.sex, 
                                        width_mult = 3, 
                                        items = [{"viewclass": "OneLineListItem",
                                                    "text": i,
                                                    "on_release": lambda x=i: self.root.ids.patient_form.set_sex(x)} for i in sex_list])
        drawer_items = {
            "home": {"text": "Inicio", "target": "homescreen"},
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
        self.session.close()
    
    def pop_packages(self):
        self.root.ids.pkg_list.add_widget(
            OneLineListItem(text=f"kivymd_version: {kivymd_version}")
        )
        self.root.ids.pkg_list.add_widget(
            OneLineListItem(text=f"kivy_version: {kivy_version}")
        )

async def main(app):
    await asyncio.gather(app.async_run("asyncio"), app.ble.connection_handler())

if __name__ == "__main__":
    Logger.setLevel(logging.DEBUG)
    # app running on one thread with two async coroutines
    app = OpenKardioApp()
    asyncio.run(main(app))