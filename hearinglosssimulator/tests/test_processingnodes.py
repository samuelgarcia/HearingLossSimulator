import pytest
import hearinglosssimulator as hls
import numpy as np
import time
import pyacq
import pyqtgraph as pg

from pyqtgraph.Qt import QtCore, QtGui

#~ exit()

nb_channel = 2
sample_rate =44100.
chunksize = 512
nloop = 200

stream_spec = dict(protocol='tcp', interface='127.0.0.1', transfertmode='sharedmem',
                dtype = 'float32',buffer_size=chunksize*4)


def setup_dev():
    length = int(chunksize*nloop)
    times = np.arange(length)/sample_rate
    buffer = np.random.rand(length, nb_channel) *.3
    f1, f2, speed = 500., 1000., .05
    freqs = (np.sin(np.pi*2*speed*times)+1)/2 * (f2-f1) + f1
    phases = np.cumsum(freqs/sample_rate)*2*np.pi
    ampl = np.abs(np.sin(np.pi*2*speed*8*times))*.8
    buffer += (np.sin(phases)*ampl)[:, None]
    buffer = buffer.astype('float32')
    
    man = pyacq.create_manager(auto_close_at_exit=False)
    nodegroup0 = man.create_nodegroup()
    


    dev = nodegroup0.create_node('NumpyDeviceBuffer', name='dev')
    dev.configure(nb_channel=nb_channel, sample_interval=1./sample_rate, chunksize=chunksize, buffer=buffer)
    dev.output.configure(**stream_spec)
    dev.initialize()


    return man, dev

    


def test_DoNothing():
    
    app = pg.mkQApp()
    
    man, dev = setup_dev()
    
    nodegroup1 = man.create_nodegroup()
    
    nodegroup1.register_node_type_from_module('hearinglosssimulator', 'DoNothing')
    
    donothing0 = nodegroup1.create_node('DoNothing')
    donothing0.configure()
    donothing0.input.connect(dev.output)
    donothing0.output.configure(**stream_spec)
    donothing0.initialize()

    donothing1 = hls.DoNothing()
    donothing1.configure()
    donothing1.input.connect(donothing0.output)
    donothing1.output.configure(**stream_spec)
    donothing1.initialize()
    donothing1.input.set_buffer()
    
    
    dev.start()
    donothing0.start()
    donothing1.start()
    
    
    def terminate():
        print('terminate')
        dev.stop()
        donothing0.stop()
        donothing1.stop()
        app.quit()

    # start for a while
    timer = QtCore.QTimer(singleShot=True, interval=2000)
    timer.timeout.connect(terminate)
    timer.start()
    
    app.exec_()
    print('yep')
    
    
    man.close()
    
    outbuffrer = donothing1.input[:]
    
    print(outbuffrer.shape)
    

    
if __name__ =='__main__':
    test_DoNothing()
