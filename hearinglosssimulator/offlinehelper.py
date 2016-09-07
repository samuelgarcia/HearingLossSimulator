import numpy as np
import pyacq


def run_one_node_offline(nodeclass, in_buffer, chunksize, sample_rate, node_conf={}, buffersize_margin=0, dtype='float32'):
    
    fake_output = pyacq.OutputStream()
    fake_output.configure(sample_rate=sample_rate, dtype=dtype)
    
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
        out_index, processed_data = node.proccesing_func(index, in_chunk)
        if out_index is not None:
            node.outputs['signals'].send(processed_data, index=out_index) # this normally done in NodeThread.process_data
        print(out_index, buffer_size)
        
    out_buffers = {}
    for k in node.outputs.keys():
        out_buffers[k] = node.outputs[k].sender._buffer.get_data(0, out_index)
        
    return node, out_buffers
    
    
    
    
    
    



def compute(sound):
    
    damaged_sound = sound
    
    
    return damaged_sound
