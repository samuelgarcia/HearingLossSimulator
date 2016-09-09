import numpy as np
import time

import pyacq


def run_one_node_offline(nodeclass, in_buffer, chunksize, sample_rate, node_conf={}, dtype='float32', 
            buffersize_margin=0, time_stats=True):
    
    fake_output = pyacq.OutputStream()
    fake_output.configure(sample_rate=sample_rate, dtype=dtype, shape=(chunksize, in_buffer.shape[1]))
    
    buffer_size = in_buffer.shape[0]
    buffer_size2 = in_buffer.shape[0] + buffersize_margin
    
    stream_spec = dict(protocol='tcp', interface='127.0.0.1', transfermode='sharedmem',
                dtype=dtype, buffer_size=buffer_size2, double=False, sample_rate=sample_rate)

    node = nodeclass(name='node_tested')
    node.configure(**node_conf)
    node.input.connect(fake_output)
    for out_name in node.outputs.keys():
        node.outputs[out_name].configure(**stream_spec)
    node.initialize()
    node.input.set_buffer(size=chunksize)
    
    
    if time_stats:
        time_durations = []
        start0 = time.perf_counter()
    nloop = buffer_size//chunksize
    index = 0
    out_index = None
    while out_index is None or out_index<buffer_size:
        index += chunksize
        if index<=buffer_size:
            in_chunk = in_buffer[index-chunksize:index, :]
        else:
            in_chunk = np.zeros((chunksize, in_buffer.shape[1]), dtype=dtype)
            #~ print('zeros at end')
        if time_stats:
            t0 = time.perf_counter()
        out_index, processed_data = node.proccesing_func(index, in_chunk)
        if time_stats:
            time_durations.append(time.perf_counter()-t0)
        
        if out_index is not None:
            node.outputs['signals'].send(processed_data, index=out_index) # this normally done in NodeThread.process_data
        #~ print(out_index, buffer_size)

    if time_stats:
        duration = time.perf_counter() - start0
        time_durations = np.array(time_durations)
        print('buffer duration {:0.3f}s total compute {:0.3f}s  speed {:0.1f}'.format(buffer_size/sample_rate, duration, buffer_size/sample_rate/duration))
        print('chunksize time:  {:0.1f}ms nloop {}'.format(chunksize/sample_rate*1000, time_durations.size))
        print('Compute time Mean: {:0.1f}ms Min: {:0.1f}ms Max: {:0.1f}ms'.format( time_durations.mean()*1000., time_durations.min()*1000., time_durations.max()*1000.))
        
        #~ count, bins = np.histogram(time_durations*1000., bins=np.arange(0,100,1))
        #~ import matplotlib.pyplot as plt
        #~ fig, ax = plt.subplots()
        #~ ax.plot(bins[:-1], count)
        #~ plt.show()
    
    
    out_buffers = {}
    for k in node.outputs.keys():
        out_buffers[k] = node.outputs[k].sender._buffer.get_data(0, out_index)
        
    return node, out_buffers
    
    
    
    
    
    



def compute(sound):
    
    damaged_sound = sound
    
    
    return damaged_sound
