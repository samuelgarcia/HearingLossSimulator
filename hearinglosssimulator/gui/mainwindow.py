import PyQt5 # this force pyqtgraph to deal with Qt5
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
import os, sys
import json

from collections import OrderedDict

from hearinglosssimulator.gui.parameters import HearingLossParameter
from hearinglosssimulator.gui.calibration import Calibration
from hearinglosssimulator.gui.audioselection import AudioDeviceSelection
from hearinglosssimulator.gui.gpuselection import GpuDeviceSelection


HearingLossParameter

class MainWindow(QtGui.QWidget):
    def __init__(self, parent = None):
        QtGui.QWidget.__init__(self, parent)
        mainlayout  = QtGui.QVBoxLayout()
        self.setLayout(mainlayout)
        
        self.resize(800,500)
        
        
        
        #~ mainlayout.addLayout(h)
        #~ but = QtGui.QPushButton(u'Configure audio')
        #~ h.addWidget(but)
        #~ but.clicked.connect(self.open_audioDeviceSelection)
        #~ but = QtGui.QPushButton(u'Configure GPU')
        #~ h.addWidget(but)
        #~ but.clicked.connect(self.open_gpuDeviceSelection)
        #~ but = QtGui.QPushButton(u'Calibration')
        #~ h.addWidget(but)
        #~ but.clicked.connect(self.open_calibrationWidget)
        
        
        
        self.audioDeviceSelection = AudioDeviceSelection(parent=self)
        self.gpuDeviceSelection = GpuDeviceSelection(parent=self)
        self.calibrationWidget = Calibration(parent=self)
        
        self.dialogs = OrderedDict([ ('Configure audio', {'widget' :self.audioDeviceSelection}), 
                                ('Configure GPU', {'widget' :self.gpuDeviceSelection}), 
                                ('Calibration', {'widget' :self.calibrationWidget}) ])
        
        mainlayout.addWidget(QtGui.QLabel(u'<h1><b>Configure</b>'))
        h = QtGui.QHBoxLayout()
        mainlayout.addLayout(h)
        for name, attr in self.dialogs.items():
            but = QtGui.QPushButton(name)
            h.addWidget(but)
            but.clicked.connect(self.open_dialog)
            attr['but'] = but
            attr['widget'].setWindowFlags(QtCore.Qt.Window)
            attr['widget'].setWindowModality(QtCore.Qt.NonModal)
            
            attr['dia'] = dia = QtGui.QDialog()
            layout  = QtGui.QVBoxLayout()
            dia.setLayout(layout)
            layout.addWidget(attr['widget'])
            
        
        
        mainlayout.addWidget(QtGui.QLabel(u'<h1><b>Start/Stop</b>'))
        self.but_compute_filters = QtGui.QPushButton(u'Computed filters')
        self.but_compute_filters.clicked.connect(self.compute_filters)
        mainlayout.addWidget(self.but_compute_filters)
        self.but_start_stop = QtGui.QPushButton(u'Start/Stop simulator on inputs', checkable = True)
        self.but_start_stop.toggled.connect(self.start_stop_audioloop)
        self.but_start_stop.setEnabled(False)
        mainlayout.addWidget(self.but_start_stop)
        mainlayout.addStretch()

        mainlayout.addWidget(QtGui.QLabel(u'<h1><b>Setup loss on each ear/Stop</b>'))
        self.hearingLossParameter = HearingLossParameter()
        mainlayout.addWidget(self.hearingLossParameter)

        
        
        

        self.configuration_elements = { 'audiodevice' : self.audioDeviceSelection,
                                                'gpudevice' : self.gpuDeviceSelection,
                                                'hearingloss' : self.hearingLossParameter,
                                                'calibration' : self.calibrationWidget,
                                                }
        self.load_configuration()
        self.change_audio_device()

        self.hearingLossParameter.valueChanged.connect(self.on_hearingloss_changed)
        self.able_to_start = False
        self.thread =None


    def warn(self, title, text):
        mb = QtGui.QMessageBox.warning(self, title,text, 
                QtGui.QMessageBox.Ok ,  QtGui.QMessageBox.Default  | QtGui.QMessageBox.Escape,
                QtGui.QMessageBox.NoButton)

    def closeEvent (self, event):
        try:
        #~ if True:
            self.save_configuration()
        except:
            self.warn('config', 'impossible to save configuration file')
        event.accept()

    @property
    def filename(self):
        if sys.platform.startswith('win'):
            dirname = os.path.join(os.environ['APPDATA'], 'HearingLossSimulator')
        else:
            dirname = os.path.expanduser('~/.config/HearingLossSimulator')
        if not os.path.exists(dirname):
            os.mkdir(dirname)
        filename = os.path.join(dirname, 'configuration.json')
        return filename
    
    def open_dialog(self):
        for name, attr in self.dialogs.items():
            if attr['but']==self.sender(): break
        
        attr['dia'].exec_()
        self.save_configuration()
        self.change_audio_device()
    
    
    def change_audio_device(self):
        self.calibrationWidget.output_device_index = self.output_device_index
        self.calibrationWidget.input_device_index = self.input_device_index
    
    @property
    def output_device_index(self):
        return self.audioDeviceSelection.get_configuration()['output_device_index']

    @property
    def input_device_index(self):
        return self.audioDeviceSelection.get_configuration()['input_device_index']

    @property
    def gpu_platform_index(self):
        return self.gpuDeviceSelection.get_configuration()['platform_index']

    @property
    def gpu_device_index(self):
        return self.gpuDeviceSelection.get_configuration()['device_index']


    def save_configuration(self):
        all_config = {k:e.get_configuration() for k, e in self.configuration_elements.items()}
        with open(self.filename, 'w', encoding='utf8') as fd:
            json.dump(all_config, fd, indent = 4)
    
    def load_configuration(self):
        if not os.path.exists(self.filename): return
        
        with open(self.filename, 'r', encoding='utf8') as fd:
            all_config = json.load(fd)
        
        for k , element in self.configuration_elements.items():
            if k in all_config:
                element.set_configuration(**all_config[k])

    def on_hearingloss_changed(self):
        self.able_to_start = False
        if self.thread is None or not self.thread.isRunning(): 
            self.but_start_stop.setEnabled(self.able_to_start)
    
    def compute_filters(self):
        pass
        # TODO
        
        #~ if self.thread is not None and self.thread.isRunning(): 
            #~ return
        
        #~ loss_weigth_dict = self.hearingLossParameter.get_configuration()['loss_weigth']
        #~ loss_weigth = [[(e['freq'], e['db_loss']) for e in l ] for l in loss_weigth_dict ]
        #~ loss_params = dict(
                        #~ nfreq = 32,
                        #~ low_freq = 80.,
                        #~ hight_freq = 15000.,
                        #~ tau1 = 0.005, #s. decay for level estimation
                        #~ smooth_time = 0.0005, #s.
                        #~ levelstep =.1, #dB
                        #~ levelmax = 120., #dB
                        #~ calibration =  self.calibrationWidget.get_configuration()['spl_calibration_at_zero_dbfs'],
                        #~ loss_weigth = loss_weigth,
                        #~ )

        #~ self.thread =ThreadHearingLoss(
                                                            #~ input_device_index = self.input_device_index,
                                                            #~ output_device_index = self.output_device_index,
                                                            #~ gpu_platform_index = self.gpu_platform_index,
                                                            #~ gpu_device_index = self.gpu_device_index,
                                                            #~ **loss_params
                                                            #~ )
        self.able_to_start = True
        self.but_start_stop.setEnabled(self.able_to_start)
    
    def start_stop_audioloop(self, checked):
        if checked:
            #~ self.thread.start()
            pass
        else:
            #~ self.thread.stop()
            #~ self.thread.wait()
            self.but_start_stop.setEnabled(self.able_to_start)


        
        


if __name__ == '__main__':
    app = pg.mkQApp()
    win = MainWindow()
    win.show()
    app.exec_()

