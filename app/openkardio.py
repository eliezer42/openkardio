import numpy as np

class Persona:
    def __init__(self, nombres, apellidos, direccion, sexo, fecha_nac, cedula, id=0, disabled=False) -> None:
        self.nombres = nombres
        self.apellidos = apellidos
        self.direccion = direccion
        self.sexo = sexo
        self.fecha_nac = fecha_nac
        self.cedula = cedula
        self.id = id
        self.disabled = disabled
    
class Paciente(Persona):
    def __init__(self, nombres, apellidos, direccion, sexo, fecha_nac, cedula, expediente="", padecimientos="",contacto_emergencia="", id=0, disabled=False) -> None:
        super().__init__(nombres, apellidos, direccion, sexo, fecha_nac, cedula, id, disabled)
        self.expediente = expediente
        self.padecimientos = padecimientos
        self.contacto_emergencia = contacto_emergencia

class Diagnosta(Persona):
    def __init__(self, nombres, apellidos, direccion, sexo, fecha_nac, cedula, cod_minsa=0, hospital_id=0, email_address="", id=0, disabled=False) -> None:
        super().__init__(nombres, apellidos, direccion, sexo, fecha_nac, cedula, id, disabled)
        self.cod_minsa = cod_minsa
        self.hospital_id = hospital_id
        self.email_address = email_address

class UnidadSalud:
    def __init__(self, nombre, ubicacion, silais, id=0) -> None:
        self.id = id
        self.nombre = nombre
        self.ubicacion = ubicacion
        self.silais = silais

class Ekg:
    def __init__(self, sample_rate=300, signal=[], gain = 1, bpm=0, ok_device_id="", id = 0) -> None:
        self.id = id
        self.sample_rate = sample_rate
        self.signal = np.array(signal)
        self.gain = gain
        self.bpm = bpm
        self.ok_device_id = ok_device_id

class Examen:
    def __init__(self, paciente_id, temp, presion, spo2, peso=0, ekg_id=0, observaciones = "", origen_id = 0, id = 0) -> None:
        self.id = id
        self.paciente_id = paciente_id
        self.temp = temp
        self.presion = presion
        self.spo2 = spo2
        self.peso = peso
        self.ekg_id = ekg_id
        self.observaciones = observaciones
        self.origen = origen_id

class Caso:
    def __init__(self, examen_id, diagnosta_id = 0, diagnostico = "", destino_id = 0, id = 0) -> None:
        self.id = id
        self.examen_id = examen_id
        self.diagnosta_id = diagnosta_id
        self.diagnostico = diagnostico
        self.destino_id = destino_id
