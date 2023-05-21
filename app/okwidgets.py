from kivy.properties import BooleanProperty, StringProperty, NumericProperty, ObjectProperty
from kivymd.uix.list import ThreeLineIconListItem, TwoLineIconListItem
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.textfield import MDTextField

class OKIconItem(MDBoxLayout):
    icon = StringProperty("alert")
    text = StringProperty('alert')

class OKListItem(ThreeLineIconListItem):
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
    pass

class OKCommentWidget(MDBoxLayout):
    hint = StringProperty("")