from .common_mainwindow import *

import numpy as np
import hearinglosssimulator.gui.wifidevice.packet_types as pt
from hearinglosssimulator.gui.wifidevice.qwificlient import QWifiClient, BaseThreadStream

from hearinglosssimulator.gui.wifidevice.wifidevicewidget import WifiDeviceWidget
from hearinglosssimulator.gui.wifidevice.wifideviceparameters import WifiDeviceParameter


"""
Calmibration date 2017-06-07

Note on calibration for the wifidevice and the headhone TechnoFirst:
  * microphone_gain=+20dB for a sinus (1000Hz, 76.7dBSPL) we have 26.5dBfs So calibration=103dB
  * speaker_gain=+0dB for a sinus (1000Hz, -10dBFs) wa have 77.9 dBSPL So calibration=88dB. Over this value wa have a gain saturation.

So we keep calibration=103.
This is OK for input and for output we add a fake gain of 15dB (=10**(15/20)=5.62) before sending output to the device.



"""


import time

udp_ip = "192.168.1.1"
udp_port = 6666

#for debug
from hearinglosssimulator.gui.myqt import DebugDecorator


calibration = 103
output_gain_compensation = 2**(15./20.)

def apply_gain_and_cast(sound_buffer):
    """
    This apply the gain due to calibration clip and cast.
    """
    if sound_buffer.dtype ==np.dtype('int16'):
        sound_buffer =sound_buffer.astype('float32')
    else:
        sound_buffer = sound_buffer * 2**15
    
    sound_buffer *= output_gain_compensation
    
    sound_buffer[sound_buffer>(2**15-1)] = 2**15-1
    sound_buffer[sound_buffer<(-2**15+1)] = -2**15+1
    
    return sound_buffer.astype('int16')
    
    
    
    
    
    

class ThreadSimulatorAudioStream(BaseThreadStream):
    
    
    def initialize_loop(self):
        
        self.index = 0
        self.empty_out = np.zeros((256, 2), dtype='int16')
        
        if self.processing is None:
            self.bypass = True
        else:
            self.bypass = self.processing.bypass
        
        print('initialize_loop')
        

    def finalize_loop(self):
        pass
    
    def process_one_packet(self, header, data_buffer_in):
        #~ print('process_one_packet')
        packet_type = pt.AUDIO_DATA
        option = header['option']
        with self.lock:
            if self.bypass:
                #~ print('process_one_packet bypass')
                sound_in_int = np.frombuffer(data_buffer_in, dtype='int16')
                sound_out_int = apply_gain_and_cast(sound_in_int)
                
            else:
                #~ t0 = time.perf_counter()
                #~ print('process_one_packet nobypass')
                sound_in_float = np.frombuffer(data_buffer_in, dtype='int16').astype('float32').reshape(256, 2)
                sound_in_float /= 2**15
                self.index += 256
                #~ print('self.index', self.index, sound_in_float.shape)
                #~ t2 = time.perf_counter()
                returns = self.processing.proccesing_func(self.index, sound_in_float)
                index2, sound_out_float = returns['main_output']
                
                #~ t3 = time.perf_counter()
                
                #~ print('index2', index2)
                if index2 is not None:
                    sound_out_int = apply_gain_and_cast(sound_out_float)
                else:
                    sound_out_int = self.empty_out
                
                
                #~ t1 = time.perf_counter()
                #~ print(int(t2*10000-t0*10000)/10, 'ms')
                
                #~ print(int(t3*10000-t2*10000)/10, 'ms')
                #~ print(int(t1*10000-t3*10000)/10, 'ms')
                #~ print('tot', int(t1*10000-t0*10000)/10, 'ms')
                #~ print()
                #~ print(t1-t0, 's')
        
        variable = sound_out_int.tobytes()
        return packet_type, option, variable
    
    def set_processing(self, processing):
        with self.lock:
            self.processing = processing
            if self.processing is not None:
                self.bypass = self.processing.bypass
    
    def set_bypass(self, bypass):
        print('set_bypass in thread', bypass)
        with self.lock:
            self.processing.set_bypass(bypass)
            self.bypass = bypass
    
    


