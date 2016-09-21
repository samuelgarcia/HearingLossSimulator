import PyQt5 # this force pyqtgraph to deal with Qt5
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
import numpy as np
import scipy.interpolate
import json


_default_bands = [ {'freq' : np.ceil(100*((2**(1./3.))**i)), 'db_loss': 0.}  for i in range(20) ]


class Band(QtGui.QWidget):
    valueChanged = QtCore.Signal()
    def __init__(self, parent = None):
        QtGui.QWidget.__init__(self, parent)
        mainlayout  = QtGui.QVBoxLayout()
        self.setLayout(mainlayout)
        mainlayout.setContentsMargins(1,1,1,1)
        
        self.db_label = QtGui.QLabel(u'')
        mainlayout.addWidget(self.db_label)
        self.slider_db_loss = QtGui.QSlider(orientation = QtCore.Qt.Vertical, minimum = -60, maximum = 0, minimumHeight = 100)
        mainlayout.addWidget(self.slider_db_loss)
        self.spinbox_freq = QtGui.QSpinBox(minimum = 50, maximum = 8000, minimumWidth = 5, maximumWidth = 55, maximumHeight = 18)
        font = QtGui.QFont()
        font.setPointSize(7)
        self.spinbox_freq.setFont(font)
        mainlayout.addWidget(self.spinbox_freq)
        
        #~ mainlayout.setAlignment(QtCore.Qt.AlignHCenter)
        mainlayout.setAlignment(self.slider_db_loss, QtCore.Qt.AlignHCenter)
        mainlayout.setAlignment(self.db_label, QtCore.Qt.AlignHCenter)
        
        self.slider_db_loss.valueChanged.connect(self.refresh_label)
        self.slider_db_loss.valueChanged.connect(self.valueChanged.emit)
        self.spinbox_freq.valueChanged.connect(self.valueChanged.emit)
        
        self.refresh_label(0)
    
    def set(self, freq = 1000., db_loss = 0.):
        self.slider_db_loss.setValue(int(db_loss))
        self.spinbox_freq.setValue(int(freq))
        
    def get(self):
        return {
                        'db_loss' : float(self.slider_db_loss.value()),
                        'freq' : float(self.spinbox_freq.value()),
                    }
    
    def refresh_label(self, value):
        self.db_label.setText(u'{} dB'.format(value))


class OneEq(QtGui.QWidget):
    valueChanged = QtCore.Signal()
    def __init__(self, parent = None, band_values = _default_bands ):
        QtGui.QWidget.__init__(self, parent)
        self.mainlayout  = QtGui.QHBoxLayout()
        self.setLayout(self.mainlayout)
        self.mainlayout.setSpacing(0)
        
        self.band_widgets = []
        
        self.set(band_values)
    
    def set(self, band_values):
        for band_widget in self.band_widgets:
            self.mainlayout.removeWidget(band_widget)
            band_widget.deleteLater()
            band_widget.setParent(None)
        
        self.band_widgets = []
        for band_value in band_values:
            w = Band()
            w.valueChanged.connect(self.valueChanged.emit)
            self.mainlayout.addWidget(w)
            w.set(**band_value)
            self.band_widgets.append(w)

    def get(self):
        band_values = [w.get() for w in self.band_widgets]
        return band_values


class MyViewBox(pg.ViewBox):
    def __init__(self, *args, **kwds):
        pg.ViewBox.__init__(self, *args, **kwds)
        self.disableAutoRange()
    def mouseClickEvent(self, ev):
        ev.accept()
    def mouseDoubleClickEvent(self, ev):
        ev.accept()
    def mouseDragEvent(self, ev):
        ev.ignore()
    def wheelEvent(self, ev):
        ev.accept()


