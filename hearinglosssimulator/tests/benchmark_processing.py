import matplotlib.pyplot as plt
import numpy as np

import hearinglosssimulator as hls

#~ exit()

nb_channel = 2
#~ nb_channel = 1

sample_rate = 44100.
#~ sample_rate = 30000.
#~ sample_rate = 20000.
#~ sample_rate = 15000.

chunksize = 256
#~ chunksize = 512
#~ chunksize = 1024
#~ chunksize = 2048
#~ backward_chunksize = chunksize*5
#~ backward_chunksize = chunksize*4


lost_chunksize = 1024
backward_chunksize = lost_chunksize + chunksize

nloop = 1000

length = int(chunksize*nloop)


in_buffer = hls.moving_erb_noise(length, sample_rate=sample_rate)
#~ in_buffer = hls.moving_sinus(length, sample_rate=sample_rate, speed = .5,  f1=100., f2=2000.,  ampl = .8)
in_buffer = np.tile(in_buffer[:, None],(1, nb_channel))
#~ print(in_buffer.shape)
#~ exit()

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
    processing = _class(nb_channel=nb_channel, sample_rate=sample_rate,  **processing_conf)
    online_arrs = hls.run_instance_offline(processing, in_buffer, chunksize, sample_rate,
                buffersize_margin=backward_chunksize, time_stats=True)

