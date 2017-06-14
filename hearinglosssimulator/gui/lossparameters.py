from hearinglosssimulator.gui.myqt import QT
import pyqtgraph as pg

import numpy as np
import scipy.interpolate
import json
import time

from collections import OrderedDict

from hearinglosssimulator.gui.guitools import MplCanvas


from hearinglosssimulator.gui.myqt import DebugDecorator



n = 7
freqs = [ 125*2**i  for i in range(n) ]
default_loss = [ {'freq' : f, 'db_loss': 0.}  for f in freqs ]
# From Irino hearing level when no compression loss
best_hearing_level_irino = [-6.7406, 2.4563, 4.7537, 5.7118, 1.0655, -3.4335, -7.2814]
best_hearing_level_simple = [0]*n

# equivalent
equivalent_compression_loss_at_thesh = 37. #dB



#~ compression_loss_preset = OrderedDict([
    #~ ('100%', [-6.7406, 2.4563, 4.7537, 5.7118, 1.0655, -3.4335, -7.2814]),
    #~ ('67%', [-0.3463, 10.0101, 17.8573, 19.9751, 16.8954, 14.5161, 5.1201]),
    #~ ('50%', [2.5999, 14.3605, 23.7777, 26.8029, 24.7069, 23.5780, 10.6923]),
    #~ ('33%', [5.4801,  18.5666, 28.9101, 32.6974, 31.2244, 30.0204, 16.0619]),
    #~ ('0%', [10.5790, 24.9903, 36.0186, 40.5679, 38.9283, 36.5154, 25.2229]),
#~ ])

compression_ratio = OrderedDict(zip(('0%', '33%', '50%', '67%','100%'), (0, 1/3., 1/2., 2/3., 1.)))


hearing_level_preset = OrderedDict([
    ('No preset' , None),
    ('All 37dB' , [37, 37, 37, 37, 37, 37, 37]),
    ('example 1' , [10, 4, 10, 13, 48, 58, 79]),
    ('60 years', [10, 15, 15, 15, 25, 35, 43]),
    ('80 years', [25, 30, 32, 28, 38, 50, 60]),
    ('Otosclerosis', [50, 55, 50, 50, 40, 25, 20]),
    ('Noise-induced', [15, 10, 15, 10, 10, 40, 20]),
])



def plot_hearingloss(ax, hearing_level, compression_degree, passive_db_loss, mode='simple'):
        
        compression_degree = np.array(compression_degree)
        passive_db_loss = np.array(passive_db_loss)
        
        lines ={} # line handles 
        
        ax.clear()
        x = np.arange(n)+.5
        
        ax.axhline(0, color='k', lw=2)
        
        
        if mode=='simple':
            baseline = best_hearing_level_simple
            compression_loss = (1 - compression_degree) * equivalent_compression_loss_at_thesh
        elif mode=='irino':
            baseline = best_hearing_level_irino
            #take irino formula
            compression_loss = (1 - compression_degree) * equivalent_compression_loss_at_thesh
        
        ax.fill_between(x, baseline, baseline + compression_loss, color='#00FFFF', alpha=.5)
        ax.fill_between(x, baseline + compression_loss,baseline + compression_loss +passive_db_loss,  color='#FF00FF', alpha=.5)
        
        lines['normal'],= ax.plot(x, baseline, color='#2EFE2E', marker='8', markersize=8, lw=2, ls='-')
        lines['compression_loss'], = ax.plot(x, baseline + compression_loss  , color='#00FFFF', marker='s', markersize=8, lw=.5, ls='--')
        lines['total_loss'], = ax.plot(x, baseline + compression_loss +passive_db_loss, color='#FF00FF', marker='s', markersize=8, lw=.5, ls='--')
        
        if hearing_level is not None:
            hearing_level = np.array(hearing_level)
            lines['hearing_level'], = ax.plot(x, hearing_level, color='#000000', marker='o', markersize=12, lw=2, ls='-', markerfacecolor='w')
        
        ax.set_title('Frequency (Hz)')
        ax.set_ylabel('Hearing Level (dB)')
        ax.grid(True)
        ax.set_xticks([i+0.5 for i in range(n)])
        ax.set_xticklabels(freqs)
        ax.set_yticks(np.arange(-20., 130., 10.))
        ax.set_xlim(0,n)
        ax.set_ylim(120., -20.)
        
        ax.set_aspect(1./20)
        
        return lines


#~ def refresh_figure(lines, hearing_level, compression_degree, passive_db_loss, mode='simple'):
    #~ x = np.arange(n)+.5
    
    #~ if mode=='simple':
        #~ baseline = best_hearing_level_simple
        #~ compression_loss = (1 - compression_degree) * equivalent_compression_loss_at_thesh
    #~ elif mode=='irino':
        #~ baseline = best_hearing_level_irino
        #~ #take irino formula
        #~ compression_loss = (1 - compression_degree) * equivalent_compression_loss_at_thesh

    #~ lines['normal'].set_data(x, baseline)
    #~ lines['compression_loss'].set_data(x, baseline + compression_loss)
    #~ lines['total_loss'].set_data(x, baseline + compression_loss +passive_db_loss)
    
    #~ if hearing_level is not None:
        #~ hearing_level = np.array(hearing_level)
        #~ lines['hearing_level'].set_data(x, hearing_level)


