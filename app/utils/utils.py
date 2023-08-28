import time
import numpy as np

class Signal:
    WAVEFORMS = ['square', 'triangle']
    def __init__(self, freq, srate, maxamp, offset, waveform) -> None:
        self.freq = freq
        self.srate = srate
        self.maxamp = maxamp
        self.offset = offset
        if waveform in self.WAVEFORMS:
            self.waveform = waveform
        else:
            raise Exception("Sorry, waveform not found")
        self.running = False

    def triangle(self, length, amplitude, offset):
        section = length // 4
        while True:
            for direction in (1, -1):
                for i in range(section):
                    yield i * (amplitude / section) * direction + offset
                for i in range(section):
                    yield (amplitude - (i * (amplitude / section))) * direction + offset

    def square(self, length, amplitude, offset):
        section = length // 2
        while True:
            for direction in (1, 0):
                for i in range(section):
                    yield amplitude * direction + offset

    def start(self, duration):
        self.start_time = time.time()
        self.duration = duration
        self.time = time.time()
        self.delta = 0
        if self.waveform == "square":
            self.gen = self.square(int(self.srate//self.freq), self.maxamp, self.offset)
        elif self.waveform == "triangle":
            self.gen = self.triangle(int(self.srate//self.freq), self.maxamp, self.offset)
        self.running = True

    def get_samples(self):
        if self.running:
            if self.time - self.start_time < self.duration:
                self.delta = time.time() - self.time
                self.time = time.time()
                self.n_samples = np.floor(self.srate*self.delta)
                self.samples = [next(self.gen) for _ in range(int(self.n_samples))]
                return self.samples
            else:
                self.stop()
                return []
        else:
            raise Exception("You should start this Signal first")
            
    def stop(self):
        self.running = False
        self.samples = []

def time_gen(srate):
    time_bin = 0
    while True:
        yield time_bin
        time_bin += 1/srate

        
single_pulse = [959,958,957,955,954,954,953,954,953,951,949,951,950,952,951,947,
    947,948,950,949,949,947,945,946,947,945,945,943,942,942,943,944,
    944,942,942,942,943,943,943,944,944,944,947,947,948,943,943,945,
    945,947,951,950,954,957,958,960,961,958,957,960,962,966,966,963,
    961,964,968,966,966,964,960,959,955,955,956,954,955,956,960,959,
    956,951,947,946,948,947,945,941,938,938,935,935,933,933,933,935,
    937,937,934,931,930,932,934,935,936,935,933,933,934,935,934,933,
    929,921,910,904,907,917,930,952,990,1058,1131,1204,1267,1325,1361,
    1364,1325,1236,1122,1019,951,919,909,910,928,948,957,955,945,942,
    938,941,940,939,936,930,929,928,929,929,928,927,925,927,927,926,
    928,926,927,928,930,929,927,926,926,926,929,928,930,928,926,927,
    933,934,934,933,929,935,937,939,939,937,938,942,944,948,949,951,
    953,957,961,965,966,970,972,976,981,983,988,990,992,998,1003,1006,
    1010,1012,1013,1015,1019,1025,1026,1026,1027,1031,1032,1035,1036,
    1031,1030,1033,1031,1032,1030,1025,1022,1018,1016,1013,1005,1003,
    997,993,990,989,984,979,972,971,970,971,967,964,962,961,963,964,
    961,957,955,959,958,959,958,955,957,957,958,957,957,954,956,957,
    958,957,959,958,960,960,961,960,961,962,963,964,965,963,962,965,
    965,964,966,967,967,965,966,967,968,968,967,965,967,967,966,968,
    967,966,965,964]

def custom_lfilter(b, a, x):
    if len(a) == 1:
        # For FIR filters (a = [1.0]), use simple convolution
        return np.convolve(b, x, mode='full')[:len(x)]
    else:
        if len(b) < len(a):
            # Pad 'b' with zeros to have the same length as 'a'
            b = np.pad(b, (0, len(a) - len(b)), 'constant')
        elif len(a) < len(b):
            # Pad 'a' with zeros to have the same length as 'b'
            a = np.pad(a, (0, len(b) - len(a)), 'constant')

        # Normalize 'a' coefficients to have 'a[0]' equal to 1
        a /= a[0]

        # Initialize output array
        y = np.zeros(len(x))

        # Apply direct form filtering
        for i in range(len(x)):
            y[i] = np.sum(b * x[i::-1]) - np.sum(a[1:] * y[i::-1])

        return y

def christov_detector(unfiltered_ecg, fs):
    """
    Ivaylo I. Christov, 
    Real time electrocardiogram QRS detection using combined 
    adaptive threshold, BioMedical Engineering OnLine 2004, 
    vol. 3:28, 2004.
    """
    total_taps = 0

    b = np.ones(int(0.02*fs))
    b = b/int(0.02*fs)
    total_taps += len(b)
    a = [1]

    MA1 = custom_lfilter(b, a, unfiltered_ecg)

    b = np.ones(int(0.028*fs))
    b = b/int(0.028*fs)
    total_taps += len(b)
    a = [1]

    MA2 = custom_lfilter(b, a, MA1)

    Y = []
    for i in range(1, len(MA2)-1):
        
        diff = abs(MA2[i+1]-MA2[i-1])

        Y.append(diff)

    b = np.ones(int(0.040*fs))
    b = b/int(0.040*fs)
    total_taps += len(b)
    a = [1]

    MA3 = custom_lfilter(b, a, Y)

    MA3[0:total_taps] = 0

    ms50 = int(0.05*fs)
    ms200 = int(0.2*fs)
    ms1200 = int(1.2*fs)
    ms350 = int(0.35*fs)

    M = 0
    newM5 = 0
    M_list = []
    MM = []
    M_slope = np.linspace(1.0, 0.6, ms1200-ms200)
    F = 0
    F_list = []
    R = 0
    RR = []
    Rm = 0
    R_list = []

    MFR = 0
    MFR_list = []

    QRS = []

    for i in range(len(MA3)):

        # M
        if i < 5*fs:
            M = 0.6*np.max(MA3[:i+1])
            MM.append(M)
            if len(MM)>5:
                MM.pop(0)

        elif QRS and i < QRS[-1]+ms200:
            newM5 = 0.6*np.max(MA3[QRS[-1]:i])
            if newM5>1.5*MM[-1]:
                newM5 = 1.1*MM[-1]

        elif QRS and i == QRS[-1]+ms200:
            if newM5==0:
                newM5 = MM[-1]
            MM.append(newM5)
            if len(MM)>5:
                MM.pop(0)    
            M = np.mean(MM)    
        
        elif QRS and i > QRS[-1]+ms200 and i < QRS[-1]+ms1200:

            M = np.mean(MM)*M_slope[i-(QRS[-1]+ms200)]

        elif QRS and i > QRS[-1]+ms1200:
            M = 0.6*np.mean(MM)

        # F
        if i > ms350:
            F_section = MA3[i-ms350:i]
            max_latest = np.max(F_section[-ms50:])
            max_earliest = np.max(F_section[:ms50])
            F = F + ((max_latest-max_earliest)/150.0)

        # R
        if QRS and i < QRS[-1]+int((2.0/3.0*Rm)):

            R = 0

        elif QRS and i > QRS[-1]+int((2.0/3.0*Rm)) and i < QRS[-1]+Rm:

            dec = (M-np.mean(MM))/1.4
            R = 0 + dec


        MFR = M+F+R
        M_list.append(M)
        F_list.append(F)
        R_list.append(R)
        MFR_list.append(MFR)

        if not QRS and MA3[i]>MFR:
            QRS.append(i)
        
        elif QRS and i > QRS[-1]+ms200 and MA3[i]>MFR:
            QRS.append(i)
            if len(QRS)>2:
                RR.append(QRS[-1]-QRS[-2])
                if len(RR)>5:
                    RR.pop(0)
                Rm = int(np.mean(RR))

    QRS.pop(0)
    
    return QRS