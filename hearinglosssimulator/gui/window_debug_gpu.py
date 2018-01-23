
import hearinglosssimulator as hls

from hearinglosssimulator.gui.myqt import QT
import pyqtgraph as pg

from hearinglosssimulator.gui.gpuselection import GpuDeviceSelection


import numpy as np



_params = [
    {'name': 'chunksize', 'type': 'list', 'values': [256, 1024] },
    {'name': 'sample_rate', 'type': 'float', 'value':44100., 'suffix': 'Hz', 'siPrefix': True},
    {'name': 'nloop', 'type': 'int', 'value': 100 },
    {'name': 'nb_channel', 'type': 'int', 'value': 2 },
]



class WindowDebugGPU(QT.QWidget):
    def __init__(self,parent = None):
        QT.QWidget.__init__(self, parent)
        
        self.resize(600,600)
        
        mainlayout  =QT.QVBoxLayout()
        self.setLayout(mainlayout)
        
        self.gpuDeviceSelection = GpuDeviceSelection()
        mainlayout.addWidget(self.gpuDeviceSelection)


        self.params = pg.parametertree.Parameter.create(name='params', type='group', children=_params)
        
        self.tree_params = pg.parametertree.ParameterTree(parent  = self)
        self.tree_params.header().hide()
        self.tree_params.setParameters(self.params, showTop=True)
        mainlayout.addWidget(self.tree_params)
        
        
        but = QT.QPushButton('run benchmark')
        mainlayout.addWidget(but)
        but.clicked.connect(self.run_benchmark)
        
        
    def run_benchmark(self):
        
    
        sample_rate = self.params['sample_rate']
        chunksize = self.params['chunksize']
        nloop = self.params['nloop']
        nb_channel = self.params['nb_channel']
        
        gpu = self.gpuDeviceSelection.get_configuration()
        gpu_platform_index = gpu['platform_index']
        gpu_device_index = gpu['device_index']
        
        lost_chunksize = 1024
        backward_chunksize = lost_chunksize + chunksize
        
        length = int(chunksize*nloop)

        in_buffer = hls.moving_erb_noise(length, sample_rate=sample_rate)
        in_buffer = np.tile(in_buffer[:, None],(1, nb_channel))

        loss_params = {  'left' : {'freqs' :  [125., 250., 500., 1000., 2000., 4000., 8000.],
                                                    'compression_degree': [0., 0., 0., 0., 0., 0., 0.],
                                                    'passive_loss_db' : [0., 0., 0., 0., 0., 0., 0.],
                                                },
                                    'right' : {'freqs' :  [125., 250., 500., 1000., 2000., 4000., 8000.],
                                                    'compression_degree': [0., 0., 0., 0., 0., 0., 0.],
                                                    'passive_loss_db' : [0., 0., 0., 0., 0., 0., 0.],
                                                }
                                }
        processing_conf = dict(nb_freq_band=32, level_step=1, loss_params=loss_params, 
                    low_freq = 100., high_freq = sample_rate*0.45, 
                    debug_mode=False, chunksize=chunksize, backward_chunksize=backward_chunksize)
        #~ node, online_arrs = hls.run_one_node_offline(hls.MainProcessing, in_buffer, chunksize, 
                        #~ sample_rate, node_conf=node_conf, buffersize_margin=backward_chunksize)


        for _class in [hls.InvCGC, hls.InvComp]:
        #~ for _class in [hls.InvComp, hls.InvComp2,]:
        #~ for _class in [hls.InvComp,]:
        #~ for _class in [hls.InvComp2,]:
            print()
            print(_class.__name__, sample_rate, chunksize, backward_chunksize, nb_channel, processing_conf['nb_freq_band'])
            processing = _class(nb_channel=nb_channel, sample_rate=sample_rate,  apply_configuration_at_init=False, **processing_conf)
            processing.create_opencl_context(gpu_platform_index=gpu_platform_index, gpu_device_index=gpu_device_index)
            print(processing.ctx)
            processing.initialize()
            online_arrs = hls.run_instance_offline(processing, in_buffer, chunksize, sample_rate,
                        buffersize_margin=backward_chunksize, time_stats=True)


        
def test_WindowDebugGPU():
    
    import pyqtgraph as pg
    
    app = pg.mkQApp()
    win = WindowDebugGPU()
    win.show()
    app.exec_()


if __name__ =='__main__':
    test_WindowDebugGPU()