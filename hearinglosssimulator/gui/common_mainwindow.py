from .myqt import QT
import pyqtgraph as pg

import os, sys
import json
import time

from collections import OrderedDict

import sounddevice as sd

#~ import pyacq

import hearinglosssimulator as hls

from .lossparameters import HearingLossParameter
from .calibration import Calibration
from .audioselection import AudioDeviceSelection
from .gpuselection import GpuDeviceSelection
from .simulatorparameters import SimulatorParameter



class Mutex(QT.QMutex):
    def __exit__(self, *args):
        self.unlock()

    def __enter__(self):
        self.lock()
        return self



class CommonMainWindow(QT.QMainWindow):
    def __init__(self, parent = None):
        QT.QMainWindow.__init__(self, parent)
        
        self.setWindowTitle(u'Hearing loss simulator')
        #~ self.setWindowIcon(QT.QIcon(':/TODO.png'))
        
        self.mutex = Mutex()

    
    def flash_icon(self):
        if self.running():
            self.flag_icon = not(self.flag_icon)
            if self.flag_icon:
                self.but_start_stop.setIcon(QT.QIcon.fromTheme(''))
            else:
                self.but_start_stop.setIcon(QT.QIcon.fromTheme('media-playback-start'))
        else:
            self.but_start_stop.setIcon(QT.QIcon.fromTheme('media-playback-stop'))


    def warn(self, title, text):
        mb = QT.QMessageBox.warning(self, title,text, 
                QT.QMessageBox.Ok ,  QT.QMessageBox.Default  | QT.QMessageBox.Escape,
                QT.QMessageBox.NoButton)

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



    
    

    def enable_bypass_simulator(self, checked):
        self.processing.set_bypass(checked)
        if checked:
            self.but_enable_bypass.setIcon(QT.QIcon.fromTheme('process-stop'))
        else:
            self.but_enable_bypass.setIcon(QT.QIcon.fromTheme(''))
            

