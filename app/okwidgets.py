from kivy.properties import BooleanProperty, StringProperty, NumericProperty
from kivymd.uix.list import ThreeLineIconListItem, TwoLineIconListItem
from kivymd.uix.card import MDCard
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.behaviors import RectangularElevationBehavior

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

class OKCard(MDCard, RectangularElevationBehavior):
    title = StringProperty("Title")

    def add_widget(self, *args, **kwargs):
        if 'container' in self.ids:
            return self.ids.container.add_widget(*args, **kwargs)
        else:
            return super().add_widget(*args, **kwargs)