from .myqt import QT
import pyqtgraph as pg

import numpy as np

import sounddevice as sd

import time

import hearinglosssimulator as hls


from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib import pyplot

class MplCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None, ):
        self.fig, self.ax = pyplot.subplots()
        FigureCanvasQTAgg.__init__(self, self.fig)
        self.setParent(parent)
        self.setSizePolicy(QT.QSizePolicy.Expanding, QT.QSizePolicy.Expanding)
        self.updateGeometry()
        self.fig.set_facecolor('#FFFFFF')
        
def test_Canvas():
    app = pg.mkQApp()
    win = MplCanvas()
    win.show()
    app.exec_()    


class FreqGainDuration(QT.QWidget):
    def __init__(self, parent = None):
        QT.QWidget.__init__(self, parent)
        mainlayout  =QT.QHBoxLayout()
        self.setLayout(mainlayout)

        mainlayout.addWidget(QT.QLabel(u'Gain (dBFs)'))
        self.spinbox_gain = QT.QSpinBox(maximum = 0, minimum = -100)
        mainlayout.addWidget(self.spinbox_gain)
        mainlayout.addStretch()
        
        mainlayout.addWidget(QT.QLabel(u'Duration (s)'))
        self.spinbox_duration = QT.QSpinBox(maximum = 15, minimum = .5)
        mainlayout.addWidget(self.spinbox_duration)
        mainlayout.addStretch()

        mainlayout.addWidget(QT.QLabel(u'Freq (Hz)'))
        self.spinbox_freq = QT.QSpinBox(maximum = 20000, minimum = 1)
        mainlayout.addWidget(self.spinbox_freq)
        
        self.set()

    def set(self, gain = -15, duration = 2., freq = 1000.):
        pass
        self.spinbox_gain.setValue(gain)
        self.spinbox_duration.setValue(duration)
        self.spinbox_freq.setValue(freq)
    
    def get(self):
        return {
                        'gain' : float(self.spinbox_gain.value()),
                        'duration' : float(self.spinbox_duration.value()),
                        'freq' : float(self.spinbox_freq.value()),
                    }

def test_FreqGainDuration():
    app = pg.mkQApp()
    win = FreqGainDuration()
    win.show()
    app.exec_()

def play_sinus(freq, dbgain, duration, device='default', nb_channel=2):
    if device is None:
        device='default'
    dev = sd.query_devices(device=device)
    print(dev)
    
    sample_rate = dev['default_samplerate']
    
    
    length = int(sample_rate * duration)+1
    sound = hls.several_sinus(length, freqs=[freq], sample_rate=sample_rate, ampl = 1.)
    sound = np.tile(sound[:, None],(1, nb_channel))
    gain = 10**(dbgain/20.)
    sound *= gain
    
    sd.play(sound, device=device, blocking=True)
    
    sd.stop()
    
    

def test_play_sinus():
    print(sd.query_devices())
    #~ play_sinus(1000., -30, 4., device='default')
    #~ play_sinus(1000., -30, 4., device=2)
    play_sinus(1000., -30, 4., device='Mappeur de sons Microsoft - Output')
    #~ Mappeur de sons Microsoft


def play_input_to_output(duration, device, sample_rate=44100, chunksize=1024, nb_channel=2):
    #~ duration = 5  # seconds
    dev = sd.query_devices(device=device)
    sample_rate = dev['default_samplerate']
    print(dev)
    

    def callback(indata, outdata, frames, time, status):
        if status:
            print(status, flush=True)
        outdata[:] = indata

    with sd.Stream(device=device, channels=nb_channel, callback=callback, samplerate=sample_rate):
        sd.sleep(int(duration * 1000)    )
    
    
    
    
    #~ pa = pyaudio.PyAudio()
    
    #~ def callback(in_data, frame_count, time_info, status):
        #~ return (in_data, pyaudio.paContinue)
    
    #~ audiostream = pa.open(rate=int(sample_rate), channels=int(nb_channel), format= pyaudio.paFloat32,
                    #~ input=True, output=True, input_device_index=input_device_index, output_device_index=output_device_index,
                    #~ frames_per_buffer=chunksize, stream_callback=callback, start=False)
    
    
    #~ audiostream.start_stream()
    
    #~ t_start = time.perf_counter()
    #~ while (time.perf_counter()-t_start)<duration:
        #~ time.sleep(0.01)

    #~ audiostream.stop_stream()
    #~ audiostream.close()

    #~ pa.terminate()
    
    
    
def test_play_input_to_output():
    print(sd.query_devices())
    play_input_to_output(4, 'default')
    #~ play_input_to_output(4, 10)




def get_dict_from_group_param(param, cascade = False):
    assert param.type() == 'group'
    d = {}
    for p in param.children():
        if p.type() == 'group':
            if cascade:
                d[p.name()] = get_dict_from_group_param(p, cascade = True)
            continue
        else:
            d[p.name()] = p.value()
    return d




if __name__ == '__main__':
    #~ test_Canvas()
    #~ test_FreqGainDuration()
    test_play_sinus()
    #~ test_play_input_to_output()


