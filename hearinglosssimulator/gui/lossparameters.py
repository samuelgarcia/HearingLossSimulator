import PyQt5 # this force pyqtgraph to deal with Qt5
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
import numpy as np
import scipy.interpolate
import json

from collections import OrderedDict

from hearinglosssimulator.gui.guitools import MplCanvas



#~ _default_bands = [ {'freq' : np.ceil(100*((2**(1./3.))**i)), 'db_loss': 0.}  for i in range(20) ]
n = 7
freqs = [ 125*2**i  for i in range(n) ]
default_loss = [ {'freq' : f, 'db_loss': 0.}  for f in freqs ]

compression_loss_preset = OrderedDict([
    ('100%', [-6.7406, 2.4563, 4.7537, 5.7118, 1.0655, -3.4335, -7.2814]),
    ('67%', [-0.3463, 10.0101, 17.8573, 19.9751, 16.8954, 14.5161, 5.1201]),
    ('50%', [2.5999, 14.3605, 23.7777, 26.8029, 24.7069, 23.5780, 10.6923]),
    ('33%', [5.4801,  18.5666, 28.9101, 32.6974, 31.2244, 30.0204, 16.0619]),
    ('0%', [10.5790, 24.9903, 36.0186, 40.5679, 38.9283, 36.5154, 25.2229]),
])
compression_ratio = OrderedDict(zip(('0%', '33%', '50%', '67%','100%'), (0, 1/3., 1/2., 2/3., 1.)))


hearing_level_preset = OrderedDict([
    ('example 1' , [10, 4, 10, 13, 48, 58, 79]),
    ('60 years', [10, 15, 15, 15, 25, 35, 43]),
    ('80 years', [25, 30, 32, 28, 38, 50, 60]),
    ('Otosclerosis', [50, 55, 50, 50, 40, 25, 20]),
    ('Noise-induced', [15, 10, 15, 10, 10, 40, 20]),
])



def plot_hearingloss(ax, hearing_level, compression_loss):
        hearing_level = np.array(hearing_level)
        compression_loss = np.array(compression_loss)
        
        lines ={} # line handles 
        
        ax.clear()
        x = np.arange(n)+.5
        
        ax.axhline(0, color='k', lw=2)
        
        compression_loss_clip = np.amin([hearing_level, compression_loss], axis=0)
        
        lines['hearing_level'], = ax.plot(x, hearing_level, color='#000000', marker='o', markersize=12, lw=2, ls='-', markerfacecolor='w')
        lines['normal'],= ax.plot(x, compression_loss_preset['100%'], color='#2EFE2E', marker='8', markersize=8, lw=2, ls='-')
        lines['compression_loss'], = ax.plot(x, compression_loss, color='#00FFFF', marker='s', markersize=8, lw=.5, ls='--')
        lines['compression_loss_clip'], = ax.plot(x, compression_loss_clip, color='#FF00FF', marker='D', markersize=8, lw=2, ls='-')
        
        ax.set_title('Frequency (Hz)')
        ax.set_ylabel('Hearing Level (dB)')
        ax.grid(True)
        ax.set_xticks([i+0.5 for i in range(n)])
        ax.set_xticklabels(freqs)
        ax.set_yticks(np.arange(-20., 130., 10.))
        ax.set_xlim(0,n)
        ax.set_ylim(120., -20.)
        
        return lines

