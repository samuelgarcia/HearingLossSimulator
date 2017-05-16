"""
This example illustrate how to use the simulator in near real time with python-sounddevice.

"""
import sounddevice as sd
import time
import hearinglosssimulator as hls


nb_channel = 2
sample_rate = 44100.
#~ chunksize = 512
chunksize = 1024
backward_chunksize = chunksize*3

loss_params = {  'left' : {'freqs' :  [125., 250., 500., 1000., 2000., 4000., 8000.],
                                            'compression_degree': [0., 0., 0., 0., 0., 0., 0.],
                                            'passive_loss_db' : [0., 0., 0., 0., 0., 0., 0.],
                                        },
                            'right' : {'freqs' :  [125., 250., 500., 1000., 2000., 4000., 8000.],
                                            'compression_degree': [0., 0., 0., 0., 0., 0., 0.],
                                            'passive_loss_db' : [0., 0., 0., 0., 0., 0., 0.],
                                        }
                        }

params = dict(
        nb_freq_band=32, low_freq = 100., high_freq = 15000.,
        tau_level = 0.005,level_step =1., level_max=100.,
        calibration =  110.,
        loss_params = loss_params,
        chunksize=chunksize, backward_chunksize=backward_chunksize, 
    )


processing = hls.InvComp(nb_channel=nb_channel, sample_rate=sample_rate,
        dtype='float32', apply_configuration_at_init=False, **params)
processing.initialize()


# define the callback audio wire
index = 0
def callback(indata, outdata, frames, time, status):
    if status:
        print(status, flush=True)
    global index
    index += frames
    
    returns = processing.proccesing_func(index, indata)
    index2, out = returns['main_output']
    if index2 is not None:
        outdata[:] = out
    else:
        outdata[:] = 0


latency = 'low'
stream = sd.Stream(channels=nb_channel, callback=callback, samplerate=sample_rate,
                blocksize=chunksize, latency=latency, device=None, dtype='float32')


# run the audio stream for 10 seconds.
stream.start()
time.sleep(10)
stream.stop()

