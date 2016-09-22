import PyQt5 # this force pyqtgraph to deal with Qt5
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
import numpy as np

from hearinglosssimulator.gui.tools import FreqGainDuration, play_sinus, play_input_to_output


class Calibration(QtGui.QWidget):
    def __init__(self, input_device_index=None, output_device_index=None, parent = None):
        QtGui.QWidget.__init__(self, parent)

        self.input_device_index = input_device_index
        self.output_device_index = output_device_index
        
        
        mainlayout  =QtGui.QVBoxLayout()
        self.setLayout(mainlayout)
        
        mainlayout.addWidget(QtGui.QLabel(u'<h1><b>Output level calibration</b>'))
        self.freqgainduration = FreqGainDuration()
        mainlayout.addWidget(self.freqgainduration)
        self.freqgainduration.spinbox_gain.valueChanged.connect(self.refresh_label_calibration)
        
        but = QtGui.QPushButton('Test play sinus')
        but.clicked.connect(self.play_sinus)
        mainlayout.addWidget(but)

        
        mainlayout.addWidget(QtGui.QLabel(u'Play sinus and report dBSpl measurement:'))
        self.spinbox_spllevel = QtGui.QDoubleSpinBox(maximum = 140., minimum = 0., value = 93.979400086720375, decimals = 3)
        mainlayout.addWidget(self.spinbox_spllevel)
        self.spinbox_spllevel.valueChanged.connect(self.refresh_label_calibration)
        
        self.label_calibration = QtGui.QLabel(u'')
        mainlayout.addWidget(self.label_calibration)
        


        but = QtGui.QPushButton('Input to output')
        but.clicked.connect(self.play_input_to_output)
        mainlayout.addWidget(but)
        
        
        
        mainlayout.addWidget(but)
        self.label_db_input = QtGui.QLabel(u'')
        mainlayout.addWidget(self.label_db_input)
        
        mainlayout.addStretch()
        
    
    
    def set_configuration(self, gain = -15., duration = 2., freq = 1000., 
                                            spl_calibration_at_zero_dbfs = 93.979400086720375):
        self.freqgainduration.set( gain = gain, duration = duration, freq = freq)
        self.spinbox_spllevel.setValue(spl_calibration_at_zero_dbfs+gain)
        
    def get_configuration(self):
        config = self.freqgainduration.get()
        config['spl_calibration_at_zero_dbfs'] =  float(self.spinbox_spllevel.value())-config['gain']
        return config
    
    def refresh_label_calibration(self):
        text = u'<h1><b>0 dBFs = {:0.2f} dBSpl</b>'.format(self.get_configuration()['spl_calibration_at_zero_dbfs'])
        self.label_calibration.setText(text)

    def play_sinus(self):
        p = self.freqgainduration.get()
        play_sinus(p['freq'], p['gain'], p['duration'], self.output_device_index)
    
    def play_input_to_output(self):
        duration = self.freqgainduration.get()['duration']
        play_input_to_output(duration, self.input_device_index, self.output_device_index,  sample_rate=44100, chunksize=1024, nb_channel=2)
    
    def refresh_label_db_input(self):
        
        arr =  self.thread.processor.chain.steps['gain'].output_buffers[0].nparray
        
        rms_value = np.sqrt(np.mean(arr[0,:]**2))
        
        p = 0.05
        rms_value = rms_value*p + self.last_rms_value*(1.-p)
        self.last_rms_value = rms_value
        
        dbFs = 20.0*np.log10(rms_value/1.) + 20.0*np.log10(2**-.5) # -3.010299dB car amplitude max=1.
        
        dbSpl = dbFs + self.get_configuration()['spl_calibration_at_zero_dbfs']
        
        text = u'Input dBFs: {:0.2f} - dBSpl : {:0.2f}'.format(dbFs, dbSpl)
        self.label_db_input.setText(text)




if __name__ == '__main__':
    app = pg.mkQApp()
    win = Calibration( input_device_index=10, output_device_index=10)
    win.show()
    app.exec_()
    print(win.get_configuration())

