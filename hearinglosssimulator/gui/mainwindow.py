import PyQt5 # this force pyqtgraph to deal with Qt5
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
import os, sys
import json

from collections import OrderedDict

import pyacq

import hearinglosssimulator as hls
from hearinglosssimulator.gui.parameters import HearingLossParameter
from hearinglosssimulator.gui.calibration import Calibration
from hearinglosssimulator.gui.audioselection import AudioDeviceSelection
from hearinglosssimulator.gui.gpuselection import GpuDeviceSelection






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
        
        self.but_start_stop = QtGui.QPushButton(u'Start/Stop playback', checkable = True)
        self.but_start_stop.toggled.connect(self.start_stop_audioloop)
        self.but_start_stop.setEnabled(False)
        mainlayout.addWidget(self.but_start_stop)

        self.but_enable_bypass = QtGui.QPushButton(u'Enable/bypass simulator', checkable = True)
        self.but_enable_bypass.toggled.connect(self.enable_bypass_simulator)
        self.but_enable_bypass.setEnabled(False)
        mainlayout.addWidget(self.but_enable_bypass)
        
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

        #~ self.hearingLossParameter.valueChanged.connect(self.on_hearingloss_changed)
        #~ self.able_to_start = False
        
        self.pyacq_manager = None



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
                #~ print(k, all_config[k])
                element.set_configuration(**all_config[k])

    def on_hearingloss_changed(self):
        pass
    
    
    def params_for_node(self):
        chunksize = 512
        backward_chunksize = chunksize * 3
        
        calibration = self.calibrationWidget.get_configuration()['spl_calibration_at_zero_dbfs']
        loss_weigth_dict = self.hearingLossParameter.get_configuration()['loss_weigth']
        loss_weigth = [[(e['freq'], e['db_loss']) for e in l ] for l in loss_weigth_dict ]

        
        params = dict(
                nb_freq_band=32, low_freq = 80., hight_freq = 20000.,
                tau_level = 0.005, level_step =10., level_max = 120., #smooth_time = 0.0005, 
                calibration =  calibration,
                loss_weigth = loss_weigth,
                chunksize=chunksize, backward_chunksize=backward_chunksize,
                gpu_platform_index = self.gpu_platform_index,
                gpu_device_index = self.gpu_device_index,
                debug_mode=False,
                bypass=self.but_enable_bypass.isChecked(),
            )
        return params

        
    def setup_pyacq_nodes(self):
        if self.pyacq_manager is not None:
            self.pyacq_manager.close()
        
        nb_channel = 2
        sample_rate = 44100.
        params = self.params_for_node()
        
        stream_spec = dict(protocol='tcp', interface='127.0.0.1', transfertmode='plaindata')
        
        background = True
        #~ background = False
        if background:
            self.pyacq_manager = pyacq.create_manager()
            ng0 = self.pyacq_manager.create_nodegroup()  # process for device
            ng1 = self.pyacq_manager.create_nodegroup()  # process for processing
            self.audio_device = ng0.create_node('PyAudio')
            ng1.register_node_type_from_module('hearinglosssimulator', 'MainProcessing')
            self.node = ng1.create_node('MainProcessing')
        else:
            self.audio_device = pyacq.PyAudio()
            self.node = hls.MainProcessing()
        
        self.audio_device.configure(nb_channel=nb_channel, sample_rate=sample_rate,
                      input_device_index=self.input_device_index,
                      output_device_index=self.output_device_index,
                      format='float32', chunksize=params['chunksize'])
        self.audio_device.output.configure(**stream_spec)
        self.audio_device.initialize()
        
        self.node.configure(**params)
        
        self.node.input.connect(self.audio_device.output)
        self.node.outputs['signals'].configure(**stream_spec)
        if background:
            # this do compute filter take very long
            self.node.initialize(_timeout=60.)
        else:
            self.node.initialize()

        self.audio_device.input.connect(self.node.outputs['signals'])
        
        self.but_start_stop.setEnabled(True)
        self.but_enable_bypass.setEnabled(True)
    
    def running(self):
        if not hasattr(self, 'audio_device'):
            return False
        
        return self.audio_device.running()
    
    def compute_filters(self):
        if not hasattr(self, 'audio_device'):
            self.setup_pyacq_nodes()
        else:
            params = self.params_for_node()
            self.node.online_configure(**params, _timeout=60.)
    
    def start_stop_audioloop(self, checked):
        if checked:
            self.audio_device.start()
            self.node.start()
        else:
            self.audio_device.stop()
            self.node.stop()
    
    
    def enable_bypass_simulator(self, checked):
        self.node.set_bypass(checked)


        
        


if __name__ == '__main__':
    app = pg.mkQApp()
    win = MainWindow()
    win.show()
    app.exec_()

