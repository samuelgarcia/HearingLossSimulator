"""
This illustrate how to use the InvCGC as a pyacq Node.
"""
import hearinglosssimulator as hls
import pyacq

import time

import pyaudio

#This pyaudio deveice_index
#~ pa = pyaudio.PyAudio()
#~ for i in range(pa.get_device_count()):
    #~ dev =  pa.get_device_info_by_index(i)
    #~ hostapi_name = pa.get_host_api_info_by_index(dev['hostApi'])['name']
    #~ print(dev, )
    #~ print(hostapi_name)
#~ exit()



nb_channel = 1
sample_rate = 44100.
chunksize = 512
backward_chunksize = chunksize * 3

loss_params = {  'left' : {'freqs' :  [125., 250., 500., 1000., 2000., 4000., 8000.],
                                            'compression_degree': [0., 0., 0., 0., 0., 0., 0.],
                                            'passive_loss_db' : [0., 0., 0., 0., 0., 0., 0.],
                                        },
                        }


params = dict(
        nb_freq_band=16, low_freq = 100., high_freq = 15000.,
        tau_level = 0.005, smooth_time = 0.0005, level_step =1., level_max = 120.,
        calibration =  93.979400086720375,
        loss_params = loss_params,
        chunksize=chunksize, backward_chunksize=backward_chunksize,
        debug_mode=False,
    )


stream_spec = dict(protocol='tcp', interface='127.0.0.1', transfertmode='plaindata')

man = pyacq.create_manager()
ng0 = man.create_nodegroup()  # process for device
ng1 = man.create_nodegroup()  # process for processing

dev = ng0.create_node('PyAudio')
dev.configure(nb_channel=nb_channel, sample_rate=sample_rate,
              input_device_index=10,
              output_device_index=10,
              format='float32', chunksize=chunksize)
dev.output.configure(**stream_spec)
dev.initialize()



ng1.register_node_type_from_module('hearinglosssimulator', 'InvCGCNode')
node = ng1.create_node('HLSNode')
node.configure(**params)

#~ ng1.register_node_type_from_module('hearinglosssimulator', 'DoNothing')
#~ node = ng1.create_node('DoNothing')
#~ node.configure()

node.input.connect(dev.output)
node.outputs['signals'].configure(**stream_spec)
node.initialize()


dev.input.connect(node.outputs['signals'])


dev.start()
node.start()
time.sleep(15)

dev.stop()
node.stop()


man.close()


