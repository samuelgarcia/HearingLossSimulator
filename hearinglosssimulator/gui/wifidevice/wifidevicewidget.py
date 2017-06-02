from ..myqt import QT
#~ import pyqtgraph as pg

from .protocol import ClientProtocol

from hearinglosssimulator.gui.wifidevice.qwificlient import QWifiClient, ThreadAudioStream



class WifiDeviceWidget(QT.QWidget):
    def __init__(self, client, parent=None):
        QT.QWidget.__init__(self, parent=parent)
        
        self.client = client
        
        mainlayout  =QT.QVBoxLayout()
        self.setLayout(mainlayout)
        
        self.label_state = QT.QLabel('disconnected')
        mainlayout.addWidget(self.label_state)
        
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
        
        self.client.try_connection()

        
        #~ self.client.insound_ready.connect(self.on_insound_ready)
        
        
    def on_state_changed(self, new_state):
        self.label_state.setText(new_state)
        
        if new_state=='connected':
            #~ self.timer_gains.start()
            self.timer_missing.stop()
            #~ self.setEnabled(True)
        elif new_state=='disconnected':
            #~ self.timer_gains.stop()
            self.timer_missing.stop()
            #~ self.setEnabled(False)
        elif 'loop' in new_state:
            #~ self.timer_gains.stop()
            self.timer_missing.start()
            #~ self.setEnabled(True)
    
    
    def refresh_missing_label(self):
        #~ print('refresh_missing_label')
        if self.client.active_thread is None:
            return
        
        n1 = self.client.active_thread.nb_missing_up
        n2 = self.client.active_thread.nb_too_late
        n3 = self.client.active_thread.nb_missing_dw
        self.label_missing.setText('Missing packet up{:6}\nMissing too late {:6}\nMissing packet dw{:6}\n'.format(n1, n2,  n3))
    
