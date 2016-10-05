import PyQt5 # this force pyqtgraph to deal with Qt5
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
import numpy as np
#~ import pyaudio
import sounddevice as sd


from hearinglosssimulator.gui.guitools import FreqGainDuration, play_sinus, play_input_to_output



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

    def set_configuration(self, device='default', gain = -15., duration = 2., freq = 1000.):
        try: self.comboin.setCurrentIndex(self.map_devicename_to_item['input'][input_device])
        except: pass
        try: self.comboout.setCurrentIndex(self.map_devicename_to_item['output'][output_device])
        except: pass
        self.freqgainduration.set( gain = gain, duration = duration, freq = freq)
    
    def get_configuration(self):
        config = { 'input_device' : self.map_item_to_devicename['input'][self.comboin.currentIndex()],
                        'output_device' : self.map_item_to_devicename['output'][self.comboout.currentIndex()],
                }
        config.update(self.freqgainduration.get())
        return config

    def resfresh_device_list(self):
        devices = sd.query_devices()
        
        self.comboin.clear()
        self.comboout.clear()
        
        self.map_item_to_devicename = { 'input' : {},'output' : {} }
        self.map_devicename_to_item = { 'input' : {},'output' : {} }
        
        hostapi_names = [hostapi['name'] for hostapi in sd.query_hostapis()]
        
        for i, dev in enumerate(devices):
            hostapi_name = hostapi_names[dev['hostapi']]
            
            if dev['max_input_channels']>=1:
                self.comboin.addItem(u'{}: {} # HostAPI:{} # In:{} # Out:{}'.format(i, dev['name'], hostapi_name,
                                                                                                    dev['max_input_channels'], dev['max_output_channels'],))
                self.map_item_to_devicename['input'][self.comboin.count()-1] = dev['name']
                self.map_devicename_to_item['input'][dev['name']] = self.comboin.count()-1
                
            if dev['max_output_channels']>=1:
                self.comboout.addItem(u'{}: {} # HostAPI:{} # In:{} # Out:{}'.format(i, dev['name'], hostapi_name,
                                                                                                    dev['max_input_channels'], dev['max_output_channels'],))
                self.map_item_to_devicename['output'][self.comboout.count()-1] = dev['name']
                self.map_devicename_to_item['output'][dev['name']] = self.comboout.count()-1
                
                
    
    def test_play_sinus(self):
        p = self.freqgainduration.get()
        device = (self.get_configuration()['input_device'], self.get_configuration()['output_device'], )
        play_sinus(p['freq'], p['gain'], p['duration'], device=device)
    
    def play_input_to_output(self):
        duration = self.freqgainduration.get()['duration']
        device = (self.get_configuration()['input_device'], self.get_configuration()['output_device'], )
        play_input_to_output(duration,device ,  sample_rate=44100, chunksize=1024, nb_channel=2)
    

if __name__ == '__main__':
    app = pg.mkQApp()
    win = AudioDeviceSelection()
    win.set_configuration()
    win.show()
    app.exec_()
    print(win.get_configuration())


