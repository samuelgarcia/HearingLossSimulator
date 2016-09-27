import PyQt5 # this force pyqtgraph to deal with Qt5
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
import numpy as np
import pyaudio
import time

import hearinglosssimulator as hls


from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib import pyplot

class MplCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None, ):
        self.fig, self.ax = pyplot.subplots()
        FigureCanvasQTAgg.__init__(self, self.fig)
        self.setParent(parent)
        self.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        self.updateGeometry()
        self.fig.set_facecolor('#FFFFFF')
        
def test_Canvas():
    app = pg.mkQApp()
    win = MplCanvas()
    win.show()
    app.exec_()    


class FreqGainDuration(QtGui.QWidget):
    def __init__(self, parent = None):
        QtGui.QWidget.__init__(self, parent)
        mainlayout  =QtGui.QHBoxLayout()
        self.setLayout(mainlayout)

        mainlayout.addWidget(QtGui.QLabel(u'Gain (dBFs)'))
        self.spinbox_gain = QtGui.QSpinBox(maximum = 0, minimum = -100)
        mainlayout.addWidget(self.spinbox_gain)
        mainlayout.addStretch()
        
        mainlayout.addWidget(QtGui.QLabel(u'Duration (s)'))
        self.spinbox_duration = QtGui.QSpinBox(maximum = 15, minimum = .5)
        mainlayout.addWidget(self.spinbox_duration)
        mainlayout.addStretch()

        mainlayout.addWidget(QtGui.QLabel(u'Freq (Hz)'))
        self.spinbox_freq = QtGui.QSpinBox(maximum = 20000, minimum = 1)
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

def play_sinus(freq, dbgain, duration, output_device_index, nb_channel=2):
    pa = pyaudio.PyAudio()
    dev =  pa.get_device_info_by_index(output_device_index)
    sample_rate =  dev['defaultSampleRate']
    assert nb_channel<=dev['maxOutputChannels']
    
    length = int(sample_rate * duration)+1
    sound = hls.several_sinus(length, freqs=[freq], sample_rate=sample_rate, ampl = 1.)
    sound = np.tile(sound[:, None],(1, nb_channel))

    gain = 10**(dbgain/20.)
    sound *= gain
    
    hls.play_with_pyaudio(sound, sample_rate=44100., output_device_index=output_device_index, chunksize=1024)
    

def test_play_sinus():
    play_sinus(1000., -30, 4., 10)


def play_input_to_output(duration, input_device_index, output_device_index,  sample_rate=44100, chunksize=1024, nb_channel=2):
    pa = pyaudio.PyAudio()
    
    def callback(in_data, frame_count, time_info, status):
        return (in_data, pyaudio.paContinue)
    
    audiostream = pa.open(rate=int(sample_rate), channels=int(nb_channel), format= pyaudio.paFloat32,
                    input=True, output=True, input_device_index=input_device_index, output_device_index=output_device_index,
                    frames_per_buffer=chunksize, stream_callback=callback, start=False)
    
    
    audiostream.start_stream()
    
    t_start = time.perf_counter()
    while (time.perf_counter()-t_start)<duration:
        time.sleep(0.01)

    audiostream.stop_stream()
    audiostream.close()

    pa.terminate()
    
    
    
def test_play_input_to_output():
    play_input_to_output(4, 10,10)
    



if __name__ == '__main__':
    test_Canvas()
    #~ test_FreqGainDuration()
    #~ test_play_sinus()
    #~ test_play_input_to_output()


