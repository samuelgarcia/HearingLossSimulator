import pytest
import hearinglosssimulator as hls
import numpy as np
import time
import pyacq
import pyqtgraph as pg
import helper
import scipy.signal
from pyqtgraph.Qt import QtCore, QtGui

import matplotlib.pyplot as plt

#~ exit()

nb_channel = 1
sample_rate =44100.
chunksize = 512
#~ backward_chunksize = 1024
#~ backward_chunksize = 2048
#~ backward_chunksize = 1024
#~ backward_chunksize = 640
backward_chunksize = 1536
#~ backward_chunksize = 512

nloop = 200

length = int(chunksize*nloop)


def test_DoNothing():
    in_buffer = hls.moving_erb_noise(length)
    in_buffer = np.tile(in_buffer[:, None],(1, nb_channel))

    node_conf = {}
    node0, online_arrs = hls.run_one_node_offline(hls.DoNothing, in_buffer, chunksize, sample_rate, node_conf=node_conf, buffersize_margin=backward_chunksize)
    out_buffer = online_arrs['signals']
    helper.assert_arrays_equal(in_buffer, out_buffer)

def test_DoNothingSlow():
    in_buffer = hls.moving_erb_noise(length)
    in_buffer = np.tile(in_buffer[:, None],(1, nb_channel))

    node_conf = {'sleep_time':chunksize/sample_rate*0.8}
    node0, online_arrs = hls.run_one_node_offline(hls.DoNothingSlow, in_buffer, chunksize, sample_rate, node_conf=node_conf, buffersize_margin=backward_chunksize)
    out_buffer = online_arrs['signals']
    helper.assert_arrays_equal(in_buffer, out_buffer)



def test_MainProcessing1():
    #~ in_buffer = hls.moving_erb_noise(length)
    in_buffer = hls.moving_sinus(length, samplerate=sample_rate, speed = .5,  f1=100., f2=2000.,  ampl = .8)
    in_buffer = np.tile(in_buffer[:, None],(1, nb_channel))
    
    
    node_conf = dict(nb_freq_band=10, level_step=1, debug_mode=True, chunksize=chunksize, backward_chunksize=backward_chunksize)
    node0, online_arrs = hls.run_one_node_offline(hls.MainProcessing, in_buffer, chunksize, sample_rate, node_conf=node_conf, buffersize_margin=backward_chunksize)
    
    print(node0.freqs)
    
    freq_band = 3
    
    fig, ax = plt.subplots(nrows = 6, sharex=True) #, sharey=True)
    ax[0].plot(in_buffer[:, 0], color = 'k')
    
    steps = ['pgc1', 'levels', 'hpaf', 'pgc2']
    for i, k in enumerate(steps):
        
        online_arr = online_arrs[k]
        print(online_arr.shape)
        ax[i+1].plot(online_arr[:, freq_band], color = 'b')
        ax[i+1].set_ylabel(k)
    #~ ax[0].plot(offline_arr[:, 0], color = 'g')
    
    out_buffer = online_arrs['signals']
    ax[-1].plot(out_buffer[:, 0], color = 'k')
    
    plt.show()
    

def test_pgc1():
    assert nb_channel==1
    in_buffer = hls.moving_sinus(length, samplerate=sample_rate, speed = .5,  f1=500., f2=2000.,  ampl = .8)
    in_buffer = np.tile(in_buffer[:, None],(1, nb_channel))
    
    node_conf = dict(nb_freq_band=5, level_step=10, debug_mode=True, chunksize=chunksize, backward_chunksize=backward_chunksize)
    node0, online_arrs = hls.run_one_node_offline(hls.MainProcessing, in_buffer, chunksize, sample_rate, node_conf=node_conf, buffersize_margin=backward_chunksize)
    
    n = node0.nb_freq_band
    in_buffer2 = np.tile(in_buffer,(1, node0.nb_freq_band))
    online_arr = online_arrs['pgc1']
    offline_arr = in_buffer2.copy()
    for i in range(n):
        offline_arr[:, i] = scipy.signal.sosfilt(node0.coefficients_pgc[i,:,:], in_buffer2[:,i])
    offline_arr = offline_arr[:online_arr.shape[0]]
    
    
    residual = np.abs((online_arr.astype('float64')-offline_arr.astype('float64'))/np.mean(np.abs(offline_arr.astype('float64'))))
    #~ print(np.max(residual))
    
    freq_band = 4
    
    fig, ax = plt.subplots(nrows = 2, sharex=True)
    ax[0].plot(in_buffer2[:, freq_band], color = 'k')
    ax[0].plot(online_arr[:, freq_band], color = 'b')
    ax[0].plot(offline_arr[:, freq_band], color = 'g')
    ax[1].plot(residual[:, freq_band], color = 'm')
    for i in range(nloop):
        ax[1].axvline(i*chunksize)
    plt.show()
    
    assert np.max(residual)<1e-5, 'pgc1 online differt from offline'

