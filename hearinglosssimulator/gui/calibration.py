import PyQt5 # this force pyqtgraph to deal with Qt5
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
import numpy as np

from hearinglosssimulator.gui.tools import FeqGainDuration, play_sinus

class Calibration(QtGui.QWidget):
    def __init__(self, parent = None):
        QtGui.QWidget.__init__(self, parent)
        mainlayout  =QtGui.QVBoxLayout()
        self.setLayout(mainlayout)
        
        mainlayout.addWidget(QtGui.QLabel(u'<h1><b>Output level calibration</b>'))
        self.freqgainduration = FeqGainDuration()
        mainlayout.addWidget(self.freqgainduration)
        self.freqgainduration.spinbox_gain.valueChanged.connect(self.refresh_label_calibration)
        
        but = QtGui.QPushButton('Play sinus')
        but.clicked.connect(self.play_sinus)
        mainlayout.addWidget(but)
        
        mainlayout.addWidget(QtGui.QLabel(u'Play sinus and report dBSpl measurement:'))
        self.spinbox_spllevel = QtGui.QDoubleSpinBox(maximum = 140., minimum = 0., value = 93.979400086720375, decimals = 3)
        mainlayout.addWidget(self.spinbox_spllevel)
        self.spinbox_spllevel.valueChanged.connect(self.refresh_label_calibration)
        
        self.label_calibration = QtGui.QLabel(u'')
        mainlayout.addWidget(self.label_calibration)
        
        mainlayout.addStretch()
        mainlayout.addWidget(QtGui.QLabel(u'<h1><b>Input level check</b>'))
        but = QtGui.QPushButton('Start input>output', checkable = True)
        but.toggled.connect(self.start_stop_thread)
        
        mainlayout.addWidget(but)
        self.label_db_input = QtGui.QLabel(u'')
        mainlayout.addWidget(self.label_db_input)
        
        mainlayout.addStretch()
        
        #~ self.input_device_index = 4 #for debbuging
        #~ self.output_device_index = 3 #for debbuging
    
    
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
        play_sinus(p['freq'], p['gain'], p['duration'], self.window().output_device_index)
    
    def start_stop_thread(self, checked):
        if checked:
            self.thread =ThreadInputOutput(gain = 0.,
                                                                input_device_index = self.window().input_device_index,
                                                                output_device_index = self.window().output_device_index
                                                                )
            self.thread.start()
            self.timer = QtCore.QTimer(singleShot = False, interval = 50)
            self.timer.timeout.connect(self.refresh_label_db_input)
            self.timer.start()
            self.last_rms_value = 0.
        else:
            self.timer.stop()
            self.thread.stop()
            
    
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
    win = Calibration()
    win.show()
    app.exec_()
