from .common_mainwindow import *


import hearinglosssimulator.gui.wifidevice.packet_types as pt
from hearinglosssimulator.gui.wifidevice.qwificlient import QWifiClient, ThreadAudioStream


udp_ip = "192.168.1.1"
udp_port = 6666

class WifiDeviceMainWindow(QT.QMainWindow):
    def __init__(self, parent = None):
        QT.QMainWindow.__init__(self, parent)
        
        self.client = QWifiClient(udp_ip, udp_port, debug=False)
        
        


    def running(self):
        pass
        #~ if not self.audio_stream_done:
            #~ return False
        
        #~ return self.stream.active


    def start_stop_audioloop(self, checked):
        pass
        #~ if checked:
            #~ self.stream.start()
        #~ else:
            #~ self.stream.stop()
    