def test_levels():
    assert nb_channel==1
    #~ in_buffer = hls.moving_sinus(length, samplerate=sample_rate, speed = .5,  f1=500., f2=2000.,  ampl = .8)
    in_buffer = hls.moving_erb_noise(length)
    in_buffer = np.tile(in_buffer[:, None],(1, nb_channel))
    
    node_conf = dict(nb_freq_band=5, level_step=10, debug_mode=True, chunksize=chunksize, backward_chunksize=backward_chunksize)
    node0, online_arrs = hls.run_one_node_offline(hls.MainProcessing, in_buffer, chunksize, sample_rate, node_conf=node_conf, buffersize_margin=backward_chunksize)
    
    freq_band = 2
    
    out_pgc1 = online_arrs['pgc1']
    hilbert_env = np.abs(scipy.signal.hilbert(out_pgc1[:, freq_band], axis=0))
    hilbert_level = 20*np.log10(hilbert_env) + node0.calibration
    
    #~ online_levels= online_arrs['levels'][:, freq_band]*node0.level_step
    online_levels= online_arrs['levels'][:, freq_band]
    online_env = 10**((online_levels-node0.calibration)/20.)
    
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


def test_hpaf():
    """
    For testing dynamic filter we take coefficient with only one level so
    it is dynamic with alwas the same coefficient
    
    """
    assert nb_channel==1
    #~ in_buffer = hls.moving_sinus(length, samplerate=sample_rate, speed = .5,  f1=500., f2=2000.,  ampl = .8)
    in_buffer = hls.moving_erb_noise(length)
    in_buffer = np.tile(in_buffer[:, None],(1, nb_channel))
    
    node_conf = dict(nb_freq_band=5, level_max=120, level_step=120, debug_mode=True, chunksize=chunksize, backward_chunksize=backward_chunksize)
    node0, online_arrs = hls.run_one_node_offline(hls.MainProcessing, in_buffer, chunksize, sample_rate, node_conf=node_conf, buffersize_margin=backward_chunksize)
    
    freq_band = 2
    
    online_pgc1 = online_arrs['pgc1']
    online_hpaf = online_arrs['hpaf']

    n = node0.nb_freq_band
    offline_hpaf = online_pgc1.copy()
    for i in range(n):
        offline_hpaf[:, i] = scipy.signal.sosfilt(node0.coefficients_hpaf[i,0, :,:], online_pgc1[:,i])

    residual = np.abs((online_hpaf.astype('float64')-offline_hpaf.astype('float64'))/np.mean(np.abs(offline_hpaf.astype('float64'))))
    print(np.max(residual))
    
    freq_band = 4
    
    fig, ax = plt.subplots(nrows = 2, sharex=True)
    ax[0].plot(online_pgc1[:, freq_band], color = 'b')
    ax[0].plot(offline_hpaf[:, freq_band], color = 'g')
    ax[0].plot(online_hpaf[:, freq_band], color = 'r', ls='--')
    ax[1].plot(residual[:, freq_band], color = 'm')
    for i in range(nloop):
        ax[1].axvline(i*chunksize)
    plt.show()
    
    assert np.max(residual)<2e-2, 'hpaf online differt from offline'


def test_pgc2():
    assert nb_channel==1
    #~ in_buffer = hls.moving_sinus(length, samplerate=sample_rate, speed = .5,  f1=50., f2=2000.,  ampl = .8)
    #~ in_buffer = hls.moving_erb_noise(length, samplerate=sample_rate,)
    in_buffer = hls.whitenoise(length, samplerate=sample_rate,)
    in_buffer = np.tile(in_buffer[:, None],(1, nb_channel))
    
    node_conf = dict(nb_freq_band=32, level_max=120, level_step=1, debug_mode=True, 
                low_freq = 60., hight_freq = 15000.,
                chunksize=chunksize, backward_chunksize=backward_chunksize)
    node0, online_arrs = hls.run_one_node_offline(hls.MainProcessing, in_buffer, chunksize, sample_rate, node_conf=node_conf, buffersize_margin=backward_chunksize)
    
    freq_band = 2
    
    online_hpaf = online_arrs['hpaf']
    online_pgc2 = online_arrs['pgc2']
    offline_pgc2 = online_pgc2.copy()
    
    n = node0.nb_freq_band
    for i in range(n):
        offline_pgc2[:, i] = scipy.signal.sosfilt(node0.coefficients_pgc[i, :,:], online_hpaf[::-1,i])[::-1]
    
    online_pgc2 = online_pgc2[:-backward_chunksize]
    offline_pgc2 = offline_pgc2[:-backward_chunksize]
    

    residual = np.abs((online_pgc2.astype('float64')-offline_pgc2.astype('float64'))/np.mean(np.abs(offline_pgc2.astype('float64')), axis=0))
    print(np.max(residual, axis=0))
    print(np.max(residual))
    
    freq_band = 4
    
    fig, ax = plt.subplots(nrows = 2, sharex=True)
    #~ ax[0].plot(online_hpaf[:, freq_band], color = 'b')
    ax[0].plot(offline_pgc2[:, freq_band], color = 'g')
    ax[0].plot(online_pgc2[:, freq_band], color = 'r', ls='--')
    ax[1].plot(residual[:, freq_band], color = 'm')
    ax[1].set_ylabel('residual for band {:0.2f}'.format(node0.freqs[freq_band]))
    for i in range(nloop):
        ax[1].axvline(i*chunksize)
    plt.show()
    
    assert np.max(residual)<2e-2, 'hpaf online differt from offline'
    

# TODO make test for residual on very low freq
    
    


    
    
    
if __name__ =='__main__':
    #~ test_DoNothing()
    test_DoNothingSlow()
    
    #~ test_MainProcessing1()
    #~ test_pgc1()
    #~ test_levels()
    #~ test_hpaf()
    #~ test_pgc2()
    


