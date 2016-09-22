import PyQt5 # this force pyqtgraph to deal with Qt5
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
import numpy as np
import pyopencl

class GpuDeviceSelection(QtGui.QWidget):
    def __init__(self, parent = None):
        QtGui.QWidget.__init__(self, parent)
        mainlayout  =QtGui.QVBoxLayout()
        self.setLayout(mainlayout)

        mainlayout.addWidget(QtGui.QLabel(u'OpenCL Platform'))
        self.combo_platform = QtGui.QComboBox()
        mainlayout.addWidget(self.combo_platform)
        
        mainlayout.addWidget(QtGui.QLabel(u'OpenCL Device'))
        self.combo_dev = QtGui.QComboBox()
        mainlayout.addWidget(self.combo_dev)
        
        mainlayout.addStretch()
        
        self.resfresh_platform_list()
        self.combo_platform.currentIndexChanged.connect(self.resfresh_device_list)
    
    def set_configuration(self, platform_index = 0, device_index = 0):
        try: self.combo_platform.setCurrentIndex(platform_index)
        except: pass
        self.resfresh_platform_list()
        try: self.combo_dev.setCurrentIndex(device_index)
        except: pass

    
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

