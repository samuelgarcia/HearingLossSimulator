from hearinglosssimulator.gui.myqt import QT
import pyqtgraph as pg

import numpy as np
#~ import pyaudio
import sounddevice as sd


from hearinglosssimulator.gui.guitools import get_dict_from_group_param


 #~ nb_channel=1, sample_rate=44100., dtype='float32',
 #~ nb_freq_band=32, low_freq = 100., high_freq = 15000.,
                #~ tau_level = 0.005,  level_step =1., level_max = 100.,
#~ chunksize=512, backward_chunksize=1024, 
# engine

_params = [
    {'name': 'nb_channel', 'type': 'int', 'value': 2 },
    
    {'name': 'simulator_engine', 'type': 'list', 'values': ['InvComp', 'InvCGC'] },
    
    #~ {'name': 'dtype', 'type': 'list', 'values': ['float32'] },
    {'name': 'nb_freq_band', 'type': 'int', 'value': 32 },
    {'name': 'low_freq', 'type': 'float', 'value':100., 'suffix': 'Hz', 'siPrefix': True},
    {'name': 'high_freq', 'type': 'float', 'value': 15000.,  'suffix': 'Hz', 'siPrefix': True},
    
    {'name': 'tau_level', 'type': 'float', 'value': 0.005,  'suffix': 's', 'siPrefix': True},
    {'name': 'level_max', 'type': 'float', 'value': 100.,  'suffix': 'dBSpl', 'siPrefix': True},
    {'name': 'level_step', 'type': 'float', 'value': 1.,  'suffix': 'dBSpl', 'siPrefix': True},
    
    {'name': 'chunksize', 'type': 'int', 'value': 1024 },
    {'name': 'backward_chunksize', 'type': 'int', 'value': 2048 },
    
]


class SimulatorParameter(QT.QWidget):
    def __init__(self, with_all_params=True, parent = None):
        QT.QWidget.__init__(self, parent)
        mainlayout  =QT.QVBoxLayout()
        self.setLayout(mainlayout)
        self.resize(400, 400)

        if with_all_params:
            children = _params
        else:
            children = _params[1:-2]
        
        self.params = pg.parametertree.Parameter.create(name='simulator', type='group', children=children)
        
        #~ layout = QT.QVBoxLayout()
        #~ self.setLayout(layout)

        self.tree_params = pg.parametertree.ParameterTree(parent  = self)
        self.tree_params.header().hide()
        self.tree_params.setParameters(self.params, showTop=True)
        mainlayout.addWidget(self.tree_params)

        #~ but = QT.QPushButton('OK')
        #~ layout.addWidget(but)
        #~ but.clicked.connect(self.accept)


    def set_configuration(self, **params):
        try: 
            for k, v in params.items():
                self.params[k] = v
        except Exception as e: 
            print('erreur SimulatorParameter.set_configuration', e)
    
    def get_configuration(self):
        config = get_dict_from_group_param(self.params)
        return config



if __name__ == '__main__':
    app = pg.mkQApp()
    win = SimulatorParameter()
    win.show()
    app.exec_()
    print(win.get_configuration())