def test_plot_hearingloss():
    import matplotlib.pyplot as plt
    hearing_level = np.array([10, 15, 15, 15, 25, 35, 43])
    compression_degree = np.array([.8, .7, .6, .5, 0, 0, 0])
    passive_db_loss = np.array([1, 2, 4, 8, 10, 12, 14])
    
    fig, ax = plt.subplots()
    plot_hearingloss(ax, hearing_level, compression_degree, passive_db_loss, mode='simple')
    
    fig, ax = plt.subplots()
    plot_hearingloss(ax, hearing_level, compression_degree, passive_db_loss, mode='irino')

    fig, ax = plt.subplots()
    lines = plot_hearingloss(ax, None, compression_degree, passive_db_loss, mode='simple')
    #~ refresh_figure(lines, None, compression_degree+.1, passive_db_loss+30, mode='simple')
    
    
    plt.show()
    


class OneChannelHearingLossParameter(QT.QWidget):
    def __init__(self, parent = None):
        QT.QWidget.__init__(self, parent)
        mainlayout  = QT.QVBoxLayout()
        self.setLayout(mainlayout)

        self.canvas = MplCanvas()
        mainlayout.addWidget(self.canvas)
        
        self.mode = 'simple'
        
        
        h = QT.QHBoxLayout()
        mainlayout.addLayout(h)
        h.addSpacerItem(QT.QSpacerItem(130,0))
        g = QT.QGridLayout()
        h.addLayout(g)
        self.spin_passive_loss = {}
        self.spin_comp_degree = {}
        for i in range(n):
            g.addWidget(QT.QLabel('{} Hz'.format(freqs[i])), 0, i)
            self.spin_passive_loss[i] = s = pg.SpinBox(suffix='dBLoss', bounds=[0, 120], step=1)
            g.addWidget(s, 1, i)
            s.sigValueChanged.connect(self.on_spinbox_changed)
            self.spin_comp_degree[i] = s = pg.SpinBox(suffix='%', bounds=[0,100], step=10)
            g.addWidget(s, 2, i)
            s.sigValueChanged.connect(self.on_spinbox_changed)
            
        h.addSpacerItem(QT.QSpacerItem(110,0))

        self.compression_degree = np.array([1.]*n)
        self.passive_loss_db = np.array([0.]*n)
        self.hearing_level = None
        
        self.lines = plot_hearingloss(self.canvas.ax,  self.hearing_level, self.compression_degree, self.passive_loss_db, mode=self.mode)
        
        self.refresh_spinbox()

    def on_spinbox_changed(self, sender):
        self.passive_loss_db = np.array([ float(self.spin_passive_loss[i].value()) for i in range(n)])
        self.compression_degree = np.array([ float(self.spin_comp_degree[i].value())/100. for i in range(n)])
        self.refresh_canvas()
    
    def refresh_canvas(self):
        #~ t0 = time.perf_counter()
        self.lines = plot_hearingloss(self.canvas.ax,  self.hearing_level, self.compression_degree, self.passive_loss_db, mode=self.mode)
        #~ refresh_figure(self.lines, None, compression_degree+.1, passive_db_loss+30, mode='simple')
        self.canvas.draw()
        #~ t1 = time.perf_counter()
        #~ print(t1-t0)
    
    def refresh_spinbox(self):
        for i in range(n):
            s = self.spin_passive_loss[i]
            s.sigValueChanged.disconnect(self.on_spinbox_changed)
            s.setValue(self.passive_loss_db[i])
            s.sigValueChanged.connect(self.on_spinbox_changed)
            
            s = self.spin_comp_degree[i]
            s.sigValueChanged.disconnect(self.on_spinbox_changed)
            s.setValue(float(np.round(self.compression_degree[i]*100.)))
            s.sigValueChanged.connect(self.on_spinbox_changed)
        
    def set_compression_degree(self, compression_degree):
        self.compression_degree = np.array(compression_degree)
        self.compression_degree[self.compression_degree<0.] = 0.
        self.compression_degree[self.compression_degree>1.] = 1.
        self.refresh_spinbox()
        self.refresh_canvas()
    
    def set_passive_loss_db(self, passive_loss_db):
        self.passive_loss_db = np.array(passive_loss_db)
        self.refresh_canvas()
        self.refresh_spinbox()
    
    def set_hearing_level(self, hearing_level, wanted_comp_degree):
        self.hearing_level = hearing_level
        
        if self.hearing_level is not None:
            eq_loss = (1-wanted_comp_degree) * equivalent_compression_loss_at_thesh
            for i in range(n):
                hl = hearing_level[i]
                if hl>eq_loss:
                    self.compression_degree[i] = wanted_comp_degree
                    self.passive_loss_db[i] = hl - eq_loss
                else:
                    self.compression_degree[i] = 1 - hl/equivalent_compression_loss_at_thesh
                    self.passive_loss_db[i] = 0.
        
        self.refresh_canvas()
        self.refresh_spinbox()
        

