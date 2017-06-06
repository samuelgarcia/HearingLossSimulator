from .common_mainwindow import *

import numpy as np
import hearinglosssimulator.gui.wifidevice.packet_types as pt
from hearinglosssimulator.gui.wifidevice.qwificlient import QWifiClient, BaseThreadStream

from hearinglosssimulator.gui.wifidevice.wifidevicewidget import WifiDeviceWidget
from hearinglosssimulator.gui.wifidevice.wifideviceparameters import WifiDeviceParameter


import time

udp_ip = "192.168.1.1"
udp_port = 6666

def DebugDecorator(func):
    def wrapper(*args, **kargs):
        print('DebugDecorator', *args, *kargs)
        try:
            ret = func(*args, **kargs)
            return ret
        except Exception as e:
            print('#'*20)
            print('# ERROR IN {}'.format(func) * 5 )
            print('#', e)
            print('#'*20)
    return wrapper    
    

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
    
    def process_one_packet(self, header, data):
        print('process_one_packet')
        packet_type = pt.AUDIO_DATA
        option = header['option']
        with self.lock:
            if self.bypass:
                print('process_one_packet bypass')
                variable = data
            else:
                t0 = time.perf_counter()
                print('process_one_packet nobypass')
                data_float = np.frombuffer(data, dtype='int16').astype('float32').reshape(256, 2)
                data_float /= 2**15
                self.index += 256
                print('self.index', self.index, data_float.shape)
                returns = self.processing.proccesing_func(self.index, data_float)
                index2, data_out = returns['main_output']
                print('index2', index2)
                if index2 is not None:
                    data_out_int = (data_out*2**15).astype('int16')
                else:
                    data_out_int = self.empty_out
                
                variable = data_out_int.tobytes()
                t1 = time.perf_counter()
                #~ print(int(t1-t0)*1000/1000., 'ms')
                print(t1-t0, 's')
            
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
        self.resize(800, 600)
        self.mainlayout.insertWidget(0, QT.QLabel(u'<h1><b>Wifi Device State/Conf</b>'))
        self.devicewidget = WifiDeviceWidget(self.client, parent=self)
        self.mainlayout.insertWidget (1,  self.devicewidget)

        self.mainlayout.addStretch()

        self.configuration_elements = { 'wifidevice' : self.wifiDeviceParameter,
                                                #~ 'hearingloss' : self.hearingLossParameter,
                                                'gpudevice' : self.gpuDeviceSelection,
                                                'simulator_wifi' :  self.simulatorParameter,
                                                }
        self.load_configuration()        
        


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
        calibration = 100. #TODO put 
        
        #~ loss_params = self.hearingLossParameter.get_configuration()
        
        #DEBUG
        loss_params = { 'left' : {'freqs' : [ 125*2**i  for i in range(7) ], 'compression_degree': [0]*7, 'passive_loss_db' : [0]*7 } }
        loss_params['right'] = loss_params['left']
        
        #~ simulator_params = self.simulatorParameter.get_configuration()
        #~ simulator_engine = simulator_params.pop('simulator_engine')
        simulator_params =  dict(chunksize=256, backward_chunksize=256+1024, nb_channel=2)
        simulator_engine = 'InvComp'
        
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
        
        #~ print(self.sample_rate)
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
    

