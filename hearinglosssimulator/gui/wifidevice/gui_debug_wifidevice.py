
from hearinglosssimulator.gui.myqt import QT
import pyqtgraph as pg

import numpy as np
from hearinglosssimulator.gui.wifidevice.wifidevicewidget import WifiDeviceWidget
from hearinglosssimulator.gui.wifidevice.qwificlient import QWifiClient, ThreadAudioStream
from hearinglosssimulator.gui.wifidevice.wifideviceparameters import WifiDeviceParameter





class WindowDebugWifiDevice(QT.QWidget):
    def __init__(self, client=None, parent = None):
        QT.QWidget.__init__(self, parent)
        
        self.client = client
        
        self.resize(600,600)
        
        mainlayout  =QT.QVBoxLayout()
        self.setLayout(mainlayout)
        
        self.devicewidget = WifiDeviceWidget(client=client)
        mainlayout.addWidget(self.devicewidget)
        
        ##
        mainlayout.addWidget(QT.QLabel(u'<h1><b>Audio params</b>'))
        h = QT.QHBoxLayout()
        mainlayout.addLayout(h)
        but = QT.QPushButton('Get params from device')
        h.addWidget(but)
        but.clicked.connect(self.get_params_from_device)
        but = QT.QPushButton('Set params to device')
        h.addWidget(but)
        but.clicked.connect(self.set_params_to_device)
        self.wifiDeviceParameter = WifiDeviceParameter()
        mainlayout.addWidget(self.wifiDeviceParameter)
        
        ##
        mainlayout.addWidget(QT.QLabel(u'<h1><b>ssid</b>'))
        but = QT.QPushButton('Apply ssid')
        mainlayout.addWidget(but)
        but.clicked.connect(self.set_ssid)
        self.edit_ssid = QT.QLineEdit()
        mainlayout.addWidget(self.edit_ssid)
        
        ##
        mainlayout.addWidget(QT.QLabel(u'<h1><b>Audio loop</b>'))
        h = QT.QHBoxLayout()
        mainlayout.addLayout(h)
        but = QT.QPushButton('Start')
        h.addWidget(but)
        but.clicked.connect(self.start_audio)
        but = QT.QPushButton('Stop')
        h.addWidget(but)
        but.clicked.connect(self.stop_audio)
        
        self.thread_audio_loop = ThreadAudioStream(client.client_protocol,  parent=self)
        self.thread_audio_loop.connection_broken.connect(self.client.on_connection_broken)
        
    
    def get_params_from_device(self):
        sr = self.client.secure_call('get_sample_rate')
        lat = self.client.secure_call('get_audio_latency')
        speaker_gain = self.client.secure_call('get_speaker_gain')
        microphone_gain = self.client.secure_call('get_microphone_gain')
        
        #~ print(sr, lat, speaker_gain, microphone_gain)
        self.wifiDeviceParameter.set_configuration(
            nb_buffer_latency=lat,
            sample_rate=sr,
            speaker_gain=speaker_gain,
            microphone_gain=microphone_gain,
        )
        
        
    def set_params_to_device(self):
        p = self.wifiDeviceParameter.get_configuration()
        #~ self.client.secure_call('set_sample_rate', p['sample_rate'])
        self.client.secure_call('set_audio_latency', p['nb_buffer_latency'])
        self.client.secure_call('set_speaker_gain', p['speaker_gain'])
        self.client.secure_call('set_microphone_gain', p['microphone_gain'])
        
        print('send', p)
        
        self.devicewidget.refresh_label_param()
    
    def set_ssid(self):
        new_ssid = self.edit_ssid.text()
        if len(new_ssid)>0:
            print('apply_new_ssid', new_ssid)
            self.client.secure_call('set_ssid', new_ssid)
    
    def start_audio(self):
        if self.client.state == 'disconnected':
            print('oups disconnected')
        elif self.client.state.endswith('loop'):
            print('oups loop')
        elif self.client.state == 'connected':
            self.client.start_loop(self.thread_audio_loop, 'audio')
            self.devicewidget.timer_missing.start()
        
    def stop_audio(self):
            if self.client.state == 'disconnected':
                print('oups disconnected')
            elif self.client.state == 'audio-loop':
                self.client.stop_loop('audio')
            elif self.client.state == 'connected':
                print('oups not running')    
    
        
def test_WindowDebugWifiDevice():
    udp_ip = "192.168.1.1"
    udp_port = 6666
        
    
    import pyqtgraph as pg
    
    client = QWifiClient(udp_ip=udp_ip,  udp_port=udp_port)
    
    app = pg.mkQApp()
    win = WindowDebugWifiDevice(client=client)
    win.show()
    app.exec_()


if __name__ =='__main__':
    test_WindowDebugWifiDevice()