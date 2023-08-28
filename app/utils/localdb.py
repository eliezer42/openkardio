from kivy.logger import Logger
from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, LargeBinary, Float, DateTime, Date
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy_utils import create_database, database_exists
from datetime import date, datetime
from os.path import join

Base = declarative_base()

class Hospital(Base):
    __tablename__ = 'hospitals'

    id = Column(Integer, primary_key=True)
    global_id = Column(String, default="")
    name = Column(String, default="")
    location = Column(String, default="")
    silais = Column(String, default="")
    email = Column(String, default="")
    disabled = Column(Boolean, default=False)
    exams = relationship('Exam', back_populates="destination")

class Person:
    id = Column(Integer, primary_key=True)
    first_name = Column(String, default="")
    last_name = Column(String, default="")
    address = Column(String, default="")
    sex = Column(String, default="")
    birth_date = Column(Date,default=date(1970,1,1))
    identification = Column(String, default="")
    disabled = Column(Boolean, default=False)

    def age(self):
        today = date.today()
        return today.year - self.birth_date.year - ((today.month, today.day) < (self.birth_date.month, self.birth_date.day))

    def name(self):
        return self.first_name + " " + self.last_name
    
class Patient(Person, Base):
    __tablename__ = 'patients'

    record = Column(String, default="")
    emergency_contact = Column(String, default="")
    exams = relationship("Exam", back_populates='patient')

class Ekg(Base):
    __tablename__ = 'ekgs'
    id = Column(Integer, primary_key=True)
    sample_rate = Column(Integer)
    signal = Column(LargeBinary)
    gain = Column(Float, default=8800.0)
    bpm = Column(Integer)
    leads = Column(Integer, default=1)
    disabled = Column(Boolean, default=False)
    exam = relationship('Exam', back_populates='ekg')

class Exam(Base):
    __tablename__ = 'exams'
    
    id = Column(Integer, primary_key=True)
    remote_id = Column(String, default="")
    status = Column(String, default="GUARDADO")
    created = Column(DateTime)
    modified = Column(DateTime)
    sent = Column(DateTime)
    diagnosed = Column(DateTime)
    name = Column(String, default="")
    origin_id = Column(String, default="")
    pressure = Column(String,default="")
    spo2 = Column(Float)
    weight_pd = Column(Float)
    notes = Column(String, default="")
    diagnostic = Column(String, default="")
    unopened = Column(Boolean, default=True)
    disabled = Column(Boolean, default=False)
    ekg_id = Column(Integer, ForeignKey('ekgs.id'))
    patient_id = Column(Integer, ForeignKey('patients.id'))
    destination_id = Column(Integer, ForeignKey('hospitals.id'))
    ekg = relationship("Ekg", back_populates="exam")
    patient = relationship("Patient", back_populates='exams')
    destination = relationship('Hospital', back_populates='exams')


def session_init(data_dir):
    SQLITE = f'sqlite:///{join(data_dir,"ok.db")}?check_same_thread=False'
    if not database_exists(SQLITE):
        create_database(SQLITE)

    engine = create_engine(SQLITE, echo=False)
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)

    return Session()
