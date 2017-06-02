from .common_mainwindow import *

import numpy as np
import hearinglosssimulator.gui.wifidevice.packet_types as pt
from hearinglosssimulator.gui.wifidevice.qwificlient import QWifiClient, BaseThreadStream

from hearinglosssimulator.gui.wifidevice.wifidevicewidget import WifiDeviceWidget



udp_ip = "192.168.1.1"
udp_port = 6666



class ThreadSimulatorAudioStream(BaseThreadStream):
    
    
    def initialize_loop(self):
        
        self.index = 0
        self.empty_out = np.zeros((256, 2), dtype='int16')
        print('initialize_loop')
        

    def finalize_loop(self):
        pass
    
    def process_one_packet(self, header, data):
        print('process_one_packet')
        packet_type = pt.AUDIO_DATA
        option = header['option']
        with self.lock:
            if self.processing.bypass:
                print('process_one_packet bypass')
                variable = data
            else:
                print('process_one_packet nobypass')
                data_float = np.frombuffer(data, dtype='int16').astype('float32').reshape(256, 2)
                data_float /= 2**15
                self.index += 256
                returns = self.processing.proccesing_func(self.index, data_float)
                index2, data_out = returns['main_output']
                if index2 is not None:
                    data_out_int = (data_out*2**15).astype('int16')
                else:
                    data_out_int = self.empty_out
                
                variable = data_out_int.tobytes()
            
        return packet_type, option, variable
    
    def set_processing(self, processing):
        with self.lock:
            self.processing = processing
    
    def set_bypass(self, bypass):
        print('set_bypass in thread', bypass)
        with self.lock:
            self.processing.set_bypass(bypass)
    
    


class WifiDeviceMainWindow(CommonMainWindow):
    def __init__(self, parent = None):
        CommonMainWindow.__init__(self, parent)
        
        self.client = QWifiClient(udp_ip, udp_port, debug=False)
        self.client.state_changed.connect(self.on_state_changed)
        
        self.thread_simulator = ThreadSimulatorAudioStream(self.client.client_protocol, parent=self.client)
        self.thread_simulator.connection_broken.connect(self.client.on_connection_broken)
        
        
        
        self.resize(800, 600)
        
        # central layout
        self.mainlayout.insertWidget(0, QT.QLabel(u'<h1><b>Wifi Device State/Conf</b>'))
        self.devicewidget = WifiDeviceWidget(self.client, parent=self)
        self.mainlayout.insertWidget (1,  self.devicewidget)

        self.mainlayout.addStretch()
    
    
    def on_state_changed(self, new_state):
        if new_state=='disconnected':
            if self.but_start_stop.isChecked():
                self.but_start_stop.setChecked(False)
            self.but_start_stop.setEnabled(False)
            self.but_enable_bypass.setEnabled(False)
        elif new_state=='connected':
            self.but_start_stop.setEnabled(True)
            self.but_enable_bypass.setEnabled(True)

    def running(self):
        return self.client.state=='audio-loop'
    
    @property
    def sample_rate(self):
        return 44100.

    def start_stop_audioloop(self, checked):
        print('start_stop_audioloop', checked)
        
        if checked:
            if self.client.state == 'disconnected':
                print('oups disconnected')
                self.but_start_stop.setChecked(False)
            elif self.client.state.endswith('loop'):
                print('oups loop')
            elif self.client.state == 'connected':
                self.client.start_loop(self.thread_simulator, 'audio')
                self.devicewidget.timer_missing.start()
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
        #~ print(params)
        classes = {'InvCGC': hls.InvCGC, 'InvComp': hls.InvComp}
        _Class = classes[simulator_engine]
        #~ print(_Class)
        
        #~ print(self.sample_rate)
        self.processing = _Class(sample_rate=self.sample_rate, 
                    apply_configuration_at_init=False, use_filter_cache=True,
                    debug_mode=False, **params)
        
        #~ self.processing.create_opencl_context(
                #~ gpu_platform_index = self.gpu_platform_index,
                #~ gpu_device_index = self.gpu_device_index,)
        
        self.processing.initialize()
        
        self.thread_simulator.set_processing(self.processing)
    
    def setup_audio_stream(self):
        pass

    def set_bypass(self, bypass):
        self.thread_simulator.set_bypass(bypass)



