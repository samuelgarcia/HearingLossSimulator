from ..myqt import QT
#~ import pyqtgraph as pg

from .protocol import ClientProtocol

from hearinglosssimulator.gui.wifidevice.qwificlient import QWifiClient, ThreadAudioStream



class WifiDeviceWidget(QT.QWidget):
    def __init__(self, client, parent=None):
        QT.QWidget.__init__(self, parent=parent)
        
        self.client = client
        
        mainlayout  =QT.QHBoxLayout()
        self.setLayout(mainlayout)
        
        self.label_state = QT.QLabel('')
        mainlayout.addWidget(self.label_state)
        
        

        self.label_param = QT.QLabel('')
        mainlayout.addWidget(self.label_param)
        
        self.label_missing = QT.QLabel('')
        mainlayout.addWidget(self.label_missing)
        
        self.nb_missing_up = 0
        self.nb_too_late = 0
        self.nb_missing_dw = 0
        
        #~ self.timer_gains = QT.QTimer(singleShot=True, interval=100)
        #~ self.timer_gains.timeout.connect(self.refresh_gains_latency)
        #~ self.timer_gains.timeout.connect(self.refresh_ssid)
        
        self.timer_missing = QT.QTimer(singleShot=False, interval=100)
        self.timer_missing.timeout.connect(self.refresh_missing_label)
        

        self.client.state_changed.connect(self.on_state_changed)
        
        #~ self.setEnabled(False)
        
        self.refresh_label_state('disconnected')
        self.client.try_connection()

        
        #~ self.client.insound_ready.connect(self.on_insound_ready)
        
        
    def on_state_changed(self, new_state):
        #~ self.label_state.setText(new_state)
        
        if new_state=='connected':
            #~ self.timer_gains.start()
            self.timer_missing.stop()
            #~ self.setEnabled(True)
            self.refresh_label_param()
        elif new_state=='disconnected':
            #~ self.timer_gains.stop()
            self.timer_missing.stop()
            #~ self.setEnabled(False)
        elif 'loop' in new_state:
            #~ self.timer_gains.stop()
            self.timer_missing.start()
            #~ self.setEnabled(True)
        
        self.refresh_label_state(new_state)
    
    def refresh_label_state(self, new_state):
        
        #~ text = 'Wifi :{}'.format(new_state)
        img = {'connected': 'led-green.png',
                'disconnected': 'led-red.png',
                'audio-loop': 'led-blue.png',
                
                }.get(new_state, '')
        text = "<html><img src=':/{img}' height='42' width='42'><p>{state}</p></html>".format(img=img, state=new_state)
        
        self.label_state.setText(text)
    
    def refresh_label_param(self):
        sr = self.client.secure_call('get_sample_rate')
        nb_lat = self.client.secure_call('get_audio_latency')
        ssid = self.client.secure_call('get_ssid')
        latency = nb_lat * 256 /sr*1000
        text = 'ssid: {}\n sample_rate: {} \n nb_buffer_latency: {}  \n latency: {:.1f}ms'.format(ssid, sr, nb_lat,latency)
        self.label_param.setText(text)
    
    def refresh_missing_label(self):
        #~ print('refresh_missing_label')
        if self.client.active_thread is None:
            return
        
        n1 = self.client.active_thread.nb_missing_up
        n2 = self.client.active_thread.nb_too_late
        n3 = self.client.active_thread.nb_missing_dw
        self.label_missing.setText('Missing packet up{:6}\nMissing too late {:6}\nMissing packet dw{:6}\n'.format(n1, n2,  n3))
    
