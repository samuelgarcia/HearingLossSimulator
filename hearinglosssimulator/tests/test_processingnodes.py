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



def make_buffer():
    
    times = np.arange(length)/sample_rate
    buffer = np.random.rand(length, nb_channel) *.3
    f1, f2, speed = 500., 3000., .05
    freqs = (np.sin(np.pi*2*speed*times)+1)/2 * (f2-f1) + f1
    phases = np.cumsum(freqs/sample_rate)*2*np.pi
    ampl = np.abs(np.sin(np.pi*2*speed*8*times))*.8
    buffer += (np.sin(phases)*ampl)[:, None]
    sound = buffer.astype('float32')
    
    return sound


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
    node0.output.configure(**stream_spec)
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
    
    out_index = node0.output.sender._buffer.index()
    
    #~ print(dev.head, out_index)
    assert dev.head-2*chunksize<out_index, 'Too slow!!! {} {}'.format(dev.head, out_index)
    #~ print(ind)
    #~ print()
    
    out_buffer = node0.output.sender._buffer.get_data(0, out_index)
    
    return out_buffer



def test_DoNothing():
    in_buffer = make_buffer()
    out_buffer = run_one_node(hls.DoNothing, in_buffer, duration=2., background=False) #background = True
    helper.assert_arrays_equal(in_buffer[:out_buffer.shape[0]], out_buffer)


def test_Gain():
    in_buffer = make_buffer()
    out_buffer = run_one_node(hls.Gain, in_buffer, duration=2., background=False, node_conf={'factor':-1.}) #background = True
    helper.assert_arrays_equal(in_buffer[:out_buffer.shape[0]], -out_buffer)

def test_DoNothingSlow():
    in_buffer = make_buffer()
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
    in_buffer = hls.moving_erb_noise(length)[:, None]
    
    node_conf = dict(nb_freq_band=5, level_step=10)
    online_arr = run_one_node(hls.MainProcessing, in_buffer, duration=2., background=False, node_conf=node_conf) #background = True
    
    
    
    
    
    
    
    
if __name__ =='__main__':
    #~ test_DoNothing()
    #~ test_Gain()
    #~ test_DoNothingSlow()
    
    test_MainProcessing1()


