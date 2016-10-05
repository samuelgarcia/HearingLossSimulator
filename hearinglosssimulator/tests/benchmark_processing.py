import matplotlib.pyplot as plt
import numpy as np

import hearinglosssimulator as hls

#~ exit()

#~ nb_channel = 2
nb_channel = 1

sample_rate =44100.

#~ chunksize = 256
#~ chunksize = 512
chunksize = 1024
#~ chunksize = 2048
backward_chunksize = chunksize*2
#~ backward_chunksize = chunksize*5
#~ backward_chunksize = chunksize*4

nloop = 100

length = int(chunksize*nloop)


in_buffer = hls.moving_erb_noise(length, sample_rate=sample_rate)
#~ in_buffer = hls.moving_sinus(length, sample_rate=sample_rate, speed = .5,  f1=100., f2=2000.,  ampl = .8)
in_buffer = np.tile(in_buffer[:, None],(1, nb_channel))
#~ print(in_buffer.shape)
#~ exit()

loss_weigth = [ [(50,0.), (1000., -35), (2000., -40.), (6000., -35.), (25000,0.),]]*nb_channel
processing_conf = dict(nb_freq_band=10, level_step=4, loss_weigth=loss_weigth, 
            debug_mode=False, chunksize=chunksize, backward_chunksize=backward_chunksize)
#~ node, online_arrs = hls.run_one_node_offline(hls.MainProcessing, in_buffer, chunksize, 
                #~ sample_rate, node_conf=node_conf, buffersize_margin=backward_chunksize)

processing, online_arrs = hls.run_one_class_offline(hls.InvCGC, in_buffer, chunksize, sample_rate,
            processing_conf=processing_conf, buffersize_margin=backward_chunksize,
             time_stats=True)

