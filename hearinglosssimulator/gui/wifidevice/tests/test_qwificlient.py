

from hearinglosssimulator.gui.wifidevice.wifidevicewidget import WifiDeviceWidget
from hearinglosssimulator.gui.wifidevice.qwificlient import QWifiClient, ThreadAudioStream
from hearinglosssimulator.gui.wifidevice.gui_debug_wifidevice import WindowDebugWifiDevice


udp_ip = "192.168.1.1"
udp_port = 6666

def test_qwificlient():
    
    import pyqtgraph as pg
    
    client = QWifiClient(udp_ip=udp_ip,  udp_port=udp_port)
    
    app = pg.mkQApp()
    win = WindowDebugWifiDevice(client=client)
    win.show()
    app.exec_()


if __name__ =='__main__':
    test_qwificlient()

