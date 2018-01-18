import pytest

import numpy as np
import scipy.signal
import matplotlib.pyplot as plt
from matplotlib.cm import get_cmap

import hearinglosssimulator as hls
import helper

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

nloop = 20

length = int(chunksize*nloop)



def test_invcomp():
    #~ in_buffer = hls.moving_erb_noise(length)
    in_buffer = hls.moving_sinus(length, sample_rate=sample_rate, speed = .5,  f1=100., f2=2000.,  ampl = .8)
    in_buffer = np.tile(in_buffer[:, None],(1, nb_channel))
    #~ print(in_buffer.shape)
    #~ exit()
    
    loss_params = { 'left' : {'freqs' : [ 125*2**i  for i in range(7) ], 'compression_degree': [0]*7, 'passive_loss_db' : [0]*7 } }
    loss_params['right'] = loss_params['left']
    processing_conf = dict(nb_freq_band=32, level_step=1., level_max = 100., loss_params=loss_params, 
                low_freq=100., high_freq=15000.,
                debug_mode=True, chunksize=chunksize, backward_chunksize=backward_chunksize)
    processing, online_arrs = hls.run_class_offline(hls.InvComp, in_buffer, chunksize, sample_rate, processing_conf=processing_conf, buffersize_margin=backward_chunksize)
    
    
    print('nlevel', processing.levels.size, 'nb_freq_band', processing.nb_freq_band)
    
    freq_band = 15
    
    fig, ax = plt.subplots(nrows = 7, sharex=True) #, sharey=True)
    ax[0].plot(in_buffer[:, 0], color = 'k')
    
    steps = ['pgc1', 'levels', 'dyngain', 'pgc2', 'passive']
    for i, k in enumerate(steps):
        
        online_arr = online_arrs[k]
        print(online_arr.shape)
        ax[i+1].plot(online_arr[:, freq_band], color = 'b')
        ax[i+1].set_ylabel(k)
    #~ ax[0].plot(offline_arr[:, 0], color = 'g')
    
    out_buffer = online_arrs['main_output']
    ax[-1].plot(out_buffer[:, 0], color = 'k')
    
    
    if nb_channel==2:
        #test stereo is like mono
        #~ fig, ax = plt.subplots()
        #~ ax.plot(out_buffer[:,0], color='b')
        #~ ax.plot(out_buffer[:,1], color='r')
        #~ fig, ax = plt.subplots()
        #~ ax.plot(out_buffer[:,0]-out_buffer[:,1], color='b')
        #~ plt.show()
        assert np.all(np.abs(out_buffer[:,0]-out_buffer[:,1])<1e-5)

    
    
    plt.show()
    

def test_pgc1():
    assert nb_channel==1
    in_buffer = hls.moving_sinus(length, sample_rate=sample_rate, speed = .5,  f1=500., f2=2000.,  ampl = .8)
    in_buffer = np.tile(in_buffer[:, None],(1, nb_channel))
    
    loss_params = { 'left' : {'freqs' : [ 125*2**i  for i in range(7) ], 'compression_degree': [0]*7, 'passive_loss_db' : [0]*7 } }
    loss_params['right'] = loss_params['left']

    processing_conf = dict(nb_freq_band=5, level_step=10, debug_mode=True, chunksize=chunksize, backward_chunksize=backward_chunksize, loss_params=loss_params)
    processing, online_arrs = hls.run_class_offline(hls.InvComp, in_buffer, chunksize, sample_rate, processing_conf=processing_conf, buffersize_margin=backward_chunksize)
    
    n = processing.nb_freq_band
    in_buffer2 = np.tile(in_buffer,(1, processing.nb_freq_band))
    online_arr = online_arrs['pgc1']
    offline_arr = in_buffer2.copy()
    for i in range(n):
        offline_arr[:, i] = scipy.signal.sosfilt(processing.coefficients_pgc[i,:,:], in_buffer2[:,i])
    offline_arr = offline_arr[:online_arr.shape[0]]
    
    
    residual = np.abs((online_arr.astype('float64')-offline_arr.astype('float64'))/np.mean(np.abs(offline_arr.astype('float64'))))
    #~ print(np.max(residual))
    
    freq_band = 4
    
    fig, ax = plt.subplots(nrows = 2, sharex=True)
    #~ ax[0].plot(in_buffer2[:, freq_band], color = 'k')
    ax[0].plot(offline_arr[:, freq_band], color = 'g')
    ax[0].plot(online_arr[:, freq_band], color = 'r', ls='--')
    ax[1].plot(residual[:, freq_band], color = 'm')
    for i in range(nloop):
        ax[1].axvline(i*chunksize)
    plt.show()
    
    #~ print(np.argmax(residual), np.max(residual))
    assert np.max(residual)<1e-5, 'pgc1 online differt from offline {}'.format(np.max(residual))

