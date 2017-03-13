import PyQt5 # this force pyqtgraph to deal with Qt5
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
import os, sys
import json
import time

from collections import OrderedDict

import sounddevice as sd

#~ import pyacq

import hearinglosssimulator as hls
from hearinglosssimulator.gui.lossparameters import HearingLossParameter
from hearinglosssimulator.gui.calibration import Calibration
from hearinglosssimulator.gui.audioselection import AudioDeviceSelection
from hearinglosssimulator.gui.gpuselection import GpuDeviceSelection



class Mutex(QtCore.QMutex):
    def __exit__(self, *args):
        self.unlock()

    def __enter__(self):
        self.lock()
        return self    


class MainWindow(QtGui.QMainWindow):
    def __init__(self, parent = None):
        QtGui.QMainWindow.__init__(self, parent)
        
        self.setWindowTitle(u'Hearing loss simulator')
        #~ self.setWindowIcon(QtGui.QIcon(':/TODO.png'))
        self.resize(1000,800)
        
        self.createActions()
        self.createToolBars()
        
        # central layout
        w = QtGui.QWidget()
        self.setCentralWidget(w)
        mainlayout  = QtGui.QVBoxLayout()
        w.setLayout(mainlayout)
        
        
        mainlayout.addWidget(QtGui.QLabel(u'<h1><b>Start/Stop</b>'))
        h = QtGui.QHBoxLayout()
        mainlayout.addLayout(h)
        
        self.but_compute_filters = QtGui.QPushButton(u'Computed filters')
        self.but_compute_filters.clicked.connect(self.compute_filters)
        h.addWidget(self.but_compute_filters)
        
        self.but_start_stop = QtGui.QPushButton(u'Start/Stop playback', checkable = True, enabled= False)
        self.but_start_stop.toggled.connect(self.start_stop_audioloop)
        self.but_start_stop.setIcon(QtGui.QIcon.fromTheme('media-playback-stop'))
        h.addWidget(self.but_start_stop)

        self.but_enable_bypass = QtGui.QPushButton(u'Enable/bypass simulator', checkable = True, enabled=False)
        self.but_enable_bypass.toggled.connect(self.enable_bypass_simulator)
        h.addWidget(self.but_enable_bypass)

        
        mainlayout.addWidget(QtGui.QLabel(u'<h1><b>Setup loss on each ear</b>'))
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
        
        #~ self.pyacq_manager = None
        self.stream_done = False
        
        self.mutex = Mutex()

    def createActions(self):
        self.actions = OrderedDict()
        
        self.audioDeviceSelection = AudioDeviceSelection(parent=self)
        self.gpuDeviceSelection = GpuDeviceSelection(parent=self)
        self.calibrationWidget = Calibration(parent=self)
        
        self.dialogs = OrderedDict([ ('Configure audio', {'widget' :self.audioDeviceSelection}), 
                                ('Configure GPU', {'widget' :self.gpuDeviceSelection}), 
                                ('Calibration', {'widget' :self.calibrationWidget}) ])
        
        for name, attr in self.dialogs.items():
            act = self.actions[name] = QtGui.QAction(name, self, checkable = False) #, icon =QtGui.QIcon(':/TODO.png'))
            act.triggered.connect(self.open_dialog)
            attr['action'] = act
            attr['widget'].setWindowFlags(QtCore.Qt.Window)
            attr['widget'].setWindowModality(QtCore.Qt.NonModal)
            attr['dia'] = dia = QtGui.QDialog()
            layout  = QtGui.QVBoxLayout()
            dia.setLayout(layout)
            layout.addWidget(attr['widget'])

    def createToolBars(self):
        self.toolbar = QtGui.QToolBar()
        self.toolbar.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
        self.addToolBar(self.toolbar)
        self.toolbar.setIconSize(QtCore.QSize(60, 40))
        
        for name, act in self.actions.items():
            self.toolbar.addAction(act)


    
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
        elif  sys.platform.startswith('darwin'):
            dirname = '~/Library/Application Support/HearingLossSimulator/'
        else:
            dirname = os.path.expanduser('~/.config/HearingLossSimulator')
            
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        filename = os.path.join(dirname, 'configuration.json')
        return filename
    
    def open_dialog(self):
        for name, attr in self.dialogs.items():
            if attr['action']==self.sender(): break
        
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
        #~ chunksize = 512
        #~ backward_chunksize = chunksize * 3
        chunksize = 1024
        backward_chunksize = chunksize * 2
        
        calibration = self.calibrationWidget.get_configuration()['spl_calibration_at_zero_dbfs']
        loss_params = self.hearingLossParameter.get_configuration()

        params = dict(
                #~ nb_freq_band=32, low_freq = 80., high_freq = 20000.,
                nb_freq_band=10, low_freq = 80., high_freq = 15000.,
                tau_level = 0.005, level_step =1., level_max = 120.,
                calibration =  calibration,
                loss_params = loss_params,
                chunksize=chunksize, backward_chunksize=backward_chunksize,
                
                debug_mode=False,
                bypass=self.but_enable_bypass.isChecked(),
            )
        return params

    
    def setup_audio_stream(self):
        nb_channel = 2
        #~ nb_channel = 1
        sample_rate = 44100.
        params = self.params_for_processing()
        dtype='float32'
        
        self.processing = hls.InvCGC(nb_channel=nb_channel, sample_rate=sample_rate,
                dtype=dtype, apply_configuration_at_init=False, **params)
                
        self.processing.make_filters()
        
        self.processing.create_opencl_context(
                gpu_platform_index = self.gpu_platform_index,
                gpu_device_index = self.gpu_device_index,)
        self.processing.initlalize_cl()
        
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
            
            #~ print(params)
            t0 = time.perf_counter()
            self.processing.configure(**params)
            t1 = time.perf_counter()
            #~ print(t1-t0)
            self.processing.make_filters()
            t2 = time.perf_counter()
            #~ print(t2-t1)
            with self.mutex:        
                self.processing.initlalize_cl()
            t3 = time.perf_counter()
            #~ print(t3-t2)
            #~ print(t3-t0)                
            
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

