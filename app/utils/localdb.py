import logging
from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, Date, LargeBinary, Float
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy_utils import create_database, database_exists
from datetime import date

SQLITE = 'sqlite:///test.db'
if not database_exists(SQLITE):
    create_database(SQLITE)

engine = create_engine(SQLITE, echo=True)
Base = declarative_base()
Session = sessionmaker(bind=engine)

class HealthCenter(Base):
    __tablename__ = 'healthcenters'

    id = Column(Integer, primary_key=True)
    global_id = Column(String, default="")
    name = Column(String, default="")
    category = Column(String, default="")
    location = Column(String, default="")
    silais = Column(String, default="")
    disabled = Column(Boolean, default=False)
    # doctors = relationship("Doctor", back_populates="hospital")
    exams = relationship('Exam', back_populates="destination")

class Person:
    id = Column(Integer, primary_key=True)
    first_name = Column(String, default="")
    last_name = Column(String, default="")
    address = Column(String, default="")
    sex = Column(String, default="")
    birth_date = Column(Date)
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
    
# class Doctor(Person, Base):
#     __tablename__ = 'doctors'

#     cod_minsa = Column(Integer)
#     email_address = Column(String, default="")
#     hospital_id = Column(Integer, ForeignKey('healthcenters.id'))
#     hospital = relationship("HealthCenter", back_populates="doctors")
#     cases = relationship('Case', back_populates='doctor')

class Ekg(Base):
    __tablename__ = 'ekgs'
    id = Column(Integer, primary_key=True)
    sample_rate = Column(Integer)
    signal = Column(LargeBinary)
    gain = Column(Float)
    bpm = Column(Integer)
    disabled = Column(Boolean, default=False)
    exam = relationship('Exam', back_populates='ekg')

class Exam(Base):
    __tablename__ = 'exams'

    id = Column(Integer, primary_key=True)
    name = Column(String, default="")
    patient_id = Column(Integer, ForeignKey('patients.id'))
    pressure = Column(String,default="")
    spo2 = Column(Float)
    weight_pd = Column(Float)
    ekg_id = Column(Integer, ForeignKey('ekgs.id'))
    notes = Column(String, default="")
    status = Column(String, default="GUARDADO")
    created = Column(Date)
    origin_id = Column(String, default="")
    diagnostic = Column(String, default="")
    destination_id = Column(Integer, ForeignKey('healthcenters.id'))
    sent = Column(Date)
    diagnosed = Column(Date)
    disabled = Column(Boolean, default=False)
    patient = relationship("Patient", back_populates='exams')
    ekg = relationship("Ekg", back_populates="exam")
    destination = relationship('HealthCenter', back_populates='exams')


Base.metadata.create_all(engine)