def test_levels():
    assert nb_channel==1
    #~ in_buffer = hls.moving_sinus(length, sample_rate=sample_rate, speed = .5,  f1=500., f2=2000.,  ampl = .8)
    in_buffer = hls.moving_erb_noise(length)
    in_buffer = np.tile(in_buffer[:, None],(1, nb_channel))
    
    loss_params = { 'left' : {'freqs' : [ 125*2**i  for i in range(7) ], 'compression_degree': [0]*7, 'passive_loss_db' : [0]*7 } }
    loss_params['right'] = loss_params['left']
    
    processing_conf = dict(nb_freq_band=5, level_step=10, debug_mode=True, chunksize=chunksize, backward_chunksize=backward_chunksize, loss_params=loss_params)
    processing, online_arrs = hls.run_class_offline(hls.InvComp, in_buffer, chunksize, sample_rate, processing_conf=processing_conf, buffersize_margin=backward_chunksize)
    
    freq_band = 2
    
    out_pgc1 = online_arrs['pgc1']
    hilbert_env = np.abs(scipy.signal.hilbert(out_pgc1[:, freq_band], axis=0))
    hilbert_level = 20*np.log10(hilbert_env) + processing.calibration
    
    #~ online_levels= online_arrs['levels'][:, freq_band]*processing.level_step
    online_levels= online_arrs['levels'][:, freq_band]
    online_env = 10**((online_levels-processing.calibration)/20.)
    
    residual = np.abs((online_levels.astype('float64')-hilbert_level.astype('float64'))/np.mean(np.abs(online_levels.astype('float64'))))
    residual[:100] = 0
    residual[-100:] = 0
    print(np.max(residual))
    
    #~ assert np.max(residual)<3e-2, 'levelfrom hilbert offline'
    
    fig, ax = plt.subplots(nrows = 2, sharex=True)
    ax[0].plot(out_pgc1[:, freq_band], color = 'k', alpha=.8)
    ax[0].plot(np.abs(out_pgc1[:, freq_band]), color = 'k', ls='--', alpha=.8)
    ax[0].plot(hilbert_env, color = 'g', lw=2)
    ax[0].plot(online_env, color = 'r', lw=2)
    
    ax[1].plot(online_levels, color='r')
    ax[1].plot(hilbert_level, color='g')
    
    ax[1].set_ylabel('level dB')
    
    plt.show()


def test_dyngain():
    """
    For testing dynamic gain we take coefficient with only one level so
    it is dynamic with alwas the same coefficient.
    
    """
    assert nb_channel==1
    #~ in_buffer = hls.moving_sinus(length, sample_rate=sample_rate, speed = .5,  f1=500., f2=2000.,  ampl = .8)
    in_buffer = hls.moving_erb_noise(length)
    in_buffer = np.tile(in_buffer[:, None],(1, nb_channel))
    
    loss_params = { 'left' : {'freqs' : [ 125*2**i  for i in range(7) ], 'compression_degree': [0]*7, 'passive_loss_db' : [0]*7 } }
    loss_params['right'] = loss_params['left']
    
    processing_conf = dict(nb_freq_band=5, level_max=120, level_step=120, debug_mode=True, chunksize=chunksize, backward_chunksize=backward_chunksize, loss_params=loss_params)
    processing, online_arrs = hls.run_class_offline(hls.InvComp, in_buffer, chunksize, sample_rate, processing_conf=processing_conf, buffersize_margin=backward_chunksize)
    
    #~ assert len(processing.levels)==1
    freq_band = 2
    
    online_pgc1 = online_arrs['pgc1']
    online_dyngain = online_arrs['dyngain']

    n = processing.nb_freq_band
    offline_dyngain = online_pgc1.copy()
    for i in range(n):
        offline_dyngain[:, i] = online_pgc1[:, i] * processing.gain_controlled[i,0]
        print(processing.gain_controlled[i,0])

    residual = np.abs((online_dyngain.astype('float64')-offline_dyngain.astype('float64'))/np.mean(np.abs(offline_dyngain.astype('float64'))))
    print(np.max(residual))
    
    freq_band = 4
    
    fig, ax = plt.subplots(nrows = 2, sharex=True)
    #~ ax[0].plot(online_pgc1[:, freq_band], color = 'b')
    ax[0].plot(offline_dyngain[:, freq_band], color = 'g')
    ax[0].plot(online_dyngain[:, freq_band], color = 'r', ls='--')
    ax[1].plot(residual[:, freq_band], color = 'm')
    for i in range(nloop):
        ax[1].axvline(i*chunksize)
    plt.show()
    
    assert np.max(residual)<2e-2, 'hpaf online differt from offline'


