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
backward_chunksize = 1024
nloop = 200

length = int(chunksize*nloop)

stream_spec = dict(protocol='tcp', interface='127.0.0.1', transfermode='sharedmem',
                dtype='float32', buffer_size=length, double=False, sample_rate=sample_rate)


def run_one_node(nodeclass, in_buffer, duration=2., background = False, node_conf={}): #background = True
    app = pg.mkQApp()
    
    if background:
        man = pyacq.create_manager(auto_close_at_exit=False)
        nodegroup0 = man.create_nodegroup()
        dev = nodegroup0.create_node('NumpyDeviceBuffer', name='dev')
    else:
        man = None
        dev = pyacq.NumpyDeviceBuffer()
        
    dev.configure(nb_channel=nb_channel, sample_interval=1./sample_rate, chunksize=chunksize, buffer=in_buffer)
    dev.output.configure(**stream_spec)
    dev.initialize()
    
    
    if background:
        nodegroup1 = man.create_nodegroup()
        nodegroup1.register_node_type_from_module('hearinglosssimulator', nodeclass.__name__)
        node0 = nodegroup1.create_node('DoNothing', name='donothing0')
    else:
        node0 = nodeclass(name='node_tested')
        
    node0.configure(**node_conf)
    node0.input.connect(dev.output)
    for out_name in node0.outputs.keys():
        node0.outputs[out_name].configure(**stream_spec)
    node0.initialize()
    node0.input.set_buffer(size=length)

    dev.start()
    node0.start()
    
    def terminate():
        #~ print('terminate')
        dev.stop()
        node0.stop()
        app.quit()

    # start for a while
    timer = QtCore.QTimer(singleShot=True, interval=duration*1000)
    timer.timeout.connect(terminate)
    timer.start()
    
    app.exec_()
    
    if background:
        man.close()
    
    out_index = node0.outputs['signals'].sender._buffer.index()
    
    #~ print(dev.head, out_index)
    #~ assert dev.head-2*chunksize<out_index, 'Too slow!!! {} {}'.format(dev.head, out_index)
    #~ print(ind)
    #~ print()
    
    out_buffers = {}
    for k in node0.outputs.keys():
        out_buffers[k] = node0.outputs[k].sender._buffer.get_data(0, out_index)
        
    #~ out_buffer = node0.output.sender._buffer.get_data(0, out_index)
    
    return node0, out_buffers



def test_DoNothing():
    in_buffer = hls.moving_erb_noise(length)
    in_buffer = np.tile(in_buffer[:, None],(1, nb_channel))

    out_buffer = run_one_node(hls.DoNothing, in_buffer, duration=2., background=False) #background = True
    helper.assert_arrays_equal(in_buffer[:out_buffer.shape[0]], out_buffer)


def test_Gain():
    in_buffer = hls.moving_erb_noise(length)
    in_buffer = np.tile(in_buffer[:, None],(1, nb_channel))

    out_buffer = run_one_node(hls.Gain, in_buffer, duration=2., background=False, node_conf={'factor':-1.}) #background = True
    helper.assert_arrays_equal(in_buffer[:out_buffer.shape[0]], -out_buffer)

def test_DoNothingSlow():
    in_buffer = hls.moving_erb_noise(length)
    in_buffer = np.tile(in_buffer[:, None],(1, nb_channel))

    out_buffer = run_one_node(hls.DoNothingSlow, in_buffer, duration=2., background=False, node_conf={'chunksize':chunksize}) #background = True
    helper.assert_arrays_equal(in_buffer[:out_buffer.shape[0]], out_buffer)


