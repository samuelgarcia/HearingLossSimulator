import os
import numpy as np
import scipy.signal
import matplotlib.pyplot as plt
import json

import hearinglosssimulator as hls

import helper


#~ path = '/home/sgarcia/test_HLS/'
path = '/home/samuel/test_HLS/'
#~ path = 'C:/Users/HI_Simulateur/Documents/test_HLS/'
#~ path = 'N:/cap/Data/data_psyac/casque_simulation_perte_anr_aida/test_HLS/'


if not os.path.exists(path):
    os.mkdir(path)


params = dict(
    nb_channel = 2,
    sample_rate =44100.,
    chunksize = 256,
    backward_chunksize = 256*3,
    nloop = 200,
    loss_weigth = [ [(50,0.), (1000., -35), (2000., -40.), (6000., -35.), (25000,0.),]]*2,
    nb_freq_band = 32,
    low_freq = 100., high_freq = 15000.,
    level_step=4, level_max = 120.,
    tau_level = 0.005, smooth_time = 0.0005,
    calibration =  93.979400086720375,
    
    )

def setup_files():
    json.dump( params, open(path+'params.json', 'w'), indent=4)
    
    globals().update(params)
    length = nloop*chunksize
    
    in_buffer = hls.moving_erb_noise(length, sample_rate=sample_rate, speed = .5,  f1=80., f2=1000.,  ampl = .8)
    in_buffer = np.tile(in_buffer[:, None],(1, nb_channel))
    with open(path+'sound.raw', mode='wb') as f:
        f.write(in_buffer.tobytes())
    
    in_buffer2 = np.fromstring(open(path+'sound.raw', mode='rb').read(), dtype='float32').reshape(length, nb_channel)
    helper.assert_arrays_equal(in_buffer, in_buffer2)
    
    
    
def process_sound():
    params = json.load(open(path+'params.json', 'r'))
    globals().update(params)
    for k in ['nloop', 'sample_rate', 'nb_channel']:
        params.pop(k)
    length = nloop*chunksize
    
    in_buffer = np.fromstring(open(path+'sound.raw', mode='rb').read(), dtype='float32').reshape(length, nb_channel)
    
    
    #~ node, online_arrs = hls.run_one_node_offline(hls.MainProcessing, in_buffer, params['chunksize'], sample_rate, node_conf=params, buffersize_margin=params['backward_chunksize'])
    processing, online_arrs = hls.run_one_class_offline(hls.InvCGC, in_buffer, params['chunksize'], sample_rate, processing_conf=params, buffersize_margin=params['backward_chunksize'])
    
    print(online_arrs['main_output'].shape)

    with open(path+'sound_filtered_new.raw', mode='wb') as f:
        f.write(online_arrs['main_output'].tobytes())


    
    
def compare_old_and_new():
    params = json.load(open(path+'params.json', 'r'))
    globals().update(params)
    length = nloop*chunksize


    in_buffer = np.fromstring(open(path+'sound.raw', mode='rb').read(), dtype='float32').reshape(length, nb_channel)
    out_buffer_old = np.fromstring(open(path+'sound_filtered_old.raw', mode='rb').read(), dtype='float32').reshape(length, nb_channel)
    out_buffer_new = np.fromstring(open(path+'sound_filtered_new.raw', mode='rb').read(), dtype='float32').reshape(length, nb_channel)
    
    out_buffer_old = out_buffer_old[backward_chunksize-chunksize:-chunksize, :]
    out_buffer_new = out_buffer_new[:out_buffer_old.shape[0], :]
    
    print(out_buffer_old.shape)
    print(out_buffer_new.shape)
    
    residuals = np.abs(out_buffer_new-out_buffer_old)
    print(np.max(residuals))
    chan = 1
    
    fig, ax = plt.subplots(nrows=3, sharex=True)
    #~ ax[0].plot(in_buffer2[:, freq_band], color = 'k')
    ax[0].plot(in_buffer[:, chan], color = 'b')
    ax[1].plot(out_buffer_old[:, chan], color = 'g')
    ax[1].plot(out_buffer_new[:, chan], color = 'r', ls='--')
    ax[2].plot(residuals[:, chan], color = 'm')
    
    #~ for i in range(nloop):
        #~ ax[1].axvline(i*chunksize)
    plt.show()
    
    
    
    
if __name__ == '__main__':
    #~ setup_files()
    #~ process_sound()
    compare_old_and_new()
