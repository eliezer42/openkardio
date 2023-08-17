import asyncio
import array
import json
from kivy.logger import Logger
import logging
import utils.remotedb as rdb
import utils.localdb as ldb
import utils.ble as ble
from kivymd.app import MDApp
from datetime import date, datetime
from kivy.lang import Builder
from kivy.storage.jsonstore import JsonStore
from kivy.metrics import dp
from kivymd.theming import ThemeManager
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.toast import toast
from navdrawer import ItemDrawer
from okwidgets import OKHospitalSelectorItem, OKCommentWidget
from sqlalchemy.exc import SQLAlchemyError
from kivy.core.window import Window
from kivy.utils import platform
from kivy.clock import Clock
from os.path import join

if platform != 'android':
    Window.size = (800, 800)
    Window.minimum_width, Window.minimum_height = Window.size

logging.Logger.manager.root = Logger

class OpenKardioApp(MDApp):
    title = "OpenKardio"
    theme_cls = ThemeManager()
    icons = {'M': 'face-man', 'F': 'face-woman'}
    dialog = None

    def __init__(self):
        super().__init__()
        self.ble = ble.BleHandler(frame_handler=self.frame_handler)
        self.running = True

    def build(self):
        logging.basicConfig(format='%(asctime)s %(message)s')
        self.theme_cls.material_style = "M3"
        
        if __name__ == '__main__':
            data_dir = getattr(self, 'user_data_dir')
            Logger.info(f"DATADIR: {data_dir}")
            try:    
                self.store = JsonStore(join(data_dir,'config.json'))
                self.user_id = self.store["user"]["id"]
            except KeyError as e:
                Logger.critical(e)
                config_data = {
                    "app": {"mode": "C"},
                    "user": {"id": "CS1"},
                    "device": {"duration": 10},
                    "filter": {"state":"on"}
                }
                with open(join(data_dir,'config.json'), 'w') as config_file:
                    json.dump(config_data, config_file)
            finally:
                self.store = JsonStore(join(data_dir,'config.json'))
                self.user_id = self.store["user"]["id"]
                

            return Builder.load_file("main.kv")
        
    def on_start(self):
        self.session = ldb.session_init(getattr(self, 'user_data_dir'))
        if self.session.query(ldb.Patient).first() is None:
                patient1 = ldb.Patient(first_name="Pedro", last_name="Perez", sex="M", birth_date=date(1998, 3, 28), record="123-456-789", identification="123")
                patient2 = ldb.Patient(first_name="Maria", last_name="Lopez", sex="F", birth_date=date(1970, 12, 13), record="123-456-789", identification="321")
                self.session.add_all([patient1, patient2])
                self.session.commit()
        self.root.ids.patient_form.sex_menu = MDDropdownMenu(caller = self.root.ids.patient_form.ids.sex,
                                                             width_mult = 3,
                                                             items = [{"viewclass": "OneLineListItem",
                                                                       "text": i,
                                                                       "height": dp(50),
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
        self.populate_start()

        Clock.schedule_once(lambda dt: self.populate_hospitals(), 5)


    def on_stop(self):
        self.running = False
        self.session.close()

    def ble_disconnect(self):
        self.ble.transition(ble.ConnState.IDLE)

    def frame_handler(self, sender, data):
        
        Logger.info("SENDER: {0}: {1} [{2} bytes]".format(sender, data, len(data)))
        if len(data) == 1:
            self.ble.toggle_reception()
            Logger.error(f"Frame: Error while receiving frame. Error code={data}")
            toast("Ocurrió un error desconocido")
        else:
            try:
                samples = array.array('h', data).tolist()
                self.root.ids.new_ekg.next_samples = samples
                if len(self.root.ids.new_ekg.ekg_samples) >= self.ble.sample_rate*9.6:
                        Logger.info("RIGHT BEFORE TOGGLE RECEPTION")
                        self.ble.transition(ble.ConnState.CONNECTED)
            except Exception as e:
                Logger.error(f"Frame: Error while decoding frame.")
                Logger.error(f"Frame: {e}")
                self.ble.toggle_reception()

    def go_back(self, previous):
        self.root.ids.screen_manager.current = previous
        self.root.ids.screen_manager.transition.direction = "right"

    def go_to(self, target):
        self.root.ids.screen_manager.current = target
        self.root.ids.screen_manager.transition.direction = "left"

    def mark_exam_as_opened(self, id):
        self.session.query(ldb.Exam).filter(ldb.Exam.id == id).update({ldb.Exam.unopened: False})
        self.session.commit()

    def populate_hospitals(self):
        try:
            hospitals = rdb.retrieve_all_objects("Hospitals")
            for gid in hospitals:
                if self.session.query(ldb.Hospital).filter(ldb.Hospital.global_id == gid).first() is None:
                    hosp_data = hospitals[gid]
                    hosp_data["global_id"] = gid
                    new_hosp = ldb.Hospital(**hosp_data)
                    self.session.add(new_hosp)
                    self.session.commit()
                    Logger.info(f"Hospital ID: {new_hosp.id}")

        except SQLAlchemyError as e:
            Logger.error(e)
            toast("Error en la base de datos local.")
        except rdb.RDBException as e:
            Logger.error(f"RDB:{str(e)}")
            toast(str(e))
        except Exception as e:
            Logger.error(f"Hospitals:{str(e)}")
            toast("Error desconocido.")

    def upsert_local_cases(self):
        try:
            sent_exams = self.session.query(ldb.Exam.remote_id).filter(ldb.Exam.remote_id != "")
            sent_exam_remote_ids = [exam.remote_id for exam in sent_exams]
            remote_cases = rdb.retrieve_objects("Cases","origin_id",self.store["user"]["id"])
            Logger.debug(f"Remote ID:{str(sent_exam_remote_ids)}")
            for oid in remote_cases:
                case_dict = remote_cases[oid]
                if oid in sent_exam_remote_ids:
                    local_exam = self.session.query(ldb.Exam).filter(ldb.Exam.remote_id == oid).one()
                    if datetime.fromisoformat(case_dict['modified']) > local_exam.modified:
                        timestamp = datetime.now().replace(microsecond=0)
                        Logger.debug(f"REMOTE:{case_dict['modified']}")
                        local_exam.diagnostic = case_dict["diagnostic"]
                        local_exam.status = case_dict['status']
                        local_exam.modified = timestamp
                        local_exam.diagnosed = timestamp
                        local_exam.unopened = True
                        self.session.commit()
                else:
                    

                    ekg = {
                        "bpm":int(case_dict.get('bpm')),
                        "sample_rate":int(case_dict.get('sample_rate')),
                        "gain":float(case_dict.get('gain')),
                        "signal":bytes(case_dict.get('signal'))
                    }
                    new_ekg = ldb.Ekg(**ekg)
                    self.session.add(new_ekg)
                    self.session.commit()
                    local_patients = self.session.query(ldb.Patient.identification).filter(ldb.Patient.identification != "")
                    patient_ids = [patient.identification for patient in local_patients]
                    if case_dict['patient_identification'] not in patient_ids:
                        patient = {
                            "first_name":case_dict.get('patient_first_name'),
                            "last_name":case_dict.get('patient_last_name'),
                            "birth_date":datetime.fromisoformat(case_dict.get('patient_birth_date')),
                            "sex":case_dict.get('patient_sex'),
                            "identification":case_dict.get('patient_identification'),
                            "record":case_dict.get('patient_record')
                        }
                        new_patient = ldb.Patient(**patient)
                        self.session.add(new_patient)
                        self.session.commit()
                    exam_data = {
                        'remote_id':oid,
                        'name':'EKG-' + datetime.fromisoformat(case_dict.get('created')).strftime('%Y%m%d') + '-' + str(new_ekg.id),
                        'ekg_id':new_ekg.id,
                        'created':datetime.fromisoformat(case_dict.get('created')),
                        'sent':datetime.fromisoformat(case_dict.get('sent')),
                        'modified':datetime.fromisoformat(case_dict.get('modified')),
                        'origin_id':self.store['user']['id'],
                        'destination_id':case_dict.get('destination_id'),
                        'spo2':float(case_dict.get('spo2')),
                        'weight_pd':float(case_dict.get('weight_pd')),
                        'pressure':case_dict.get('pressure'),
                        'notes':case_dict.get('notes'),
                        'status':case_dict.get('status'),
                        'patient_id':self.session.query(ldb.Patient.id).filter(ldb.Patient.identification==case_dict['patient_identification']).one()[0]
                    }
                    if case_dict.get('status') == 'EVALUADO':
                        exam_data.update(
                            {
                                'diagnosed':datetime.fromisoformat(case_dict.get('diagnosed')),
                                'diagnostic':case_dict.get('diagnostic')
                            }
                        )
                    new_exam = ldb.Exam(**exam_data)
                    self.session.add(new_exam)
                    self.session.commit()
                    # self.root.ids.screen_manager.get_screen("ekg_detail_view").object_id = new_exam.id
                    # self.root.ids.screen_manager.get_screen("ekg_detail_view").title = new_exam.name
                    # self.root.ids.screen_manager.current = "ekg_detail_view"

        except SQLAlchemyError as e:
            Logger.error(e)
            toast("Error en la base de datos local.")

        except rdb.RDBException as e:
            Logger.error(e)
            toast(str(e))

        except Exception as e:
            Logger.error(e)
            toast("Error desconocido")
            
        finally:
            self.session.rollback()
    
    def retrieve_foreign_cases(self):
        try:
 
            exam_query = self.session.query(ldb.Exam.remote_id).filter(ldb.Exam.remote_id != "")
            exam_remote_ids = [exam.remote_id for exam in exam_query]
            Logger.debug(f"Remote IDs:{str(exam_remote_ids)}")
            remote_cases = rdb.retrieve_objects("Cases","destination_id",self.store["user"]["id"])
            for gid in remote_cases:
                data = remote_cases[gid]
                if gid not in exam_remote_ids:
                    patient_query = self.session.query(ldb.Patient.identification).filter(ldb.Patient.identification != "")
                    patient_ids = [patient.identification for patient in patient_query]
                    if data.get('patient_identification') not in patient_ids:
                        patient = ldb.Patient(
                            first_name = data.get('patient_first_name'),
                            last_name = data.get('patient_last_name'),
                            birth_date = datetime.strptime(data.get('patient_birth_date'),'%d-%m-%Y').date(),
                            sex = data.get('patient_sex'),
                            identification = data.get('patient_identification'),
                            record = data.get('patient_record')
                        )
                        self.session.add(patient)
                        self.session.commit()
                    else:
                        patient = self.session.query(ldb.Patient.id).filter(ldb.Patient.identification == data.get('patient_identification')).one()
                    ekg = ldb.Ekg(
                        sample_rate = data.get('sample_rate'),
                        bpm = data.get('bpm'),
                        leads = data.get('leads'),
                        signal = bytes(data.get('signal')),
                        gain = data.get('gain')
                        )
                    self.session.add(ekg)
                    self.session.commit()
                    exam = ldb.Exam(
                        name = 'EKG-' + data.get('created')[:10].replace('-','') + '-' + str(ekg.id),
                        origin_id = data.get('origin_id'),
                        remote_id = gid,
                        status = data.get('status'),
                        pressure = data.get('pressure'),
                        spo2 = data.get('spo2'),
                        weight_pd = data.get('weight_pd'),
                        destination_id = data.get('destination_id'),
                        created = datetime.fromisoformat(data.get('created')),
                        modified = datetime.fromisoformat(data.get('modified')),
                        sent = datetime.fromisoformat(data.get('sent')),
                        notes = data.get('notes'),
                        ekg_id = ekg.id,
                        patient_id = patient.id
                    )

                    self.session.add(exam)
                    self.session.commit()

        except SQLAlchemyError as e:
            Logger.error(e)
            toast("Error en la base de datos local.")

        except rdb.RDBException as e:
            Logger.error(e)
            toast(str(e))

        except Exception as e:
            Logger.error(e)
            toast("Error desconocido")
            
        finally:
            self.session.rollback()

    def download_cases(self):
        if self.store['app']['mode'] == 'C':
            self.upsert_local_cases()
        elif self.store['app']['mode'] == 'H':
            self.retrieve_foreign_cases()
        self.root.ids.pending.badge_icon = self.root.ids.exam_pending_list.populate("",False,False)
        self.root.ids.done.badge_icon = self.root.ids.exam_done_list.populate("",False,True)
          
    def save_exam(self):
        try:
            timestamp = datetime.now().replace(microsecond=0)
            metadata = self.root.ids.new_exam_metadata.save()
            ekg = self.root.ids.new_ekg.get_ekg()
            new_ekg = ldb.Ekg(**ekg)
            self.session.add(new_ekg)
            self.session.commit()
            exam_data = {
                'name':'EKG-' + date.today().strftime("%Y%m%d") + '-' + str(new_ekg.id),
                'ekg_id':new_ekg.id,
                'created':timestamp,
                'modified':timestamp,
                'origin_id':self.store['user']['id']
            }
            exam_data.update(metadata)
            new_exam = ldb.Exam(**exam_data)
            self.session.add(new_exam)
            self.session.commit()
            Logger.info("Commited Ekg")
            self.root.ids.screen_manager.get_screen("ekg_detail_view").object_id = new_exam.id
            self.root.ids.screen_manager.get_screen("ekg_detail_view").title = new_exam.name
            self.root.ids.screen_manager.current = "ekg_detail_view"
        except Exception as e:
            Logger.error(e)
            self.session.rollback()

    def send_exam(self, exam_id:ldb.Exam):
            
        exam = self.session.query(ldb.Exam).filter(ldb.Exam.id == exam_id).one()

        def send_diagnostic(diagnostic:str):
            try:
                timestamp = datetime.now().replace(microsecond=0)
                updated_case = {'diagnostic':diagnostic,
                                'diagnosed':timestamp.isoformat(),
                                'modified':timestamp.isoformat(),
                                'status':'EVALUADO'
                                }
                rdb.update_object('Cases',exam.remote_id,updated_case)
                updated_case['diagnosed'] = timestamp
                updated_case['modified'] = timestamp
                for key, value in updated_case.items():
                    setattr(exam, key, value)
                self.session.commit()
                self.root.ids.exam_metadata.populate(exam_id)

            except SQLAlchemyError as e:
                Logger.error(e)
                toast("Error en la base de datos.")

            except rdb.RDBException as e:
                Logger.error(e)
                toast(str(e))
            
            except Exception as e:
                toast("Error desconocido")
                Logger.error(f"Exam:{e}")

            finally:
                self.session.rollback()
                self.dialog.dismiss()

        def send_to_firebase(global_id:str):
            Logger.debug(f"Global ID: {global_id}")
            try:
                timestamp = datetime.now().replace(microsecond=0)
                remote_exam_id = rdb.create_object("Cases",
                    {
                        'exam_id':exam.id,
                        'origin_id':exam.origin_id,
                        'status':"ENVIADO",
                        'destination_id':global_id,
                        'created':exam.created.isoformat(),
                        'modified':timestamp.isoformat(),
                        'sent':timestamp.isoformat(),
                        'diagnosed':'',
                        'patient_first_name':exam.patient.first_name,
                        'patient_last_name':exam.patient.last_name,
                        'patient_birth_date':exam.patient.birth_date.strftime('%d-%m-%Y'),
                        'patient_identification':exam.patient.identification,
                        'patient_record':exam.patient.record,
                        'patient_sex':exam.patient.sex,
                        'pressure':exam.pressure,
                        'spo2':exam.spo2,
                        'weight_pd':exam.weight_pd,
                        'sample_rate':exam.ekg.sample_rate,
                        'bpm':exam.ekg.bpm,
                        'leads':exam.ekg.leads,
                        'gain':exam.ekg.gain,
                        'signal':list(exam.ekg.signal),
                        'notes':exam.notes,
                        'diagnostic':exam.diagnostic
                    }
                )
                exam.status = "ENVIADO"
                exam.sent = timestamp
                exam.modified = timestamp
                exam.remote_id = remote_exam_id
                self.session.commit()
                return remote_exam_id

            except SQLAlchemyError as e:
                Logger.error(f"SQL Error: {e}")

            except rdb.RDBException as e:
                Logger.error(e)
                toast(str(e))

            except Exception as e:
                Logger.error(e)
                toast("Error desconocido.")
            
            finally:
                self.session.rollback()

        def send_callback(global_id):
            remote_id = send_to_firebase(global_id)
            if remote_id is not None:
                self.dialog.dismiss()
                self.root.ids.screen_manager.get_screen("ekg_detail_view").title = exam.name
                exam.destination_id = global_id
                self.session.commit()
                self.root.ids.exam_metadata.populate(exam_id)
                Logger.debug(f"Remote ID:{remote_id}")
                return
            self.dialog.dismiss()
            

        if "GUARDADO" != exam.status and self.store['app']['mode'] == 'C':
            toast(f"Este examen ya fue enviado.")
            return
        
        if self.store['app']['mode'] != 'H':
            hosp_list = self.session.query(ldb.Hospital).order_by(ldb.Hospital.name).all()
            Logger.critical([hosp.global_id for hosp in hosp_list])
            self.dialog = MDDialog(
                title="Hospital de destino",
                type="simple",
                items=[
                    OKHospitalSelectorItem(text=item.name, secondary_text=item.location, global_id=item.global_id, on_release=lambda x: send_callback(x.global_id)) for item in hosp_list
                ]
            )
        else:
            self.dialog = MDDialog(
                title="Diagnóstico",
                type="custom",
                content_cls=OKCommentWidget(hint="Agregue su diagnóstico"),
                buttons=[
                    MDFlatButton(
                        text="CANCELAR",
                        on_release=lambda _: self.dialog.dismiss()
                    ),
                    MDRaisedButton(
                        text="GUARDAR",
                        on_release=lambda _: send_diagnostic(self.dialog.content_cls.ids.text_field.text)
                    )
                ]
            )
        self.dialog.open()

    def delete_patient(self, patient_id):
        
        def delete_from_db():
            obj = self.session.query(ldb.Patient).get(patient_id)
            try:
                self.session.delete(obj)
                self.session.commit()
                Logger.info(f"Patient {patient_id} deleted successfully.")
            except SQLAlchemyError as e:
                self.session.rollback()
                Logger.error(e)
        
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
                Logger.info(f"Exam {exam_id} deleted successfully.")
            except SQLAlchemyError as e:
                self.session.rollback()
                Logger.error(e)

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
    
    def populate_start(self):
        unopened_exams = self.session.query(ldb.Exam).filter(ldb.Exam.unopened == True).count()
        info_msg = f"Usted está registrado como {self.store['user']['id']}. Tiene {unopened_exams} exámen(es) sin abrir."
        self.root.ids["info"].text = info_msg
        exam_count = self.session.query(ldb.Exam).count()
        patient_count = self.session.query(ldb.Patient).count()
        self.root.ids["start_exams"].count = exam_count
        self.root.ids["start_patients"].count = patient_count
        self.root.ids["start_exams"].clear()
        if self.store['app']['mode'] == 'C':
            self.root.ids["start_exams"]\
                .add_bar("GUARDADO","#d35f5f",self.session.query(ldb.Exam)\
                .filter(ldb.Exam.status == "GUARDADO")\
                .count()/max(exam_count,1))
            self.root.ids["start_exams"]\
                .add_bar("ENVIADO","#5f99d3",self.session.query(ldb.Exam)\
                .filter(ldb.Exam.status == "ENVIADO")\
                .count()/max(exam_count,1))
            self.root.ids["start_exams"]\
                .add_bar("EVALUADO","#5fd399",self.session.query(ldb.Exam)\
                .filter(ldb.Exam.status == "EVALUADO")\
                .count()/max(exam_count,1))
        else:
            self.root.ids["start_exams"]\
                .add_bar("RECIBIDO","#5f99d3",self.session.query(ldb.Exam)\
                .filter(ldb.Exam.status == "ENVIADO")\
                .count()/max(exam_count,1))
            self.root.ids["start_exams"]\
                .add_bar("EVALUADO","#5fd399",self.session.query(ldb.Exam)\
                .filter(ldb.Exam.status == "EVALUADO")\
                .count()/max(exam_count,1))

        self.root.ids["start_patients"].clear()
        self.root.ids["start_patients"].add_bar("FEMENINO","#d35f5f",self.session.query(ldb.Patient).filter(ldb.Patient.sex == "F").count()/max(patient_count,1))
        self.root.ids["start_patients"].add_bar("MASCULINO","#5f99d3",self.session.query(ldb.Patient).filter(ldb.Patient.sex == "M").count()/max(patient_count,1))

async def main(app):
    await asyncio.gather(app.async_run("asyncio"), app.ble.connection_handler())

if __name__ == "__main__":
    Logger.setLevel(logging.DEBUG)
    # app running on one thread with two async coroutines
    app = OpenKardioApp()
    asyncio.run(main(app))