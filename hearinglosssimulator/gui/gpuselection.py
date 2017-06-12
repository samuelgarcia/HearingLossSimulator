from hearinglosssimulator.gui.myqt import QT
import pyqtgraph as pg

import numpy as np
import pyopencl

class GpuDeviceSelection(QT.QWidget):
    def __init__(self, parent = None):
        QT.QWidget.__init__(self, parent)
        mainlayout  =QT.QVBoxLayout()
        self.setLayout(mainlayout)

        mainlayout.addWidget(QT.QLabel(u'OpenCL Platform'))
        self.combo_platform = QT.QComboBox()
        mainlayout.addWidget(self.combo_platform)
        
        mainlayout.addWidget(QT.QLabel(u'OpenCL Device'))
        self.combo_dev = QT.QComboBox()
        mainlayout.addWidget(self.combo_dev)
        
        mainlayout.addStretch()
        
        self.resfresh_platform_list()
        self.combo_platform.currentIndexChanged.connect(self.resfresh_device_list)
        
        if len(pyopencl.get_platforms())>0:
            self.resfresh_device_list(0)
    
    def set_configuration(self, platform_index = 0, device_index = 0):
        self.combo_platform.currentIndexChanged.disconnect(self.resfresh_device_list)
        try: 
            self.combo_platform.setCurrentIndex(platform_index)
        except: 
            pass
        try:
            self.resfresh_device_list(platform_index)
        except:
            pass
        try:
            self.combo_dev.setCurrentIndex(device_index)
        except: 
            pass
        self.combo_platform.currentIndexChanged.connect(self.resfresh_device_list)
    
    def get_configuration(self):
        config = {'platform_index': int(self.combo_platform.currentIndex()),
                        'device_index':int(self.combo_dev.currentIndex()),
                        }
        return config
    
    def resfresh_platform_list(self):
        self.combo_platform.clear()
        for i, platform in enumerate(pyopencl.get_platforms()):
            self.combo_platform.addItem(u'{}: {}'.format(i, platform.name))
        
    def resfresh_device_list(self, platform_index):
        self.combo_dev.clear()
        platform = pyopencl.get_platforms()[platform_index]
        
        for i, dev in enumerate(platform.get_devices()):
            self.combo_dev.addItem(u'{}: {}'.format(i, dev.name))




if __name__ == '__main__':
    app = pg.mkQApp()
    win = GpuDeviceSelection()
    win.show()
    app.exec_()
    print(win.get_configuration())

