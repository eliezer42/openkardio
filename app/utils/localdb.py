import logging
from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, Date, LargeBinary, Float
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy_utils import create_database, database_exists
from datetime import date

SQLITE                  = 'sqlite:///test.db'
if not database_exists(SQLITE):
    create_database(SQLITE)

engine = create_engine(SQLITE, echo=True)
Base = declarative_base()
Session = sessionmaker(bind=engine)

class HealthCenter(Base):
    __tablename__ = 'healthcenters'

    id = Column(Integer, primary_key=True)
    name = Column(String, default="")
    category = Column(String, default="")
    location = Column(String, default="")
    silais = Column(String, default="")
    disabled = Column(Boolean, default=False)
    doctors = relationship("Doctor", back_populates="hospital")
    exams = relationship('Exam', back_populates="origin")
    cases = relationship('Case', back_populates='destination')

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
    
class Patient(Person, Base):
    __tablename__ = 'patients'

    record = Column(String, default="")
    med_conditions = Column(String, default="")
    emergency_contact = Column(String, default="")
    exams = relationship("Exam", back_populates='patient')
    
class Doctor(Person, Base):
    __tablename__ = 'doctors'

    cod_minsa = Column(Integer)
    email_address = Column(String, default="")
    hospital_id = Column(Integer, ForeignKey('healthcenters.id'))
    hospital = relationship("HealthCenter", back_populates="doctors")
    cases = relationship('Case', back_populates='doctor')

class Ekg(Base):
    __tablename__ = 'ekgs'
    id = Column(Integer, primary_key=True)
    sample_rate = Column(Integer)
    signal = Column(LargeBinary)
    gain = Column(Float)
    bpm = Column(Integer)
    ok_device_id = Column(String, default="")
    disabled = Column(Boolean, default=False)
    exam = relationship('Exam', back_populates='ekg')

class Exam(Base):
    __tablename__ = 'exams'

    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey('patients.id'))
    temp = Column(Float)
    sys_pres = Column(Integer)
    dia_pres = Column(Integer)
    spo2 = Column(Integer)
    weight_pd = Column(Integer)
    ekg_id = Column(Integer, ForeignKey('ekgs.id'))
    notes = Column(String, default="")
    origin_id = Column(Integer, ForeignKey('healthcenters.id'))
    disabled = Column(Boolean, default=False)
    patient = relationship("Patient", back_populates='exams')
    ekg = relationship("Ekg", back_populates="exam")
    origin = relationship('HealthCenter', back_populates='exams')
    case = relationship('Case', back_populates='exam')

class Case(Base):
    __tablename__ = 'cases'

    id = Column(Integer, primary_key=True)
    exam_id = Column(Integer, ForeignKey('exams.id'))
    doctor_id = Column(Integer, ForeignKey('doctors.id'))
    diagnostics = Column(String, default="")
    destination_id = Column(Integer, ForeignKey('healthcenters.id'))
    disabled = Column(Boolean)
    exam = relationship("Exam", back_populates='case')
    doctor = relationship("Doctor", back_populates="cases")
    destination = relationship('HealthCenter', back_populates='cases')

Base.metadata.create_all(engine)

if __name__ == '__main__':
    session = Session()
    patient1 = Patient(first_name="Eliezer", last_name="Mendez", sex="M", birth_date=date(1998, 3, 28), record="123-456-789")
    patient2 = Patient(first_name="Guillermo", last_name="Mendez", sex="M", birth_date=date(1960, 6, 25), record="123-456-789")
    patient3 = Patient(first_name="Evelyn", last_name="Delgado", sex="F", birth_date=date(1970, 12, 13), record="123-456-789")
    session.add_all([patient1, patient2, patient3])
    exam1 = Exam()
    session.commit()
    session.close()