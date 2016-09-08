import os
import time

import numpy as np
import scipy.signal
import scipy.interpolate

from pyqtgraph.Qt import QtCore
import pyqtgraph as pg
from pyqtgraph.util.mutex import Mutex

import pyopencl
mf = pyopencl.mem_flags


import pyacq

from .filterfactory import (gammatone, asymmetric_compensation_coeffs, loggammachirp, erbspace)
from .tools import sosfreqz



"""
Note:
  * NodeThread and BaseProcessingNode should be move to pyacq
  

2 possibilities:
  * each is step is one pyacq.Node > more easy to debug but overhead in stream between nodes> finnaly this do not work because of multiple input for CL_DynamicSosFilter
  * all step are in one pyacq.Node > choosen solution. For debug each step have an optional output.
  
  
# CL_DynamicSosFilter hard to fit the frame because 2 input...
# 


"""

class NodeThread(pyacq.ThreadPollInput):
    def __init__(self, input_stream, output_stream, proccesing_func,  timeout = 200, parent = None):
        pyacq.ThreadPollInput.__init__(self, input_stream, timeout = timeout, return_data=True, parent = parent)
        self.output_stream = output_stream
        self.proccesing_func = proccesing_func

    def process_data(self, pos, data):
        pos2, processed_data = self.proccesing_func(pos, data)
        if pos2 is not None:
            self.output_stream.send(processed_data, index=pos2)

class BaseProcessingNode(pyacq.Node,  QtCore.QObject):
    _input_specs = {'signals' : dict(streamtype = 'signals')}
    _output_specs = {'signals' : dict(streamtype = 'signals')}
    
    def __init__(self, parent = None, **kargs):
        QtCore.QObject.__init__(self, parent)
        pyacq.Node.__init__(self, **kargs)
    
    def _configure(self):
        pass
        #~ print(self.name, self.output.params)
    
    def after_input_connect(self, inputname):
        # this automatically propagate 'sample_rate', 'dtype', 'shape'
        # to output spec
        # in case of a Node that change sample_rate or the number of channel 
        # this must be overwirtten
        self.nb_channel = self.input.params['shape'][1]
        for k in ['sample_rate', 'dtype', 'shape']:
            self.outputs['signals'].spec[k] = self.input.params[k]
        
    
    def _initialize(self):
        self.thread = NodeThread(self.input, self.outputs['signals'], self.proccesing_func)
        #~ self.thread.set_params(self.engine, self.coefficients, self.nb_channel,
                            #~ self.output.params['dtype'], self.chunksize)
    
    def _start(self):
        print
        self.thread.last_pos = None
        self.thread.start()
    
    def _stop(self):
        self.thread.stop()
        self.thread.wait()
    
    def proccesing_func(self, pos, data):
        raise(NotImplementedError)
    
    #~ def set_coefficients(self, coefficients):
        #~ self.coefficients = coefficients
        #~ if self.initialized():
            #~ self.thread.set_params(self.engine, self.coefficients, self.nb_channel,
                                #~ self.output.params['dtype'], self.chunksize)


cl_code_filename = os.path.join(os.path.dirname(__file__), 'cl_processing.cl')
with open(cl_code_filename, mode='r') as f:
    cl_code = f.read()


class CL_BaseProcessingNode(BaseProcessingNode):
    #~ def __init__(self, **kargs):
        #~ BaseProcessingNode.__init__(self, **kargs)
    
    def _configure(self, gpu_platform_index=None, gpu_device_index=None):
        self.gpu_platform_index = gpu_platform_index
        self.gpu_device_index = gpu_device_index
    
    def after_input_connect(self, inputname):
        BaseProcessingNode.after_input_connect(self, inputname)
        # maybe patch here to test if harware support float64
        assert self.input.params['dtype'] == np.dtype('float32')
    
    def _initialize(self):
        BaseProcessingNode._initialize(self)
        if self.gpu_platform_index is None:
            self.ctx = pyopencl.create_some_context()
        else:
            self.devices =  [pyopencl.get_platforms()[self.gpu_platform_index].get_devices()[self.gpu_device_index] ]
            self.ctx = pyopencl.Context(self.devices)        
        self.queue = pyopencl.CommandQueue(self.ctx)
        print(self.ctx)
        
        self.initlalize_cl()
    
    def initlalize_cl(self):
        self.opencl_prg = None
        self.global_size = None
        self.local_size = None
        raise(NotImplementedError)
        
    
    
    
        


