import PyQt5 # this force pyqtgraph to deal with Qt5
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
import numpy as np
import pyaudio


from hearinglosssimulator.gui.tools import FreqGainDuration, play_sinus, play_input_to_output



class AudioDeviceSelection(QtGui.QWidget):
    def __init__(self, parent = None):
        QtGui.QWidget.__init__(self, parent)
        mainlayout  =QtGui.QVBoxLayout()
        self.setLayout(mainlayout)
        
        mainlayout.addWidget(QtGui.QLabel(u'<h1><b>Select device</b>'))
        but = QtGui.QPushButton('refresh device list')
        but.clicked.connect(self.resfresh_device_list)
        mainlayout.addWidget(but)
        
        mainlayout.addWidget(QtGui.QLabel(u'Input device'))
        self.comboin = QtGui.QComboBox()
        mainlayout.addWidget(self.comboin)
        mainlayout.addWidget(QtGui.QLabel(u'Output device'))
        self.comboout = QtGui.QComboBox()
        mainlayout.addWidget(self.comboout)
        
        mainlayout.addStretch()
        mainlayout.addWidget(QtGui.QLabel(u'<h1><b>Test device</b>'))
        
        self.freqgainduration = FreqGainDuration()
        mainlayout.addWidget(self.freqgainduration)
        
        but = QtGui.QPushButton('Test play sinus')
        but.clicked.connect(self.test_play_sinus)
        mainlayout.addWidget(but)

        but = QtGui.QPushButton('Test input to output')
        but.clicked.connect(self.play_input_to_output)
        mainlayout.addWidget(but)
        
        self.resfresh_device_list()

    def set_configuration(self, output_device_index = 0,input_device_index = 0,
                                                gain = -15., duration = 2., freq = 1000.):
        try: self.comboin.setCurrentIndex(self.map_deviceindex_to_item['input'][input_device_index])
        except: pass
        try: self.comboout.setCurrentIndex(self.map_deviceindex_to_item['output'][output_device_index])
        except: pass
        self.freqgainduration.set( gain = gain, duration = duration, freq = freq)
    
    def get_configuration(self):
        config = { 'input_device_index' : self.map_item_to_deviceindex['input'][self.comboin.currentIndex()], 
                        'output_device_index' : self.map_item_to_deviceindex['output'][self.comboout.currentIndex()],
                }
        config.update(self.freqgainduration.get())
        return config

    def resfresh_device_list(self):
        pa = pyaudio.PyAudio()
        self.comboin.clear()
        self.comboout.clear()
        self.map_item_to_deviceindex = { 'input' : {},'output' : {} }
        self.map_deviceindex_to_item = { 'input' : {},'output' : {} }
        for i in range(pa.get_device_count()):
            dev =  pa.get_device_info_by_index(i)
            hostapi_name = pa.get_host_api_info_by_index(dev['hostApi'])['name']
            if dev['maxInputChannels']>=1:
                self.comboin.addItem(u'{}: {} HostAPI {} max_chan {}'.format(i, dev['name'], hostapi_name, dev['maxInputChannels']))
                self.map_item_to_deviceindex['input'][self.comboin.count()-1] = i
                self.map_deviceindex_to_item['input'][i] = self.comboin.count()-1
            if dev['maxOutputChannels']>=1:
                self.comboout.addItem(u'{}: {} HostAPI {} max_chan {}'.format(i, dev['name'], hostapi_name, dev['maxOutputChannels']))
                self.map_item_to_deviceindex['output'][self.comboout.count()-1] = i
                self.map_deviceindex_to_item['output'][i] = self.comboout.count()-1
    
    def test_play_sinus(self):
        p = self.freqgainduration.get()
        output_device_index = self.get_configuration()['output_device_index']
        play_sinus(p['freq'], p['gain'], p['duration'], output_device_index)
    
    def play_input_to_output(self):
        duration = self.freqgainduration.get()['duration']
        input_device_index = self.get_configuration()['input_device_index']
        output_device_index = self.get_configuration()['output_device_index']
        play_input_to_output(duration, input_device_index, output_device_index,  sample_rate=44100, chunksize=1024, nb_channel=2)
    

if __name__ == '__main__':
    app = pg.mkQApp()
    win = AudioDeviceSelection()
    win.set_configuration()
    win.show()
    app.exec_()
    print(win.get_configuration())


