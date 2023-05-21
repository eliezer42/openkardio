from kivy.properties import StringProperty, ListProperty, NumericProperty
from kivymd.uix.screen import MDScreen

class ToolbarScreen(MDScreen):
    title = StringProperty()
    action_items = ListProperty([])
    right_items = ListProperty([])
    object_id = NumericProperty(0)

    def add_widget(self, *args, **kwargs):
        if 'container' in self.ids:
            return self.ids.container.add_widget(*args, **kwargs)
        else:
            return super().add_widget(*args, **kwargs)