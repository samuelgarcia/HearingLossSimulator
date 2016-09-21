import pytest
import hearinglosssimulator as hls
from hearinglosssimulator.gui.mainwindow import MainWindow
import pyqtgraph as pg


def test_mainwindow():
    app = pg.mkQApp()
    win = MainWindow()
    win.show()
    app.exec_()    


if __name__ == '__main__':
    test_mainwindow()
