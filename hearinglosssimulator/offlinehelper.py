import numpy as np
import time

import pyacq

import soundfile

from .invcgc import MainProcessing


def run_one_node_offline(nodeclass, in_buffer, chunksize, sample_rate, node_conf={}, dtype='float32', 
            buffersize_margin=0, time_stats=True, out_mode='full_buffer'):
    
    fake_output = pyacq.OutputStream()
    fake_output.configure(sample_rate=sample_rate, dtype=dtype, shape=(chunksize, in_buffer.shape[1]))
    
    buffer_size = in_buffer.shape[0]
    buffer_size2 = in_buffer.shape[0] + buffersize_margin
    
    
    stream_spec = dict(protocol='tcp', interface='127.0.0.1', transfermode='sharedmem',
                dtype=dtype, buffer_size=buffer_size2, double=False, sample_rate=sample_rate)
    if out_mode=='full_buffer':
        stream_spec['buffer_size'] = buffer_size2
    elif out_mode=='yield_buffer':
        stream_spec['buffer_size'] = chunksize * 2
    
    node = nodeclass(name='node_tested')
    node.configure(**node_conf)
    node.input.connect(fake_output)
    for out_name in node.outputs.keys():
        node.outputs[out_name].configure(**stream_spec)
    node.initialize()
    node.input.set_buffer(size=chunksize)
    
    
    
    def loop():
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
            #~ print(np.mean(in_chunk**2))
            
            out_index, processed_data = node.proccesing_func(index, in_chunk)
            if time_stats:
                time_durations.append(time.perf_counter()-t0)
            
            if out_index is not None:
                node.outputs['signals'].send(processed_data, index=out_index) # this normally done in NodeThread.process_data
            
            yield out_index, processed_data
        
        if time_stats:
            duration = time.perf_counter() - start0
            time_durations = np.array(time_durations)
            print('buffer duration {:0.3f}s total compute {:0.3f}s  speed {:0.1f}'.format(buffer_size/sample_rate, duration, buffer_size/sample_rate/duration))
            print('chunksize time:  {:0.1f}ms nloop {}'.format(chunksize/sample_rate*1000, time_durations.size))
            print('Compute time Mean: {:0.1f}ms Min: {:0.1f}ms Max: {:0.1f}ms'.format( time_durations.mean()*1000., time_durations.min()*1000., time_durations.max()*1000.))
    
    
    if out_mode=='full_buffer':    
        for out_index, processed_data in loop():
            pass
        
        #~ print(out_index, buffer_size)
        #~ count, bins = np.histogram(time_durations*1000., bins=np.arange(0,100,1))
        #~ import matplotlib.pyplot as plt
        #~ fig, ax = plt.subplots()
        #~ ax.plot(bins[:-1], count)
        #~ plt.show()
    
        out_buffers = {}
        if out_mode=='full_buffer':    
            for k in node.outputs.keys():
                out_buffers[k] = node.outputs[k].sender._buffer.get_data(0, out_index)
            
        return node, out_buffers
    
    elif out_mode=='yield_buffer':
        return loop()
    


def compute_numpy(sound, sample_rate, **params):
    """
    
    """
    assert isinstance(sound, np.ndarray)
    
    if sound.ndim==1:
        sound = sound[:, None]
        onedim = True
    else:
        onedim = False
    
    sound = sound.astype('float32')
    
    chunksize = params['chunksize']
    backward_chunksize =  params['backward_chunksize']
    
    node, out_buffers = run_one_node_offline(MainProcessing, sound, chunksize, sample_rate, node_conf=params, dtype='float32', 
            buffersize_margin=backward_chunksize, time_stats=False, out_mode='full_buffer')
    out_sound = out_buffers['signals']
    
    if onedim:
        out_sound = out_sound[:, 0]
    
    return out_sound



class WaveNumpy:
    """
    Fake numpy buffer?
    """
    def __init__(self, wav_filename):
        self.file = soundfile.SoundFile(wav_filename, 'r', )
        self.shape = (len(self.file), self.file.channels)
    
    def __getitem__(self, sl):
        assert isinstance(sl, tuple)
        assert len(sl) == 2
        sl0, sl1 = sl[0], sl[1]
        assert sl0.step is None
        self.file.seek(sl0.start)
        buf = self.file.read(frames=sl0.stop-sl0.start,dtype='float32', always_2d=True)
        buf = buf[:, sl1]
        #~ print(sl, np.mean(buf**2), np.max(np.abs(buf)))
        return buf
        
        
        

def compute_wave_file(in_filename, out_filename, duration_limit=None, **params):
    assert in_filename != out_filename
    buffer_in = WaveNumpy(in_filename)
    in_wav = buffer_in.file
    out_wav = soundfile.SoundFile(out_filename, 'w', channels=in_wav.channels, samplerate=in_wav.samplerate, subtype='FLOAT')
    
    sample_rate = float(in_wav.samplerate)
    
    nb_channel = in_wav.channels
    chunksize = params['chunksize']
    backward_chunksize =  params['backward_chunksize']
    if len(params['loss_weigth'])<nb_channel:
        params['loss_weigth'] = params['loss_weigth']*nb_channel
    
    
    
    iter = run_one_node_offline(MainProcessing, buffer_in, chunksize, sample_rate, node_conf=params, dtype='float32', 
            buffersize_margin=backward_chunksize, time_stats=False, out_mode='yield_buffer')
    
    for i, (out_index, processed_data) in enumerate(iter):
        #~ print(i, out_index)
        if processed_data is not None:
            #~ print(processed_data.shape)
            out_wav.write(processed_data)
        
        #~ print(duration_limit, out_index, sample_rate)
        if duration_limit is not None and out_index is not None and\
                out_index/sample_rate>=duration_limit:
            print('break')
            break
        
        
        #~ if 
    
    #~ node, out_buffers