class HearingLossParameter(QtGui.QWidget):
    def __init__(self, parent = None):
        QtGui.QWidget.__init__(self, parent)
        mainlayout  = QtGui.QVBoxLayout()
        self.setLayout(mainlayout)


        h = QtGui.QHBoxLayout()
        mainlayout.addLayout(h)
        h.addStretch()
        self.combo_hearing_level_preset = QtGui.QComboBox()
        h.addWidget(self.combo_hearing_level_preset)
        self.combo_hearing_level_preset.addItems(hearing_level_preset.keys())
        self.combo_hearing_level_preset.currentIndexChanged.connect(self.on_preset_changed)
        self.combo_compression_loss_preset = QtGui.QComboBox()
        h.addWidget(self.combo_compression_loss_preset)
        self.combo_compression_loss_preset.addItems(compression_loss_preset.keys())
        self.combo_compression_loss_preset.currentIndexChanged.connect(self.on_preset_changed)
        
        
        self.canvas = MplCanvas()
        mainlayout.addWidget(self.canvas)
        
        
        h = QtGui.QHBoxLayout()
        mainlayout.addLayout(h)
        h.addSpacerItem(QtGui.QSpacerItem(130,0))
        g = QtGui.QGridLayout()
        h.addLayout(g)
        self.spin_hearinglevel = {}
        self.spin_comp_degree = {}
        for i in range(n):
            g.addWidget(QtGui.QLabel('{} Hz'.format(freqs[i])), 0, i)
            self.spin_hearinglevel[i] = s = pg.SpinBox(suffix='dBHL', bounds=[-20, 120], step=1)
            g.addWidget(s, 1, i)
            s.sigValueChanged.connect(self.on_spinbox_changed)
            self.spin_comp_degree[i] = s = pg.SpinBox(suffix='%', bounds=[0,100], step=10)
            g.addWidget(s, 2, i)
            s.sigValueChanged.connect(self.on_spinbox_changed)
            
        h.addSpacerItem(QtGui.QSpacerItem(110,0))

        self.hearing_level = hearing_level_preset['80 years']
        
        self.compression_loss = compression_loss_preset['0%']
        
        self.lines = plot_hearingloss(self.canvas.ax,  self.hearing_level, self.compression_loss)
        
        self.all_interp1d_loss_to_comp = {}
        self.all_interp1d_comp_to_loss = {}
        for i in range(n):
            losses = [compression_loss_preset[k][i] for k in compression_ratio.keys()]
            comps = list(compression_ratio.values())
            self.all_interp1d_loss_to_comp[i] = scipy.interpolate.interp1d(losses, comps, kind='linear')
            self.all_interp1d_comp_to_loss[i] = scipy.interpolate.interp1d(comps, losses, kind='linear')
            
        self.refresh_spinbox()
    
    def refresh_canvas(self):
        x = np.arange(n)+.5
        compression_loss_clip = np.amin([self.hearing_level, self.compression_loss], axis=0)
        
        self.lines['hearing_level'].set_data(x, self.hearing_level)
        self.lines['compression_loss_clip'].set_data(x, compression_loss_clip)
        
        self.canvas.draw()
    
    def refresh_spinbox(self):
        self.get_compression_degree()
        for i in range(n):
            s = self.spin_hearinglevel[i]
            s.sigValueChanged.disconnect(self.on_spinbox_changed)
            s.setValue(self.hearing_level[i])
            s.sigValueChanged.connect(self.on_spinbox_changed)
            
            s = self.spin_comp_degree[i]
            s.sigValueChanged.disconnect(self.on_spinbox_changed)
            s.setValue(float(np.round(self.compression_degree[i]*100.)))
            s.sigValueChanged.connect(self.on_spinbox_changed)
    
    def on_preset_changed(self):
        k = self.combo_hearing_level_preset.currentText()
        self.hearing_level = hearing_level_preset[k]

        k = self.combo_compression_loss_preset.currentText()
        self.compression_loss = compression_loss_preset[k]
        
        self.refresh_canvas()
        self.refresh_spinbox()
    
    def on_spinbox_changed(self, sender):
        self.hearing_level = [ float(self.spin_hearinglevel[i].value()) for i in range(n)]
        if sender in self.spin_comp_degree.values():
            self.get_compression_loss()
        
        self.refresh_canvas()
        self.refresh_spinbox()
        
    def get_compression_degree(self):
        compression_loss_clip = np.amin([self.hearing_level, self.compression_loss], axis=0)
        self.compression_degree = []
        for i in range(n):
            self.compression_degree.append(float(self.all_interp1d_loss_to_comp[i](compression_loss_clip[i])))
        return self.compression_degree
    
    def get_compression_loss(self):
        for i in range(n):
            v = float(self.spin_comp_degree[i].value())/100.
            self.compression_loss[i] = self.all_interp1d_comp_to_loss[i](v)
        


if __name__ == '__main__':
    app = pg.mkQApp()
    win = HearingLossParameter()
    win.show()
    app.exec_()

