from kivy.utils import platform
import json
from faker import Faker
fake = Faker()
if platform == 'android':

    from jnius import autoclass, cast

    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    currentActivity = cast('android.app.Activity', PythonActivity.mActivity)
    context = cast('android.content.Context', currentActivity.getApplicationContext())
    FirebaseApp = autoclass('com.google.firebase.FirebaseApp')
    FirebaseFirestore = autoclass('com.google.firebase.firestore.FirebaseFirestore')
    HashMap = autoclass('java.util.HashMap')

    app = FirebaseApp.initializeApp(context)
    db = FirebaseFirestore.getInstance()

else:
    import firebase_admin
    from firebase_admin import credentials
    from firebase_admin import firestore

    # Use a service account.
    cred = credentials.Certificate('./openkardio-6586d-firebase-adminsdk-432xd-27b7ffe590.json')
    # Application Default credentials are automatically created.
    app = firebase_admin.initialize_app(cred)
    db = firestore.client()

def create_random_object():
    print('Creating...')
    doc_ref = db.collection(u'test1').document()
    objDict = {"name": fake.first_name(), "color":fake.color_name() , "age": fake.pyint(max_value=99)}
    if platform == 'android':
        objMap = HashMap()
        for k, v in objDict.items():
            objMap.put(k, v)
        doc_ref.set(objMap)
    else:
        doc_ref.set(objDict)
    return doc_ref.id