def test_pgc2():
    assert nb_channel==1
    #~ in_buffer = hls.moving_sinus(length, sample_rate=sample_rate, speed = .5,  f1=50., f2=2000.,  ampl = .8)
    #~ in_buffer = hls.moving_erb_noise(length, sample_rate=sample_rate,)
    in_buffer = hls.whitenoise(length, sample_rate=sample_rate,)
    in_buffer = np.tile(in_buffer[:, None],(1, nb_channel))
    
    loss_params = { 'left' : {'freqs' : [ 125*2**i  for i in range(7) ], 'compression_degree': [0]*7, 'passive_loss_db' : [0]*7 } }
    loss_params['right'] = loss_params['left']
    
    processing_conf = dict(nb_freq_band=32, level_max=120, level_step=1, debug_mode=True, 
                low_freq = 60., high_freq = 15000.,
                loss_params = loss_params,
                chunksize=chunksize, backward_chunksize=backward_chunksize)
    processing, online_arrs = hls.run_class_offline(hls.InvComp, in_buffer, chunksize, sample_rate, processing_conf=processing_conf, buffersize_margin=backward_chunksize)
    
    freq_band = 4
    
    online_dyngain = online_arrs['dyngain']
    online_pgc2 = online_arrs['pgc2']
    offline_pgc2 = online_pgc2.copy()
    
    n = processing.nb_freq_band
    for i in range(n):
        offline_pgc2[:, i] = scipy.signal.sosfilt(processing.coefficients_pgc[i, :,:], online_dyngain[::-1,i])[::-1]
    
    online_pgc2 = online_pgc2[:-backward_chunksize]
    offline_pgc2 = offline_pgc2[:-backward_chunksize]
    

    residual = np.abs((online_pgc2.astype('float64')-offline_pgc2.astype('float64'))/np.mean(np.abs(offline_pgc2.astype('float64')), axis=0))
    print(np.max(residual, axis=0))
    print(np.max(residual))
    
    #~ freq_band = 4
    
    fig, ax = plt.subplots(nrows = 2, sharex=True)
    #~ ax[0].plot(online_hpaf[:, freq_band], color = 'b')
    ax[0].plot(offline_pgc2[:, freq_band], color = 'g')
    ax[0].plot(online_pgc2[:, freq_band], color = 'r', ls='--')
    ax[1].plot(residual[:, freq_band], color = 'm')
    ax[1].set_ylabel('residual for band {:0.2f}'.format(processing.freqs[freq_band]))
    for i in range(nloop):
        ax[1].axvline(i*chunksize)
    plt.show()
    
    # TODO make one values per band
    assert np.max(residual)<2e-2, 'hpaf online differt from offline'


def test_passive_loss():
    in_buffer = hls.moving_sinus(length, sample_rate=sample_rate, speed = .5,  f1=500., f2=2000.,  ampl = .8)
    in_buffer = np.tile(in_buffer[:, None],(1, nb_channel))
    
    loss_params = { 'left' : {'freqs' : [ 125*2**i  for i in range(7) ], 'compression_degree': [1.]*7, 'passive_loss_db' : [-20.]*7 } }
    loss_params['right'] = loss_params['left']

    processing_conf = dict(nb_freq_band=32, level_step=10, debug_mode=True, chunksize=chunksize, backward_chunksize=backward_chunksize, loss_params=loss_params)
    processing, online_arrs = hls.run_class_offline(hls.InvComp, in_buffer, chunksize, sample_rate, processing_conf=processing_conf, buffersize_margin=backward_chunksize)
    
    n = processing.nb_freq_band
    
    online_pgc2 = online_arrs['pgc2']
    online_passive = online_arrs['passive']
    #~ offline_passive = online_pgc2.copy()
    
    
    #~ channels = ('left', 'right')[:nb_channel]
    
    #~ for c, chan in enumerate(channels):
        #~ for i in range(n):
            #~ offline_passive[:, c*n + i] = processing.passive_gain[c*n + i] * online_pgc2
    offline_passive = processing.passive_gain.T * online_pgc2
    
    residual = np.abs((online_passive.astype('float64')-offline_passive.astype('float64'))/np.mean(np.abs(offline_passive.astype('float64'))))
    print(np.max(residual))
    
    freq_band = 15
    
    fig, ax = plt.subplots(nrows = 2, sharex=True)
    #~ ax[0].plot(in_buffer2[:, freq_band], color = 'k')
    ax[0].plot(offline_passive[:, freq_band], color = 'g')
    ax[0].plot(online_passive[:, freq_band], color = 'r', ls='--')
    ax[1].plot(residual[:, freq_band], color = 'm')
    for i in range(nloop):
        ax[1].axvline(i*chunksize)
    plt.show()
    
    assert np.max(residual)<1e-4, 'passive online differt from offline'
    
    
    
    
if __name__ =='__main__':
    #~ test_invcomp()
    #~ test_pgc1()
    #~ test_levels()
    #~ test_dyngain()
    test_pgc2()
    #~ test_passive_loss()
    


