from hearinglosssimulator.gui.myqt import QT
import pyqtgraph as pg

import numpy as np
#~ import pyaudio
import sounddevice as sd


from hearinglosssimulator.gui.guitools import get_dict_from_group_param



_params = [
    {'name': 'nb_buffer_latency', 'type': 'int', 'value': 6},
    {'name': 'sample_rate', 'type': 'float', 'value':44100., 'suffix': 'Hz', 'siPrefix': True},
    
    {'name': 'speaker_gain', 'type': 'float', 'value':0., 'limits': (-63.5, 24.), 'step' :0.5, 'suffix': 'dB', 'siPrefix': True},
    {'name': 'microphone_gain', 'type': 'float', 'value':20.,  'limits': (-12, 20.), 'step' :0.5, 'suffix': 'dB', 'siPrefix': True},
    
    
]


class WifiDeviceParameter(QT.QWidget):
    def __init__(self, parent = None):
        QT.QWidget.__init__(self, parent)
        mainlayout  =QT.QVBoxLayout()
        self.setLayout(mainlayout)
        self.resize(400, 400)
        
        #~ self.client = client
        
        self.params = pg.parametertree.Parameter.create(name='wifi_device', type='group', children=_params)
        
        self.tree_params = pg.parametertree.ParameterTree(parent  = self)
        self.tree_params.header().hide()
        self.tree_params.setParameters(self.params, showTop=True)
        mainlayout.addWidget(self.tree_params)
    
    def set_configuration(self, **params):
        try: 
            for k, v in params.items():
                self.params[k] = v
        except Exception as e: 
            print('erreur WifiDeviceParameter.set_configuration', e)
    
    def get_configuration(self):
        config = get_dict_from_group_param(self.params)
        return config



if __name__ == '__main__':
    app = pg.mkQApp()
    win = WifiDeviceParameter()
    win.show()
    app.exec_()
    print(win.get_configuration())
