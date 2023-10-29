import time
import requests
from kivy.logger import Logger
from google.oauth2 import service_account
from google.auth.transport.requests import Request

# Define the required scopes
scopes = [
  "https://www.googleapis.com/auth/userinfo.email",
  "https://www.googleapis.com/auth/firebase.database"
]

base_url = 'https://openkardio-6586d-default-rtdb.firebaseio.com'

# Authenticate a credential with the service account
credentials = service_account.Credentials.from_service_account_file(
    "openkardio-6586d-firebase-adminsdk-432xd-1c800391f7.json", scopes=scopes)
session = requests.Session()
session.timeout = (3, 3)
request = Request(session)

token_init = False

def get_token():
    global token_init
    try:
        if credentials.expired or not token_init:
            credentials.refresh(request)
            token_init = True
        return credentials.token
    except Exception as e:
        Logger.error(f"Timeout: {str(e)}")


class RDBException(Exception):
    pass

def new_obj_id() -> str:
    return str(round(time.time() * 1000))

def create_object(obj_class:str,obj:dict) -> str:
    
    obj_id = new_obj_id()
    
    conn_token = get_token()
    if conn_token:
        r = requests.put(f'{base_url}/{obj_class}/{obj_id}.json?access_token={conn_token}',json=obj)

        if r.status_code != 200:
            raise RDBException('Creating object of type [{0}] failed. Error: {1}'.format(obj_class,r.json()["error"]))
    
        return obj_id
    
    raise RDBException('Error: Sin conexión a Internet')


def update_object(obj_class:str, obj_id:str, obj_data:dict):
    
    conn_token = get_token()
    if conn_token:
        r = requests.patch(f'{base_url}/{obj_class}/{obj_id}.json?access_token={conn_token}',json=obj_data)
        
        if r.status_code != 200:
            raise RDBException('Updating object of type [{0}] failed. Error: {1}'.format(obj_class,r.json()["error"]))
        
        return
    
    raise RDBException('Error: Sin conexión a Internet')


def retrieve_object(obj_class:str,obj_id:str) -> dict:

    conn_token = get_token()
    if conn_token:
        r = requests.get(f'{base_url}/{obj_class}/{obj_id}.json?access_token={conn_token}')

        if r.status_code != 200:
            raise RDBException('Fetching object of type [{0}] failed. Error: {1}'.format(obj_class,r.json()["error"]))
        
        return r.json()

    raise RDBException('Error: Sin conexión a Internet')


def retrieve_objects(obj_class:str, field:str, value):

    conn_token = get_token()
    if conn_token:
        if type(value) is str:
            r = requests.get(f'{base_url}/{obj_class}.json?orderBy="{field}"&equalTo="{value}"&access_token={conn_token}')
        else:
            r = requests.get(f'{base_url}/{obj_class}.json?orderBy="{field}"&equalTo={value}&access_token={conn_token}')

        if r.status_code != 200:
            print(r.reason)
            raise RDBException('Fetching object of type [{0}] failed. Error: {1}'.format(obj_class,r.json()["error"]))
        
        return r.json()
    
    raise RDBException('Error: Sin conexión a Internet')

def retrieve_all_objects(obj_class:str):

    conn_token = get_token()
    if conn_token:
        r = requests.get(f'{base_url}/{obj_class}.json?access_token={conn_token}')

        if r.status_code != 200:
            raise RDBException('Fetching object of type [{0}] failed. Error: {1}'.format(obj_class,r.json()["error"]))
        
        return r.json()
    
    raise RDBException('Error: Sin conexión a Internet')


def retrieve_all_ids(obj_class:str):
    conn_token = get_token()
    if conn_token:
        r = requests.get(f'{base_url}/{obj_class}.json?shallow=true&access_token={conn_token}')

        if r.status_code != 200:
            raise RDBException('Fetching object of type [{0}] failed. Error: {1}'.format(obj_class,r.json()["error"]))
        
        return r.json()
    
    raise RDBException('Error: Sin conexión a Internet')


def delete_object(obj_class:str,obj_id) -> bool:
    conn_token = get_token()
    if conn_token:
        r = requests.delete(f'{base_url}/{obj_class}/{obj_id}.json?access_token={conn_token}')

        if r.status_code != 200:
            raise RDBException('Fetching object of type [{0}] failed. Error: {1}'.format(obj_class,r.json()["error"]))
        
        return
    
    raise RDBException('Error: Sin conexión a Internet')
