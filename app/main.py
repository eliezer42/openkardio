import logging
import asyncio
import array
import utils.remotedb as rdb
import utils.localdb as ldb
import utils.ble as ble
from datetime import date, datetime
from os.path import join, dirname, realpath
from kivy.logger import Logger
from kivy.lang import Builder
from kivy.storage.jsonstore import JsonStore
from kivy.metrics import dp
from kivymd.app import MDApp
from kivymd.theming import ThemeManager
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.toast import toast
from plyer import notification
from plyer.utils import platform
from navdrawer import ItemDrawer
from okwidgets import OKHospitalSelectorItem, OKCommentWidget
from sqlalchemy.exc import SQLAlchemyError

logging.Logger.manager.root = Logger

class OpenKardioApp(MDApp):
    title = "OpenKardio"
    theme_cls = ThemeManager()
    icons = {'M': 'face-man', 'F': 'face-woman'}
    dialog = None
    user_id = "CS1"

    def __init__(self):
        super().__init__()
        self.ble = ble.BleHandler(self.frame_handler)
        self.running = True

    def build(self):
        logging.basicConfig(format='%(asctime)s %(message)s')
        self.theme_cls.material_style = "M3"
        self.store = JsonStore("okconfig.json")
        if __name__ == '__main__':
            self.store["app"] = {"mode":"CS"}
            self.store["user"] = {"id":"CS1"}
            return Builder.load_file("main.kv")
        
    def on_start(self):
        self.user_id = self.store["user"]["id"]
        self.session = ldb.Session()
        if self.session.query(ldb.Patient).first() is None:
                self.populate_hospitals()
                patient1 = ldb.Patient(first_name="Pedro", last_name="Perez", sex="M", birth_date=date(1998, 3, 28), record="123-456-789")
                patient2 = ldb.Patient(first_name="Maria", last_name="Lopez", sex="F", birth_date=date(1970, 12, 13), record="123-456-789")
                self.session.add_all([patient1, patient2])
                self.session.commit()
        self.retrieve_own_cases()
        self.root.ids.patient_form.sex_menu = MDDropdownMenu(caller = self.root.ids.patient_form.ids.sex,
                                                             width_mult = 3,
                                                             items = [{"viewclass": "OneLineListItem",
                                                                       "text": i,
                                                                       "height": dp(56),
                                                                       "on_release": lambda x=i: self.root.ids.patient_form.set_sex(x)} for i in ["Femenino", "Masculino"]])

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

    def go_to(self, target):
        self.root.ids.screen_manager.current = target
        self.root.ids.screen_manager.transition.direction = "left"
    
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
    
    def retrieve_own_cases(self):
        try:
            exam_query = self.session.query(ldb.Exam.remote_id).filter(ldb.Exam.remote_id != "")
            exam_remote_ids = [exam.remote_id for exam in exam_query]
            logging.debug(exam_remote_ids)
            for case in rdb.retrieve_objects("Cases","origin_id",self.store["user"]["id"]):
                case_dict = case.to_dict()
                if case.id in exam_remote_ids:
                    local_exam = self.session.query(ldb.Exam).filter(ldb.Exam.remote_id == case.id).one()
                    if datetime.fromisoformat(case_dict['modified']) > local_exam.modified:
                        timestamp = datetime.now().replace(microsecond=0)
                        logging.debug(f"REMOTE:{case_dict['modified']}")
                        local_exam.diagnostic = case_dict["diagnostic"]
                        local_exam.status = "DIAGNOSTICADO"
                        local_exam.modified = timestamp
                        local_exam.diagnosed = timestamp
                        self.session.commit()
                logging.info(case_dict["created"])
        except SQLAlchemyError as e:
            logging.error(e)
            toast("Error en la base de datos local.")
            self.session.rollback()
        except Exception as e:
            logging.error(e)
            toast("Error desconocido")
            self.session.rollback()

    def populate_hospitals(self):
        try:
            for hospital in rdb.retrieve_all_objects("Hospitals"):
                logging.debug(hospital.id)
                if self.session.query(ldb.Hospital).filter(ldb.Hospital.global_id == hospital.id).first() is None:
                    hosp_data = hospital.to_dict()
                    hosp_data["global_id"] = hospital.id
                    new_hosp = ldb.Hospital(**hosp_data)
                    self.session.add(new_hosp)
                    self.session.commit()
        except SQLAlchemyError as e:
            logging.error(e)
            toast("Error en la base de datos local.")
        except Exception as e:
            logging.error(e)
            toast(e)

    def show_comment_dialog(self):

        self.dialog = MDDialog(
            title="Comentario",
            type="custom",
            content_cls=OKCommentWidget(hint="Agregue un comentario"),
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
        try:
            timestamp = datetime.now().replace(microsecond=0)
            metadata = self.root.ids.new_exam_metadata.save()
            ekg = self.root.ids.new_ekg.get_ekg()
            new_ekg = ldb.Ekg(**ekg)
            self.session.add(new_ekg)
            self.session.commit()
            logging.info("EKG ID:" + str(new_ekg.id))
            exam_data = {
                'name':'EKG-' + date.today().strftime("%Y%m%d") + '-' + str(new_ekg.id),
                'ekg_id':new_ekg.id,
                'created':timestamp,
                'modified':timestamp,
                'origin_id':self.user_id,
                'notes':notes,
            }
            exam_data.update(metadata)
            new_exam = ldb.Exam(**exam_data)
            self.session.add(new_exam)
            self.session.commit()
            self.root.ids.screen_manager.get_screen("ekg_detail_view").object_id = new_exam.id
            self.root.ids.screen_manager.get_screen("ekg_detail_view").title = new_exam.name
            self.root.ids.screen_manager.current = "ekg_detail_view"
            self.dialog.dismiss()
        except Exception as e:
            logging.error(e)
            self.session.rollback()

    def send_exam(self, exam_id):
        exam = self.session.query(ldb.Exam).filter(ldb.Exam.id == exam_id).one()
        
        def send_to_firestore(global_id:str):
            remote_exam_id = None
            try:
                logging.info('Sending case')
                timestamp = datetime.now().replace(microsecond=0)
                remote_exam_id = rdb.create_object({
                    'exam_id':exam.id,
                    'origin_id':exam.origin_id,
                    'status':"ENVIADO",
                    'destination_id':global_id,
                    'created':exam.created.isoformat(),
                    'modified':timestamp.isoformat(),
                    'sent':timestamp.isoformat(),
                    'diagnosed':'',
                    'patient_name':exam.patient.name(),
                    'patient_age':exam.patient.age(),
                    'patient_identification':exam.patient.identification,
                    'patient_record':exam.patient.record,
                    'pressure':exam.pressure,
                    'spo2':exam.spo2,
                    'weight_pd':exam.weight_pd,
                    'sample_rate':exam.ekg.sample_rate,
                    'bpm':exam.ekg.bpm,
                    'leads':exam.ekg.leads,
                    'signal':exam.ekg.signal,
                    'notes':exam.notes,
                    'diagnostic':exam.diagnostic
                },
                "Cases")
                exam.status = "ENVIADO"
                exam.sent = timestamp
                exam.modified = timestamp
                exam.remote_id = remote_exam_id
                self.session.commit()
                logging.info(f"Remote ID: {remote_exam_id}")
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
                logging.debug(remote_id)
                logging.debug(exam_id)
                self.root.ids.exam_metadata.populate(exam_id)
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
                OKHospitalSelectorItem(text=item.name, secondary_text=item.location, on_release=lambda _: send_callback(item.global_id)) for item in self.session.query(ldb.Hospital).order_by(ldb.Hospital.name)
            ]
        )
        self.dialog.open()

    def delete_patient(self, patient_id):
        
        def delete_from_db():
            obj = self.session.query(ldb.Patient).get(patient_id)
            try:
                self.session.delete(obj)
                self.session.commit()
                logging.info(f"Patient {patient_id} deleted successfully.")
            except SQLAlchemyError as e:
                self.session.rollback()
                logging.error(e)
        
        def delete_callback():
            delete_from_db()
            self.dialog.dismiss()
            self.go_back("patient_list_view")
        
        self.dialog = MDDialog(
            text="¿Estás seguro(a) que deseas borrar este paciente?",
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

    def delete_exam(self, exam_id):
        
        def delete_from_db():
            obj = self.session.query(ldb.Exam).get(exam_id)
            try:
                self.session.delete(obj)
                self.session.commit()
                logging.info(f"Exam {exam_id} deleted successfully.")
            except SQLAlchemyError as e:
                self.session.rollback()
                logging.error(e)

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

    

async def main(app):
    await asyncio.gather(app.async_run("asyncio"), app.ble.connection_handler())

if __name__ == "__main__":
    Logger.setLevel(logging.DEBUG)
    # app running on one thread with two async coroutines
    app = OpenKardioApp()
    asyncio.run(main(app))