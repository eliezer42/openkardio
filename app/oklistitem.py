from kivy.properties import StringProperty, NumericProperty
from kivymd.uix.list import OneLineIconListItem, MDList, ThreeLineIconListItem

class OKListItem(ThreeLineIconListItem):
    icon = StringProperty("alert")
    screen = StringProperty()
    object_id = NumericProperty()