def test_OneChannelHearingLossParameter():
    app = pg.mkQApp()
    win = OneChannelHearingLossParameter()
    win.show()
    app.exec_()

        
    

class HearingLossParameter(QT.QWidget):
    def __init__(self, parent = None):
        QT.QWidget.__init__(self, parent)
        mainlayout  = QT.QVBoxLayout()
        self.setLayout(mainlayout)

        h = QT.QHBoxLayout()
        mainlayout.addLayout(h)

        self.tab = QT.QTabWidget()
        h.addWidget(self.tab)
        
        ears = ('left', 'right')
        self.hl_params ={}
        for ear in ears:
            p = OneChannelHearingLossParameter()
            self.hl_params[ear] = p
            self.tab.addTab(p, ear)
        
        v = QT.QVBoxLayout()
        h.addLayout(v)
        
        v.addWidget(QT.QLabel('Hear level presets:'))
        self.combo_hearing_level_preset = QT.QComboBox()
        self.combo_hearing_level_preset.setMinimumHeight(48)
        v.addWidget(self.combo_hearing_level_preset)
        self.combo_hearing_level_preset.addItems(hearing_level_preset.keys())
        self.combo_hearing_level_preset.currentIndexChanged.connect(self.on_change_preset)
        v.addWidget(QT.QLabel('Compression healthiness:'))
        self.combo_compression_loss_preset = QT.QComboBox()
        self.combo_compression_loss_preset.setMinimumHeight(48)
        v.addWidget(self.combo_compression_loss_preset)
        self.combo_compression_loss_preset.addItems(compression_ratio.keys())
        self.combo_compression_loss_preset.setCurrentIndex(2)
        self.combo_compression_loss_preset.currentIndexChanged.connect(self.on_change_preset)
        v.addSpacing(30)
        but = QT.QPushButton(u'Copy L>R')
        v.addWidget(but)
        but.clicked.connect(self.copy_l_to_r)
        but = QT.QPushButton(u'Load')
        v.addWidget(but)
        but.clicked.connect(self.load)
        but = QT.QPushButton(u'Save')
        v.addWidget(but)
        but.clicked.connect(self.save)
        v.addStretch()



        self.nb_channel = 2

    def on_change_preset(self):
        
        preset_name = self.combo_hearing_level_preset.currentText()
        preset_value = hearing_level_preset[preset_name]
        
        k = self.combo_compression_loss_preset.currentText()
        wanted_comp_degree = compression_ratio[k]
        
        for ear, p in self.hl_params.items():
            p.set_hearing_level(preset_value, wanted_comp_degree)
    
    def set_nb_channel(self, n):
        assert n in (1,2), 'only mono or stereo'
        self.nb_channel = n
        if n==1:
            self.tab.setTabEnabled(1, False)
        else:
            self.tab.setTabEnabled(1, True)

    def set_configuration(self, **config):
        for k, conf in config.items():
            self.hl_params[k].set_compression_degree(conf['compression_degree'])
            self.hl_params[k].set_passive_loss_db(conf['passive_loss_db'])
    
    def get_configuration(self):
        config = {}
        for ear in ('left', 'right')[:self.nb_channel]:
            config[ear] = {
                        'freqs' : freqs,
                        'passive_loss_db' : self.hl_params[ear].passive_loss_db.tolist(),
                        'compression_degree' : self.hl_params[ear].compression_degree.tolist(),
                        }
        return config

    def copy_l_to_r(self):
        self.hl_params['right'].passive_loss_db = self.hl_params['left'].passive_loss_db.copy()
        self.hl_params['right'].compression_degree = self.hl_params['left'].compression_degree.copy()
        self.hl_params['right'].refresh_canvas()
        self.hl_params['right'].refresh_spinbox()

    def load(self):
        fd = QT.QFileDialog(fileMode= QT.QFileDialog.ExistingFile, acceptMode = QT.QFileDialog.AcceptOpen)
        fd.setNameFilters(['Hearingloss setup (*.json)', 'All (*)'])
        fd.setViewMode( QT.QFileDialog.Detail )
        if fd.exec_():
            filename = fd.selectedFiles()[0]
            config = json.load(open(filename, 'r', encoding='utf8'))
            self.set_configuration(**config)

    def save(self):
        fd = QT.QFileDialog(fileMode= QT.QFileDialog.AnyFile, acceptMode = QT.QFileDialog.AcceptSave, defaultSuffix = 'json')
        fd.setNameFilter('Hearingloss setup (*.json)')
        if fd.exec_():
            filename = fd.selectedFiles()[0]
            json.dump(self.get_configuration(),open(filename, 'w', encoding='utf8'), indent=4, separators=(',', ': '))


def test_HearingLossParameter():

    app = pg.mkQApp()
    win = HearingLossParameter()
    #~ win.set_nb_channel(1)
    win.set_nb_channel(2)
    win.show()
    app.exec_()
    print(win.get_configuration())

if __name__ == '__main__':
    
    #~ test_plot_hearingloss()
    #~ test_OneChannelHearingLossParameter()
    test_HearingLossParameter()
    


