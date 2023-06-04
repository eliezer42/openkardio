import time
import requests
from kivy.logger import Logger

class RDBException(Exception):
    pass

def new_obj_id() -> str:
    return str(round(time.time() * 1000))

def create_object(obj_class:str,obj:dict) -> str:
    
    obj_id = new_obj_id()
    
    r = requests.put(f'https://openkardio-6586d-default-rtdb.firebaseio.com/{obj_class}/{obj_id}.json',json=obj)

    if r.status_code != 200:
        raise RDBException('Creating object of type [{0}] failed. Error: {1}'.format(obj_class,r.json()["error"]))
    
    return obj_id

def update_object(obj_class:str, obj_id:str, obj_data:dict):
    
    r = requests.patch(f'https://openkardio-6586d-default-rtdb.firebaseio.com/{obj_class}/{obj_id}.json',json=obj_data)
    Logger.info(f'URL: https://openkardio-6586d-default-rtdb.firebaseio.com/{obj_class}/{obj_id}.json')
    if r.status_code != 200:
        raise RDBException('Updating object of type [{0}] failed. Error: {1}'.format(obj_class,r.json()["error"]))


def retrieve_object(obj_class:str,obj_id:str) -> dict:
    
    r = requests.get(f'https://openkardio-6586d-default-rtdb.firebaseio.com/{obj_class}/{obj_id}.json')

    if r.status_code != 200:
        raise RDBException('Fetching object of type [{0}] failed. Error: {1}'.format(obj_class,r.json()["error"]))
    
    return r.json()


def retrieve_objects(obj_class:str, field:str, value):

    if type(value) is str:
        r = requests.get(f'https://openkardio-6586d-default-rtdb.firebaseio.com/{obj_class}.json?orderBy="{field}"&equalTo="{value}"')
    else:
        r = requests.get(f'https://openkardio-6586d-default-rtdb.firebaseio.com/{obj_class}.json?orderBy="{field}"&equalTo={value}')

    if r.status_code != 200:
        print(r.reason)
        raise RDBException('Fetching object of type [{0}] failed. Error: {1}'.format(obj_class,r.json()["error"]))
    
    return r.json()

def retrieve_all_objects(obj_class:str):
    
    r = requests.get(f'https://openkardio-6586d-default-rtdb.firebaseio.com/{obj_class}.json')

    if r.status_code != 200:
        raise RDBException('Fetching object of type [{0}] failed. Error: {1}'.format(obj_class,r.json()["error"]))
    
    return r.json()


def retrieve_all_ids(obj_class:str):
    
    r = requests.get(f'https://openkardio-6586d-default-rtdb.firebaseio.com/{obj_class}.json?shallow=true')

    if r.status_code != 200:
        raise RDBException('Fetching object of type [{0}] failed. Error: {1}'.format(obj_class,r.json()["error"]))
    
    return r.json()

def delete_object(obj_class:str,obj_id) -> bool:

    r = requests.delete(f'https://openkardio-6586d-default-rtdb.firebaseio.com/{obj_class}/{obj_id}.json')

    if r.status_code != 200:
        raise RDBException('Fetching object of type [{0}] failed. Error: {1}'.format(obj_class,r.json()["error"]))
    


def main():
    new_user_id = create_object(
        "users",
        {
            "name":"Guillermo",
            "age":27,
            "blob":list(b'\x45\x36\x55\xf6\x36\x55\xf6\x36\x55\xf6\x36\x55\xf6')
        }
    )
    print("Created")
    print(retrieve_all_objects("users"))
    print("Retrieved")

if __name__ == '__main__':
    main()

