import PyQt5 # this force pyqtgraph to deal with Qt5
from hearinglosssimulator.gui.mainwindow import MainWindow
import pyqtgraph as pg


if __name__ == '__main__':
    app = pg.mkQApp()
    win = MainWindow()
    win.show()
    app.exec_()    