class WifiDeviceMainWindow(CommonMainWindow):
    
    _prefix_application = 'WifiDevice_'
    
    def __init__(self, parent = None):
        CommonMainWindow.__init__(self, parent)
        
        self.client = QWifiClient(udp_ip, udp_port, debug=False)
        self.client.state_changed.connect(self.on_state_changed)
        
        self.thread_simulator = ThreadSimulatorAudioStream(self.client.client_protocol, parent=self.client)
        self.thread_simulator.connection_broken.connect(self.client.on_connection_broken)
        self.thread_simulator.set_processing(None)
        
        self.simulatorParameter = SimulatorParameter(with_all_params=False, parent=self)
        self.gpuDeviceSelection = GpuDeviceSelection(parent=self)
        self.wifiDeviceParameter = WifiDeviceParameter(parent=self)
        
        self.createActions()
        self.createToolBars()
        
        # central layout
        self.resize(1000,800)
        v = self.firstlayout
        
        v.insertWidget(0, QT.QLabel(u'<h1><b>Wifi Device State/Conf</b>'))
        self.devicewidget = WifiDeviceWidget(self.client, parent=self)
        v.insertWidget (1,  self.devicewidget)


        #~ self.mainlayout.addWidget(QT.QLabel(u'<h1><b>Setup loss on each ear</b>'))
        #~ self.hearingLossParameter = HearingLossParameter()
        #~ self.mainlayout.addWidget(self.hearingLossParameter)
        
        v = QT.QVBoxLayout()
        self.mainlayout.addLayout(v)
        
        v.addWidget(QT.QLabel(u'<h1><b>Setup loss on each ear</b>'))
        self.hearingLossParameter = HearingLossParameter()
        v.addWidget(self.hearingLossParameter)


        #~ self.mainlayout.addStretch()

        self.configuration_elements = { 'wifidevice' : self.wifiDeviceParameter,
                                                'hearingloss' : self.hearingLossParameter,
                                                'gpudevice' : self.gpuDeviceSelection,
                                                'simulator_wifi' :  self.simulatorParameter,
                                                }
        self.load_configuration()        
        
        #~ self.showFullScreen()
        self.showMaximized()


    def createActions(self):
        self.actions = OrderedDict()
        

        
        self.dialogs = OrderedDict([
                                ('Simulator', {'widget' :self.simulatorParameter}),
                                ('Configure GPU', {'widget' :self.gpuDeviceSelection}), 
                                ('Wifi Device', {'widget' :self.wifiDeviceParameter}),
                                
                            ])
        
        for name, attr in self.dialogs.items():
            act = self.actions[name] = QT.QAction(name, self, checkable = False) #, icon =QT.QIcon(':/TODO.png'))
            act.triggered.connect(self.open_dialog)
            attr['action'] = act
            attr['widget'].setWindowFlags(QT.Qt.Window)
            attr['widget'].setWindowModality(QT.Qt.NonModal)
            attr['dia'] = dia = QT.QDialog()
            layout  = QT.QVBoxLayout()
            dia.setLayout(layout)
            layout.addWidget(attr['widget'])

    def createToolBars(self):
        self.toolbar = QT.QToolBar()
        self.toolbar.setToolButtonStyle(QT.Qt.ToolButtonTextUnderIcon)
        self.addToolBar(self.toolbar)
        self.toolbar.setIconSize(QT.QSize(60, 40))
        
        for name, act in self.actions.items():
            self.toolbar.addAction(act)
            
    
    def on_state_changed(self, new_state):
        if new_state=='disconnected':
            if self.but_start_stop.isChecked():
                self.but_start_stop.setChecked(False)
            self.but_start_stop.setEnabled(False)
            #~ self.but_enable_bypass.setEnabled(False)
        elif new_state=='connected':
            self.but_start_stop.setEnabled(True)
            #~ self.but_enable_bypass.setEnabled(True)

    def running(self):
        return self.client.state=='audio-loop'

    def after_dialog(self):
        try:
            self.check_wifi_params()
            self.devicewidget.refresh_label_param()
        except:
            pass
    
    @property
    def sample_rate(self):
        return self.wifiDeviceParameter.get_configuration()['sample_rate']
        #~ return 44100.
    
    def check_wifi_params(self):
        # check is sample_rate and latency have change
        # if yes reset
        print('check_wifi_params')
        actual_conf = self.wifiDeviceParameter.get_configuration()
        #~ print('actual_conf', actual_conf)
        
        
        flag = True
        
        #~ print('sr', sr, 'lat', lat, type(lat))
        
        #sample_rate
        sr = self.client.secure_call('get_sample_rate')
        if sr is None:
            #an error occured
            return False
        if sr!=actual_conf['sample_rate']:
            flag = False
            self.warn('params', 'audio conf have change need wifi reset, please reconnect wifi')
            self.client.secure_call('set_sample_rate', actual_conf['sample_rate'])
        
        #latency
        lat = self.client.secure_call('get_audio_latency')
        if lat is None:
            #an error occured
            return False
        if lat!=actual_conf['nb_buffer_latency']:
            flag = False
            self.warn('params', 'audio conf have change need wifi reset, please reconnect wifi')
            self.client.secure_call('set_audio_latency', actual_conf['nb_buffer_latency'])
        

        #latency
        speaker_gain = self.client.secure_call('get_speaker_gain')
        if speaker_gain is None:
            #an error occured
            return False
        if speaker_gain!=actual_conf['speaker_gain']:
            flag = False
            self.warn('params', 'audio conf have change need wifi reset, please reconnect wifi')
            self.client.secure_call('set_speaker_gain', actual_conf['speaker_gain'])

        #latency
        microphone_gain = self.client.secure_call('get_microphone_gain')
        if microphone_gain is None:
            #an error occured
            return False
        if microphone_gain!=actual_conf['microphone_gain']:
            flag = False
            self.warn('params', 'audio conf have change need wifi reset, please reconnect wifi')
            self.client.secure_call('set_microphone_gain', actual_conf['microphone_gain'])
        
        
        print(sr, lat, speaker_gain, microphone_gain)
        return flag
        
    
    #~ @DebugDecorator
    def start_stop_audioloop(self, checked):
        #~ a = 0/0
        print('start_stop_audioloop', checked)
        
        if checked:
            if self.client.state == 'disconnected':
                print('oups disconnected')
                self.but_start_stop.setChecked(False)
            elif self.client.state.endswith('loop'):
                print('oups loop')
            elif self.client.state == 'connected':
                if self.check_wifi_params():
                    self.client.start_loop(self.thread_simulator, 'audio')
                    self.devicewidget.timer_missing.start()
                else:
                    self.but_start_stop.setChecked(False)
        else:
            if self.client.state == 'disconnected':
                print('oups disconnected')
                #~ self.but_start_stop.setChecked(False)
            elif self.client.state == 'audio-loop':
                self.client.stop_loop('audio')
            elif self.client.state == 'connected':
                print('oups not running')
    
    def setup_processing(self):
        print('setup_processing')
        # take from UI
        
        loss_params = self.hearingLossParameter.get_configuration()
        
        #DEBUG
        #~ loss_params = { 'left' : {'freqs' : [ 125*2**i  for i in range(7) ], 'compression_degree': [0]*7, 'passive_loss_db' : [0]*7 } }
        #~ loss_params['right'] = loss_params['left']
        
        simulator_params = self.simulatorParameter.get_configuration()
        simulator_engine = simulator_params.pop('simulator_engine')
        simulator_params['chunksize'] =  256
        simulator_params['backward_chunksize'] =  256+1024
        simulator_params['nb_channel'] =  2
        
        print('simulator_engine', simulator_engine)
        print(simulator_params)
        
        #make params
        params ={}
        params.update(simulator_params)
        params['calibration'] = calibration
        params['loss_params'] = loss_params
        params['bypass'] = self.but_enable_bypass.isChecked()
        print('bypass:', params['bypass'])
        classes = {'InvCGC': hls.InvCGC, 'InvComp': hls.InvComp}
        _Class = classes[simulator_engine]
        #~ print(_Class)
        
        print(self.sample_rate)
        self.processing = _Class(sample_rate=self.sample_rate, 
                    apply_configuration_at_init=False, use_filter_cache=True,
                    debug_mode=False, **params)
        
        platform_index = self.gpuDeviceSelection.get_configuration()['platform_index']
        device_index = self.gpuDeviceSelection.get_configuration()['device_index']
        self.processing.create_opencl_context(
                gpu_platform_index = platform_index,
                gpu_device_index = device_index)

        
        self.processing.initialize()
        
        self.thread_simulator.set_processing(self.processing)
    
    def setup_audio_stream(self):
        pass

    def set_bypass(self, bypass):
        if self.processing is None:
            self.thread_simulator.set_bypass(True)
        else:
            self.thread_simulator.set_bypass(bypass)
    
    def compute_filters(self):
        print('compute_filters')
        with self.mutex:
            try:
                self.setup_processing()
                self.setup_audio_stream()
            except Exception as e:
                print(e)
                
            else:
                #~ self.but_start_stop.setEnabled(True)
                self.but_enable_bypass.setEnabled(True)
    