"""
def test_CL_SosFilter():
    nb_section = 8
    
    in_buffer = make_buffer()
    coefficients = scipy.signal.iirfilter(nb_section, [0.1, .4], btype='bandpass',
                    analog=False, ftype='bessel', output='sos')
    coefficients = np.tile(coefficients[None,:,:], (nb_channel, 1,1))
    
    print(coefficients.shape)
    node_conf = dict(coefficients=coefficients, chunksize=chunksize, backward_chunksize=backward_chunksize)
    online_arr = run_one_node(hls.CL_SosFilter, in_buffer, duration=2., background=False, node_conf=node_conf) #background = True
    

    offline_arr = in_buffer.copy()
    for i in range(nb_channel):
        offline_arr[:, i] = scipy.signal.sosfilt(coefficients[i,:,:], in_buffer[:,i])
    
    offline_arr = offline_arr[:online_arr.shape[0]]
    
    residual = np.abs((online_arr.astype('float64')-offline_arr.astype('float64'))/np.mean(np.abs(offline_arr.astype('float64'))))
    print(np.max(residual))
    
    
    fig, ax = plt.subplots(nrows = 2, sharex=True)
    ax[0].plot(in_buffer[:, 0], color = 'k')
    ax[0].plot(online_arr[:, 0], color = 'b')
    ax[0].plot(offline_arr[:, 0], color = 'g')
    #~ ax[1].plot((out_scipy_offline[:, 0]-out_buffer[:, 0])/np.mean(out_scipy_offline[:, 0]*out_buffer[:, 0]), color = 'm')
    ax[1].plot(residual[:, 0], color = 'm')
    for i in range(nloop):
        ax[1].axvline(i*chunksize)
    plt.show()
    
    assert np.max(residual)<1e-5, 'CL_SosFilter online differt from offline'

"""


def test_MainProcessing1():
    #~ in_buffer = hls.moving_erb_noise(length)
    in_buffer = hls.moving_sinus(length, samplerate=sample_rate, speed = .5,  f1=100., f2=2000.,  ampl = .8)
    in_buffer = np.tile(in_buffer[:, None],(1, nb_channel))
    
    
    node_conf = dict(nb_freq_band=5, level_step=10, debug_mode=True, chunksize=chunksize, backward_chunksize=backward_chunksize)
    node0, online_arrs = run_one_node(hls.MainProcessing, in_buffer, duration=2., background=False, node_conf=node_conf) #background = True
    
    
    print(node0.freqs)
    
    freq_band = 2
    
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
    node0, online_arrs = run_one_node(hls.MainProcessing, in_buffer, duration=2., background=False, node_conf=node_conf) #background = True
    
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
    
    assert np.max(residual)<1e-5, 'CL_SosFilter online differt from offline'

def test_levels():
    assert nb_channel==1
    #~ in_buffer = hls.moving_sinus(length, samplerate=sample_rate, speed = .5,  f1=500., f2=2000.,  ampl = .8)
    in_buffer = hls.moving_erb_noise(length)
    in_buffer = np.tile(in_buffer[:, None],(1, nb_channel))
    
    node_conf = dict(nb_freq_band=5, level_step=10, debug_mode=True, chunksize=chunksize, backward_chunksize=backward_chunksize)
    node0, online_arrs = run_one_node(hls.MainProcessing, in_buffer, duration=2., background=False, node_conf=node_conf) #background = True
    
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
    assert nb_channel==1
    #~ in_buffer = hls.moving_sinus(length, samplerate=sample_rate, speed = .5,  f1=500., f2=2000.,  ampl = .8)
    in_buffer = hls.moving_erb_noise(length)
    in_buffer = np.tile(in_buffer[:, None],(1, nb_channel))
    
    node_conf = dict(nb_freq_band=5, level_step=10, debug_mode=True, chunksize=chunksize, backward_chunksize=backward_chunksize)
    node0, online_arrs = run_one_node(hls.MainProcessing, in_buffer, duration=2., background=False, node_conf=node_conf) #background = True
    
    freq_band = 2
    
    out_hpaf = online_arrs['hpaf']

    
    
    
if __name__ =='__main__':
    #~ test_DoNothing()
    #~ test_Gain()
    #~ test_DoNothingSlow()
    
    test_MainProcessing1()
    #~ test_pgc1()
    #~ test_levels()
    #~ test_hpaf()
    


