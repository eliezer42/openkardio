from kivy.properties import BooleanProperty, StringProperty, NumericProperty, ObjectProperty
from kivymd.uix.list import ThreeLineIconListItem, TwoLineIconListItem, ThreeLineAvatarIconListItem
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.relativelayout import MDRelativeLayout
from kivymd.uix.textfield import MDTextField
from kivy.animation import Animation
from kivymd.uix.selectioncontrol import MDCheckbox
from kivymd.app import MDApp

class OKIconItem(MDBoxLayout):
    icon = StringProperty("alert")
    text = StringProperty('alert')

class OKListItem(ThreeLineAvatarIconListItem):
    avatar = StringProperty("")
    icon = StringProperty("alert")
    screen = StringProperty()
    object_id = NumericProperty()
    propagate = BooleanProperty()

class OKSelectorItem(TwoLineIconListItem):
    icon = StringProperty("alert")
    screen = StringProperty()
    object_id = NumericProperty()
    propagate = BooleanProperty(False)

class OKHospitalSelectorItem(TwoLineIconListItem):
    global_id = StringProperty("")

class OKCommentWidget(MDBoxLayout):
    hint = StringProperty("")

class OKIdTextField(MDRelativeLayout):
    hint_text = StringProperty()
    disabled = BooleanProperty(True)


class OKModeControl(MDRelativeLayout):

    def populate(self):
        widget = self.ids[str(MDApp.get_running_app().store['app']['mode'])]
        widget.active = True
    
    def on_checkbox_active(self, checkbox, value):
        if value:
            MDApp.get_running_app().store['app'] = {'mode':checkbox.value}

class ModeCheck(MDCheckbox):
    value = StringProperty("")

class OKDeviceControl(MDRelativeLayout):
    
    def populate(self):
        widget = self.ids[str(MDApp.get_running_app().store['device']['duration'])]
        widget.active = True

    def on_checkbox_active(self, checkbox, value):
        if value:
            MDApp.get_running_app().store['device'] = {'duration':int(checkbox.value)}

class DurationCheck(MDCheckbox):
    value = StringProperty("")

class OKFilterControl(MDRelativeLayout):
    
    def populate(self):
        widget = self.ids[str(MDApp.get_running_app().store['filter']['state'])]
        widget.active = True

    def on_checkbox_active(self, checkbox, value):
        if value:
            MDApp.get_running_app().store['filter'] = {'state':checkbox.value}

class FilterCheck(MDCheckbox):
    value = StringProperty("on")