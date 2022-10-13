import logging
import asyncio
import array
import utils.remotedb as rdb
import utils.localdb as ldb
import utils.ble as ble
from os.path import join, dirname, realpath
from kivy.config import Config
from kivy.logger import Logger
from kivy.lang import Builder
from kivymd.app import MDApp
from kivymd.theming import ThemeManager
from kivymd.uix.menu import MDDropdownMenu
from kivymd.toast import toast
from plyer import notification
from plyer.utils import platform
from navdrawer import ItemDrawer

Config.set('modules','showborder','')
logging.Logger.manager.root = Logger

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
                                            'assets/plyer-icon.png')
                notification.notify(**kwargs)
            elif platform == 'linux':
                print("***NOTIFICATION***")
                print(kwargs)
        except Exception as e:
            logging.warning(e)

    def create_obj(self):
        obj_str = rdb.create_random_object()
        self.root.ids.out.text = obj_str

    def build(self):
        logging.basicConfig(format='%(asctime)s %(message)s')
        self.session = ldb.Session()
        return Builder.load_file("main.kv")

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