import PyQt5 # this force pyqtgraph to deal with Qt5
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
import pyaudio

class FeqGainDuration(QtGui.QWidget):
    def __init__(self, parent = None):
        QtGui.QWidget.__init__(self, parent)
        mainlayout  =QtGui.QHBoxLayout()
        self.setLayout(mainlayout)

        mainlayout.addWidget(QtGui.QLabel(u'Gain (dBFs)'))
        self.spinbox_gain = QtGui.QSpinBox(maximum = 0, minimum = -100, value = -15.)
        mainlayout.addWidget(self.spinbox_gain)
        mainlayout.addStretch()
        
        mainlayout.addWidget(QtGui.QLabel(u'Duration (s)'))
        self.spinbox_duration = QtGui.QSpinBox(maximum = 15, minimum = .5, value = 2.)
        mainlayout.addWidget(self.spinbox_duration)
        mainlayout.addStretch()

        mainlayout.addWidget(QtGui.QLabel(u'Freq (Hz)'))
        self.spinbox_freq = QtGui.QSpinBox(maximum = 20000, minimum = 1, value = 1000.)
        mainlayout.addWidget(self.spinbox_freq)

    def set(self, gain = -15, duration = 2., freq = 1000.):
        self.spinbox_gain.setValue(gain)
        self.spinbox_duration.setValue(duration)
        self.spinbox_freq.setValue(freq)
    
    def get(self):
        return {
                        'gain' : float(self.spinbox_gain.value()),
                        'duration' : float(self.spinbox_duration.value()),
                        'freq' : float(self.spinbox_freq.value()),
                    }


def play_sinus(freq, gain, duration, output_device_index):
    pa = pyaudio.PyAudio()
    dev =  pa.get_device_info_by_index(output_device_index)
    samplerate =  dev['defaultSampleRate']
    nchannel = dev['maxOutputChannels']
    assert nchannel==2
    length = int(samplerate * duration)+1
    sound = hl.several_sinus(length, freqs = [freq],  samplerate = samplerate, ampl = 1.)
    sound = np.array([sound] * nchannel)
    steps = [ 
                    hl.InputNumpy('in', sound),
                    hl.GainProcessing('gain', ['in'], nchannel, gain),
                    hl.OutputAudioDevice('out', ['gain'], nchannel, output_device_index = output_device_index),
                    ]
    processor = hl.ProcessChainEngine(chunksize, winsize, samplerate, steps) 
    processor.run()
