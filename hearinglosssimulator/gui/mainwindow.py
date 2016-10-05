import PyQt5 # this force pyqtgraph to deal with Qt5
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
import os, sys
import json
import time

from collections import OrderedDict

import sounddevice as sd

import pyacq

import hearinglosssimulator as hls
from hearinglosssimulator.gui.parameters import HearingLossParameter
from hearinglosssimulator.gui.calibration import Calibration
from hearinglosssimulator.gui.audioselection import AudioDeviceSelection
from hearinglosssimulator.gui.gpuselection import GpuDeviceSelection



class Mutex(QtCore.QMutex):
    def __exit__(self, *args):
        self.unlock()

    def __enter__(self):
        self.lock()
        return self    




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
        self.but_start_stop.setIcon(QtGui.QIcon.fromTheme('media-playback-stop'))
        mainlayout.addWidget(self.but_start_stop)

        self.but_enable_bypass = QtGui.QPushButton(u'Enable/bypass simulator', checkable = True)
        self.but_enable_bypass.toggled.connect(self.enable_bypass_simulator)
        self.but_enable_bypass.setEnabled(False)
        mainlayout.addWidget(self.but_enable_bypass)
        
        mainlayout.addStretch()

        mainlayout.addWidget(QtGui.QLabel(u'<h1><b>Setup loss on each ear/Stop</b>'))
        self.hearingLossParameter = HearingLossParameter()
        mainlayout.addWidget(self.hearingLossParameter)

        self.timer_icon = QtCore.QTimer(interval=1000)
        self.timer_icon.timeout.connect(self.flash_icon)
        self.flag_icon = True
        self.timer_icon.start()
        
        

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
        self.stream_done = False
        
        self.mutex = Mutex()
    
    def flash_icon(self):
        if self.running():
            self.flag_icon = not(self.flag_icon)
            if self.flag_icon:
                self.but_start_stop.setIcon(QtGui.QIcon.fromTheme(''))
            else:
                self.but_start_stop.setIcon(QtGui.QIcon.fromTheme('media-playback-start'))
        else:
            self.but_start_stop.setIcon(QtGui.QIcon.fromTheme('media-playback-stop'))


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
        self.calibrationWidget.device = self.audio_device
    
    
    @property
    def audio_device(self):
        return (self.audioDeviceSelection.get_configuration()['input_device'], 
                        self.audioDeviceSelection.get_configuration()['output_device'])
    
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
                try:
                    element.set_configuration(**all_config[k])
                except:
                    pass

    def params_for_processing(self):
        chunksize = 512
        backward_chunksize = chunksize * 3
        
        calibration = self.calibrationWidget.get_configuration()['spl_calibration_at_zero_dbfs']
        loss_weigth_dict = self.hearingLossParameter.get_configuration()['loss_weigth']
        loss_weigth = [[(e['freq'], e['db_loss']) for e in l ] for l in loss_weigth_dict ]

        
        params = dict(
                #~ nb_freq_band=32, low_freq = 80., hight_freq = 20000.,
                nb_freq_band=10, low_freq = 80., hight_freq = 15000.,
                tau_level = 0.005, level_step =10., level_max = 120.,
                calibration =  calibration,
                loss_weigth = loss_weigth,
                chunksize=chunksize, backward_chunksize=backward_chunksize,
                gpu_platform_index = self.gpu_platform_index,
                gpu_device_index = self.gpu_device_index,
                debug_mode=False,
                bypass=self.but_enable_bypass.isChecked(),
            )
        return params

    
    def setup_audio_stream(self):
        nb_channel = 2
        sample_rate = 44100.
        params = self.params_for_processing()
        dtype='float32'
        
        self.processing = hls.InvCGC(nb_channel=nb_channel, sample_rate=sample_rate, dtype=dtype, **params)
        
        self.index = 0
        def callback(indata, outdata, frames, time, status):
            if status:
                print(status, flush=True)
            self.index += frames
            with self.mutex:
                returns = self.processing.proccesing_func(self.index, indata)
            index2, out = returns['main_output']
            if index2 is not None:
                outdata[:] = out
            else:
                outdata[:] = 0
        
        latency = 'low'
        #~ latency = 'high'
        self.stream = sd.Stream(channels=nb_channel, callback=callback, samplerate=sample_rate,
                        blocksize=params['chunksize'], latency=latency, device=self.audio_device)
        
        self.but_start_stop.setEnabled(True)
        self.but_enable_bypass.setEnabled(True)
        
        self.stream_done = True
        
    def running(self):
        if not self.stream_done:
            return False
        
        return self.stream.active
    
    def compute_filters(self):
        if not hasattr(self, 'stream'):
            self.setup_audio_stream()
        else:
            params = self.params_for_processing()
            
            print(params)
            t0 = time.perf_counter()
            self.processing.configure(**params)
            t1 = time.perf_counter()
            print(t1-t0)
            self.processing.make_filters()
            t2 = time.perf_counter()
            print(t2-t1)
            with self.mutex:        
                self.processing.initlalize_cl()
            t3 = time.perf_counter()
            print(t3-t2)
            print(t3-t0)                
            
                #~ self.processing.online_configure(**params)
    
    def start_stop_audioloop(self, checked):
        if checked:
            self.stream.start()
        else:
            self.stream.stop()
    
    def enable_bypass_simulator(self, checked):
        self.processing.set_bypass(checked)
        if checked:
            self.but_enable_bypass.setIcon(QtGui.QIcon.fromTheme('process-stop'))
        else:
            self.but_enable_bypass.setIcon(QtGui.QIcon.fromTheme(''))
            


        
        


if __name__ == '__main__':
    app = pg.mkQApp()
    win = MainWindow()
    win.show()
    app.exec_()