class HearingLossParameter(QtGui.QWidget):
    valueChanged = QtCore.Signal()
    def __init__(self, parent = None):
        QtGui.QWidget.__init__(self, parent)
        mainlayout = QtGui.QVBoxLayout()
        self.setLayout(mainlayout)
        
        h = QtGui.QHBoxLayout()
        mainlayout.addLayout(h)
        but = QtGui.QPushButton(u'Set flat')
        h.addWidget(but)
        but.clicked.connect(self.set_flat)
        but = QtGui.QPushButton(u'Load')
        h.addWidget(but)
        but.clicked.connect(self.load)
        but = QtGui.QPushButton(u'Save')
        h.addWidget(but)
        but.clicked.connect(self.save)
        
        ears = ('left', 'right')
        self.eqs =[ ]
        for i, ear in enumerate(ears):
            eq = OneEq()
            self.eqs.append(eq)
            mainlayout.addWidget(QtGui.QLabel(u'<h1><b>{}</b>'.format(ear)))
            mainlayout.addWidget(eq)
            eq.valueChanged.connect(self.refresh_curves)
            eq.valueChanged.connect(self.valueChanged.emit)
        
        self.viewBox = MyViewBox()
        self.graphicsview  = pg.GraphicsView()
        mainlayout.addWidget(self.graphicsview)
        self.plot = pg.PlotItem(viewBox = self.viewBox)
        #~ self.plot.setLogMode(x=True, y = False)
        self.graphicsview.setCentralItem(self.plot)
        
        for i, ear in enumerate(ears):
            color = ['#FF0000', '#00FF00'][i]
            curve = pg.PlotCurveItem(pen = color)
            self.plot.addItem(curve)
        self.set_configuration()
    
    def set_configuration(self, loss_weigth = [_default_bands]*2,):
        assert len(loss_weigth) ==2
        for i, one_loss in enumerate(loss_weigth):
            self.eqs[i].set(one_loss)
        self.refresh_curves()
    
    def get_configuration(self):
        config = {'loss_weigth' : [ eq.get() for eq in self.eqs] }
        # TODO classer freqs
        return config

    def refresh_curves(self):
        loss_weigth = self.get_configuration()['loss_weigth']
        for i in range(2):
            freqs = [0., ]
            db_loss = [0., ]
            for v in loss_weigth[i]:
                freqs.append(v['freq'])
                db_loss.append(v['db_loss'])
            freqs += [23000., ]
            db_loss += [0., ]                
            freqs  = np.array(freqs)
            db_loss  = np.array(db_loss)
            f = scipy.interpolate.interp1d(freqs, db_loss, kind='linear')
            x =np.arange(50,22000, 10)
            self.plot.items[i].setData(x, f(x))
            
        self.plot.setXRange(0, 23000)
        self.plot.setYRange(-80, 0.)
    
    def set_flat(self):
        for eq in self.eqs:
            eq.set(_default_bands)
            #~ loss = eq.get()
            #~ for e in loss:
                #~ e['db_loss'] = 0.
            #~ eq.set(loss)

    def load(self):
        fd = QtGui.QFileDialog(fileMode= QtGui.QFileDialog.ExistingFile, acceptMode = QtGui.QFileDialog.AcceptOpen)
        fd.setNameFilters(['Hearingloss setup (*.json)', 'All (*)'])
        fd.setViewMode( QtGui.QFileDialog.Detail )
        if fd.exec_():
            filename = fd.selectedFiles()[0]
            loss_weigth = json.load(open(filename, 'r', encoding='utf8'))
            self.set_configuration(loss_weigth = loss_weigth)

    def save(self):
        fd = QtGui.QFileDialog(fileMode= QtGui.QFileDialog.AnyFile, acceptMode = QtGui.QFileDialog.AcceptSave, defaultSuffix = 'json')
        fd.setNameFilter('Hearingloss setup (*.json)')
        if fd.exec_():
            filename = fd.selectedFiles()[0]
            print(self.get_configuration()['loss_weigth'])
            json.dump(self.get_configuration()['loss_weigth'],open(filename, 'w', encoding='utf8'), indent=4, separators=(',', ': '))


if __name__ == '__main__':
    app = pg.mkQApp()
    win = HearingLossParameter()
    win.show()
    app.exec_()

