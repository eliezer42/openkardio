import logging
from kivy.utils import platform
from array import array

if platform == 'android':

    from jnius import autoclass, cast

    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    currentActivity = cast('android.app.Activity', PythonActivity.mActivity)
    context = cast('android.content.Context', currentActivity.getApplicationContext())
    FirebaseApp = autoclass('com.google.firebase.FirebaseApp')
    FirebaseFirestore = autoclass('com.google.firebase.firestore.FirebaseFirestore')
    Blob = autoclass('com.google.firebase.firestore.Blob')
    HashMap = autoclass('java.util.HashMap')

    app = FirebaseApp.initializeApp(context)
    db = FirebaseFirestore.getInstance()

else:
    import firebase_admin
    from firebase_admin import credentials
    from firebase_admin import firestore

    # Use a service account.
    cred = credentials.Certificate('./openkardio-6586d-firebase-adminsdk-432xd-1c800391f7.json')

    # Application Default credentials are automatically created.
    app = firebase_admin.initialize_app(cred)
    db = firestore.client()

def create_object(objDict, collection):
    logging.info('Creating...')
    doc_ref = db.collection(collection).document()

    if platform != 'android':
        doc_ref.set(objDict)
        logging.info('Created')
        return doc_ref.id
    objMap = HashMap()
    logging.info(type(objMap))
    for k, v in objDict.items():
        if k == "signal":
            objMap.put(k,Blob.fromBytes(v))
            continue
        objMap.put(k, v)
    doc_ref.set(objMap)
    logging.info('Created')
    return doc_ref.id

def update_object(objDict, collection, id):
    logging.info('Updating...')
