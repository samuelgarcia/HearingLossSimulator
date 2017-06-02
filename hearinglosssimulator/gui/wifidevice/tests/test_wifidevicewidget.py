

from hearinglosssimulator.gui.wifidevice.wifidevicewidget import WifiDeviceWidget
from hearinglosssimulator.gui.wifidevice.qwificlient import QWifiClient, ThreadAudioStream


udp_ip = "192.168.1.1"
udp_port = 6666

def test_wifidevicewidget():
    
    import pyqtgraph as pg
    
    client = QWifiClient(udp_ip=udp_ip,  udp_port=udp_port)
    
    app = pg.mkQApp()
    win = WifiDeviceWidget(client=client)
    win.show()
    app.exec_()


if __name__ =='__main__':
    test_wifidevicewidget()


