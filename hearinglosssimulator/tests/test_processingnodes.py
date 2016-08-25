import pytest
import hearinglosssimulator as hls
import numpy as np
import time
import pyacq
import pyqtgraph as pg
import helper

from pyqtgraph.Qt import QtCore, QtGui

#~ exit()

nb_channel = 2
sample_rate =44100.
chunksize = 512
nloop = 200

length = int(chunksize*nloop)

stream_spec = dict(protocol='tcp', interface='127.0.0.1', transfermode='sharedmem',
                dtype='float32', buffer_size=length, double=False, sample_rate=sample_rate)



def make_buffer():
    
    times = np.arange(length)/sample_rate
    buffer = np.random.rand(length, nb_channel) *.3
    f1, f2, speed = 500., 1000., .05
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
    
    print(dev.head, out_index)
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



    
if __name__ =='__main__':
    #~ test_DoNothing()
    #~ test_Gain()
    test_DoNothingSlow()
    