## Nodes

class DoNothing(BaseProcessingNode):
    def proccesing_func(self, pos, data):
        return pos, data

class DoNothingSlow(BaseProcessingNode):
    def _configure(self, sleep_time=None):
        self.sleep_time = sleep_time
    
    def proccesing_func(self, pos, data):
        time.sleep(self.sleep_time)
        return pos, data



class MainProcessing(CL_BaseProcessingNode):
    """
    Node for conputing DGCG filters.
    
    Variables:
    ----
    nb_freq_band: nb band of filter for each channel
    low_freq: first filter (Hz)
    hight_freq = last filter (Hz)
    tau_level: (s) decay for level estimation
    smooth_time:  (s)  smothin windows  for level estimation
    level_step: step (dB) for precomputing hpaf filters. The smaller = finer garin but high memory for GPU
    level_max: max level (dB) for level
    calibration: equivalent dbSPL for 0dBFs. 0dBFs is one sinus of amplitude 1
                    default is 93.979400086720375 dBSPL is equivalent when amplitude is directly the pressure
                    so 0dbSPL is 2e-5Pa
    loss_weigth: a list (size nb_channel) of list (size nb loss measurement) of pair (freq, loss_db)
        Example 1 channel: [ [(50,0.), (1000., -35), (2000., -40.), (6000., -35.), (25000,0.),]]
    
    
    """
    def _configure(self, nb_freq_band=16, low_freq = 100., hight_freq = 15000.,
                tau_level = 0.005, smooth_time = 0.0005, level_step =1., level_max = 120.,
                calibration =  93.979400086720375,
                loss_weigth = [ [(50,0.), (1000., -35), (2000., -40.), (6000., -35.), (25000,0.),]],
                chunksize=512, backward_chunksize=1024, debug_mode=False, **kargs):
        """
        Parameters for configure
        -------
        coefficients: per channel sos filter coefficient shape (nb_channel, nb_section, 6)
        
        """
        CL_BaseProcessingNode._configure(self, **kargs)

        self.nb_freq_band = nb_freq_band
        self.low_freq = low_freq
        self.hight_freq = hight_freq
        self.tau_level = tau_level
        self.smooth_time = smooth_time
        self.level_step = level_step
        self.level_max = level_max
        self.calibration = calibration
        self.loss_weigth = loss_weigth
        self.chunksize = chunksize
        self.backward_chunksize = backward_chunksize
        
        self.debug_mode = debug_mode
        

    def after_input_connect(self, inputname):
        CL_BaseProcessingNode.after_input_connect(self, inputname)

        self.nb_channel = self.input.params['shape'][1]
        self.sample_rate = self.input.params['sample_rate']
        self.dtype = self.input.params['dtype']
        
        
        for k in ['sample_rate', 'dtype', 'shape']:
            self.outputs['signals'].spec[k] = self.input.params[k]
        
        self.total_channel = self.nb_freq_band*self.nb_channel
        
        if self.debug_mode:
            steps = ['pgc1', 'levels', 'hpaf', 'pgc2']
            for step in steps:
                self._output_specs[step] = dict(streamtype = 'signals', shape=(-1,self.total_channel),
                        sample_rate=self.sample_rate)
            self.outputs = {name:pyacq.OutputStream(spec=spec, node=self, name=name) for name, spec in self._output_specs.items()}
    
    
    def make_filters(self):
        
        assert len(self.loss_weigth) == self.nb_channel, 'The nb_channel given in loss_weight is not nb_channel {} {}'.format(len(self.loss_weigth), self.nb_channel)
        
        
        self.freqs = erbspace(self.low_freq,self.hight_freq, self.nb_freq_band)
        
        # compute losses at ERB freq
        self.losses = [ ]
        for c in range(self.nb_channel):
            lw = self.loss_weigth[c]
            lw = [(0,0)]+lw + [(self.sample_rate/2, 0.)]
            loss_freq, loss_db = np.array(lw).T
            interp = scipy.interpolate.interp1d(loss_freq, loss_db)
            self.losses.append(interp(self.freqs))
        self.losses = np.array(self.losses)
        
        # pgc filter coefficient
        b1 = 1.81
        c1 = -2.96
        #~ b1 = 1.019
        #~ c1 = 1. 
        b2 = 2.17
        c2 = 2.2
        
        p0=2
        p1=1.7818*(1-0.0791*b2)*(1-0.1655*abs(c2))
        p2=0.5689*(1-0.1620*b2)*(1-0.0857*abs(c2))
        p3=0.2523*(1-0.0244*b2)*(1+0.0574*abs(c2))
        p4=1.0724

        pgcfilters_1ch = loggammachirp(self.freqs, self.sample_rate, b=b1, c=c1).astype(self.dtype)
        
        #noramlize PGC to 0 db at maximum 
        for f, freq in enumerate(self.freqs):
            w, h = sosfreqz(pgcfilters_1ch[f,:,:], worN =2**16,)
            gain = np.max(np.abs(h))
            pgcfilters_1ch[f,0, :3] /= gain
        
        self.coefficients_pgc = np.concatenate([pgcfilters_1ch]*self.nb_channel, axis =0)

        # Construct hpaf filters : pre compute for all sound levels for each freq
        self.levels = np.arange(0, self.level_max,self.level_step)
        nlevel = self.levels.size
        
        # construct hpaf depending on loss
        self.coefficients_hpaf = np.zeros((self.nb_channel*self.nb_freq_band, len(self.levels), 4, 6), dtype = self.dtype)
        for c in range(self.nb_channel):
            w = -self.losses[c,:]/30.
            frat1r = -w/65/2.
            frat0r = 1+w/2.
            for l, level in enumerate(self.levels):
                frat = frat0r + frat1r*level
                freqs2 = self.freqs*frat
                self.coefficients_hpaf[c*self.nb_freq_band:(c+1)*self.nb_freq_band , l, : , : ] = asymmetric_compensation_coeffs(freqs2, self.sample_rate, b2,c2,p0,p1,p2,p3,p4)
        
        NFFT = 2**16
        
        #noramlize for highest level
        for c in range(self.nb_channel):
            for f, freq in enumerate(self.freqs):
                #~ filter = np.concatenate([pgcfilters_1ch[f,:,:], self.coefficients_hpaf[c*self.nb_freq_band+f , -1, : , : ], ], axis = 0)
                filter = np.concatenate([pgcfilters_1ch[f,:,:], self.coefficients_hpaf[c*self.nb_freq_band+f , -1, : , : ],pgcfilters_1ch[f,:,:] ], axis = 0)
                w, h = sosfreqz(filter, worN =NFFT)
                gain = np.max(np.abs(h))
                self.coefficients_hpaf[c*self.nb_freq_band+f , :, 0 , :3 ] /= gain
        
        # compensate final gain for sum
        all = np.zeros(NFFT)
        for f, freq in enumerate(self.freqs):
            all_filter = np.concatenate([self.coefficients_pgc[f,:,:],self.coefficients_hpaf[f,-1,:,:], self.coefficients_pgc[f,:,:]], axis = 0)
            w, h = sosfreqz(all_filter,worN = NFFT)
            all += np.abs(h) 
        
        # check this
        fft_freqs = w/np.pi*(self.sample_rate/2.)
        all = all[(fft_freqs>self.freqs[0]) & (fft_freqs<self.freqs[-1])]
        self.dbgain_final = -np.mean(20*np.log10(all))
        self.gain_final = 10**(self.dbgain_final/20.)
        
        print('dbgain_final', self.dbgain_final)
        
        
        # make decays per band
        samedecay = np.exp(-2./self.tau_level/self.sample_rate)
        # same decay for all band
        self.expdecays = np.ones((self.nb_freq_band), dtype = self.dtype) * samedecay
        # one decay per band (for testing)
        #~ self.expdecays=  np.exp(-2.*self.freqs/nbcycle_decay/self.sample_rate).astype(self.dtype)

    
    def initlalize_cl(self):
        """
        
        Steps:
          * pgc1:
          * levels
          * hpaf: 
          * pgc2: 
        
        """
        self.make_filters()
        
        
        self.dtype = self.input.params['dtype']
        assert self.dtype == np.dtype('float32')
        #~ assert self.coefficients.shape[0]==self.nb_channel, 'wrong coefficients.shape'
        
        
        self.out_hpaf_ringbuffer = pyacq.RingBuffer(shape=(self.backward_chunksize, self.total_channel), 
                                    dtype=self.dtype, double=True, fill=0., axisorder=(1,0))
        
        #host arrays
        self.in_pgc1 = np.zeros((self.total_channel, self.chunksize), dtype= self.dtype)
        self.out_pgc1 = np.zeros((self.total_channel, self.chunksize), dtype= self.dtype)
        self.zi_pgc1 = np.zeros((self.total_channel, self.coefficients_pgc.shape[1], 2), dtype= self.dtype)
        
        smooth_sample = int(self.sample_rate*self.smooth_time)
        smooth_sample = 1
        self.previouslevel = np.zeros((self.total_channel, smooth_sample), dtype = self.dtype)
        self.out_levels = np.zeros((self.total_channel, self.chunksize), dtype= self.dtype)
        
        self.out_hpaf = np.zeros((self.total_channel, self.chunksize), dtype= self.dtype)
        self.zi_hpaf = np.zeros((self.total_channel, self.coefficients_hpaf.shape[2], 2), dtype= self.dtype)
        
        self.in_pgc2 = np.zeros((self.total_channel, self.backward_chunksize), dtype= self.dtype)
        self.out_pgc2 = np.zeros((self.total_channel, self.backward_chunksize), dtype= self.dtype)
        self.zi_pgc2 = np.zeros((self.total_channel, self.coefficients_pgc.shape[1], 2), dtype= self.dtype)
        #set initial state to minimize initiale state
        #~ for chan in range(self.total_channel):
            #~ for section in range(self.coefficients_pgc.shape[1]):
                #~ coeff = self.coefficients_pgc[chan, section, :]
                #~ b, a = coeff[:3], coeff[3:]
                #~ zi = scipy.signal.lfilter_zi(b, a)
                #~ self.zi_pgc2[chan, section, :] = zi[::-1]
                
        
        
        #GPU buffers
        self.coefficients_pgc_cl = pyopencl.Buffer(self.ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=self.coefficients_pgc)
        
        self.in_pgc1_cl = pyopencl.Buffer(self.ctx, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf=self.in_pgc1)
        self.out_pgc1_cl = pyopencl.Buffer(self.ctx, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf=self.out_pgc1)
        self.zi_pgc1_cl = pyopencl.Buffer(self.ctx, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf=self.zi_pgc1)
        
        self.expdecays_cl = pyopencl.Buffer(self.ctx, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf=self.expdecays)
        self.previouslevel_cl = pyopencl.Buffer(self.ctx, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf=self.previouslevel)
        self.out_levels_cl = pyopencl.Buffer(self.ctx, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf=self.out_levels)
        
        self.out_hpaf_cl = pyopencl.Buffer(self.ctx, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf=self.out_hpaf)
        self.zi_hpaf_cl = pyopencl.Buffer(self.ctx, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf=self.zi_hpaf)
        self.coefficients_hpaf_cl = pyopencl.Buffer(self.ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=self.coefficients_hpaf)
        
        self.in_pgc2_cl = pyopencl.Buffer(self.ctx, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf=self.in_pgc2)
        self.out_pgc2_cl = pyopencl.Buffer(self.ctx, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf=self.out_pgc2)
        self.zi_pgc2_cl = pyopencl.Buffer(self.ctx, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf=self.zi_pgc2)
        
        
        # compialtion
        kernel = cl_code%dict(forward_chunksize=self.chunksize, backward_chunksize=self.backward_chunksize,
                                            nb_channel=self.total_channel, max_chunksize=max(self.chunksize, self.backward_chunksize),
                                            nb_level=len(self.levels),
                                            levelavgsize=smooth_sample,
                                            calibration=self.calibration,
                                            levelstep=self.level_step,
                                            levelmax=self.level_max,
                                                            )
        prg = pyopencl.Program(self.ctx, kernel)
        self.opencl_prg = prg.build(options='-cl-mad-enable')
        
        
    
    def proccesing_func(self, pos, data):
        
        # split each channels in nb_freq_band
        for chan in range(self.nb_channel):
            self.in_pgc1[chan*self.nb_freq_band:(chan+1)*self.nb_freq_band, :] = data[:, chan]
            
        pyopencl.enqueue_copy(self.queue,  self.in_pgc1_cl, self.in_pgc1)
        
        #pgc1
        nb_section = self.coefficients_pgc.shape[1]
        global_size = (self.total_channel, nb_section,)
        local_size = (1, nb_section, )
        event = self.opencl_prg.forward_filter(self.queue, global_size, local_size,
                                self.in_pgc1_cl, self.out_pgc1_cl, self.coefficients_pgc_cl, self.zi_pgc1_cl, np.int32(nb_section))
        event.wait()
        if self.debug_mode:
            ev = pyopencl.enqueue_copy(self.queue,  self.out_pgc1, self.out_pgc1_cl)
            self.outputs['pgc1'].send(self.out_pgc1.T, index=pos)
        
        
        #levels
        chunkcount = pos // self.chunksize
        global_size = (self.total_channel, )
        local_size = (1,  )
        event = self.opencl_prg.estimate_leveldb(self.queue, global_size, local_size,
                                self.out_pgc1_cl, self.out_levels_cl, self.previouslevel_cl, self.expdecays_cl, np.int64(chunkcount))  #TODO change chnkcount by pos directly
        event.wait()
        if self.debug_mode:
            pyopencl.enqueue_copy(self.queue,  self.out_levels, self.out_levels_cl)
            self.outputs['levels'].send(self.out_levels.T, index=pos)
        
        
        # hpaf
        nb_section = self.coefficients_hpaf.shape[2]
        global_size = (self.total_channel, nb_section,)
        local_size = (1, nb_section, )
        event = self.opencl_prg.dynamic_sos_filter(self.queue, global_size, local_size,
                                self.out_pgc1_cl, self.out_levels_cl, self.out_hpaf_cl, self.coefficients_hpaf_cl,
                                self.zi_hpaf_cl, np.int32(nb_section))
        event.wait()
        
        
        pyopencl.enqueue_copy(self.queue,  self.out_hpaf, self.out_hpaf_cl)
        if self.debug_mode:
            self.outputs['hpaf'].send(self.out_hpaf.T, index=pos)
        
        # get out_hpaf in host and put it in ring buffer
        self.out_hpaf_ringbuffer.new_chunk(self.out_hpaf.T, index=pos)
        # get the (longer) backward buffer
        in_pgc2 = self.out_hpaf_ringbuffer.get_data(pos-self.backward_chunksize, pos)
        self.in_pgc2[:] = in_pgc2.T
        # and send it baack to device
        pyopencl.enqueue_copy(self.queue,  self.in_pgc2_cl, self.in_pgc2)
        
        pos2 = pos - self.backward_chunksize + self.chunksize
        #~ print('ici', 'pos', pos,  'pos2', pos2, in_pgc2.shape)
        
        if pos2<=0:
            return None, None
        
        
        
        # pgc2
        #TODO: do this in CL
        pyopencl.enqueue_copy(self.queue,  self.zi_pgc2_cl, self.zi_pgc2)
        
        #TODO: make backward chunksize multiple of chunksize and do not copy to RAM
        # but make a ring of chunks
        
        nb_section = self.coefficients_pgc.shape[1]
        global_size = (self.total_channel, nb_section,)
        local_size = (1, nb_section, )
        event = self.opencl_prg.backward_filter(self.queue, global_size, local_size,
                                self.in_pgc2_cl, self.out_pgc2_cl, self.coefficients_pgc_cl, self.zi_pgc2_cl, np.int32(nb_section))
        event.wait()
        pyopencl.enqueue_copy(self.queue,  self.out_pgc2, self.out_pgc2_cl)
        out_pgc2_short = self.out_pgc2[:, :self.chunksize]
        
        if pos2<self.chunksize:
            out_pgc2_short = out_pgc2_short[:, :pos2]
            out_buffer = np.empty((self.nb_channel, pos2), dtype=self.dtype)
        else:
            out_buffer = np.empty((self.nb_channel, self.chunksize), dtype=self.dtype)
        
        if self.debug_mode:
            #~ print('pos2', pos2, self.out_pgc2.shape, out_pgc2_short.shape)
            self.outputs['pgc2'].send(out_pgc2_short.T, index=pos2)
        
        
        # sum by channel block
        
        for chan in range(self.nb_channel):
            out_buffer[chan, :] = np.sum(out_pgc2_short[chan*self.nb_freq_band:(chan+1)*self.nb_freq_band, :], axis = 0)
        
        #gain
        out_buffer *= self.gain_final
        
        return pos2, out_buffer.T

