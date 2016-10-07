import os
import time

import numpy as np
import scipy.signal
import scipy.interpolate

from pyqtgraph.Qt import QtCore
import pyqtgraph as pg
#~ from pyqtgraph.util.mutex import Mutex

import pyopencl
mf = pyopencl.mem_flags


import pyacq

#~ from .filterfactory import (gammatone, asymmetric_compensation_coeffs, loggammachirp, erbspace)
#~ from .tools import sosfreqz
from .filterfactory import (erbspace)
from .cgcfilter import make_cgc_filter


"""


"""


# read opencl source code
cl_code_filename = os.path.join(os.path.dirname(__file__), 'cl_processing.cl')
with open(cl_code_filename, mode='r') as f:
    cl_code = f.read()



class InvCGC:
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
    def __init__(self, nb_channel=1, sample_rate=44100., dtype='float32',
                apply_configuration_at_init=True, **params):

        self.nb_channel = nb_channel
        self.sample_rate = sample_rate
        self.dtype = np.dtype(dtype)

        self.configure(**params)
        
        if apply_configuration_at_init:
            self.make_filters()
            self.create_opencl_context()
            self.initlalize_cl()
    
    def create_opencl_context(self, gpu_platform_index=None, gpu_device_index=None):
        self.gpu_platform_index = gpu_platform_index
        self.gpu_device_index = gpu_device_index
        
        if self.gpu_platform_index is None:
            self.ctx = pyopencl.create_some_context()
        else:
            self.devices =  [pyopencl.get_platforms()[self.gpu_platform_index].get_devices()[self.gpu_device_index] ]
            self.ctx = pyopencl.Context(self.devices)        
        self.queue = pyopencl.CommandQueue(self.ctx)
        print(self.ctx)
    
    
    def configure(self, nb_freq_band=16, low_freq = 100., hight_freq = 15000.,
                tau_level = 0.005, smooth_time = 0.0005, level_step =1., level_max = 120.,
                calibration =  93.979400086720375,
                loss_params = {},
                #~ loss_weigth = [ [(50,0.), (1000., -35), (2000., -40.), (6000., -35.), (25000,0.),]],
                chunksize=512, backward_chunksize=1024, debug_mode=False, bypass=False, **kargs):
        
        
        self.nb_freq_band = nb_freq_band
        self.low_freq = low_freq
        self.hight_freq = hight_freq
        self.tau_level = tau_level
        self.smooth_time = smooth_time
        self.level_step = level_step
        self.level_max = level_max
        self.calibration = calibration
        #~ self.loss_weigth = loss_weigth
        self.loss_params = loss_params
        self.chunksize = chunksize
        self.backward_chunksize = backward_chunksize
        
        assert self.backward_chunksize%self.chunksize==0, 'backward_chunksize must multiple of chunksize'
        self.backward_ratio = self.backward_chunksize//self.chunksize
        
        self.bypass = bypass
        self.debug_mode = debug_mode
    
    
    def make_filters(self):
        self.total_channel = self.nb_freq_band*self.nb_channel
        self.freqs = erbspace(self.low_freq,self.hight_freq, self.nb_freq_band)
        
        channels = ('left', 'right')[:self.nb_channel]
        # interpolate compression_degree and passive_loss
        compresison_degree_all = {}
        passive_loss_all = {}
        for c, chan in enumerate(channels):
            cg = self.loss_params[chan]['compression_degree']
            interp = scipy.interpolate.interp1d(self.loss_params[chan]['freqs'], cg, bounds_error=False, fill_value=(cg[0], cg[-1]))
            compresison_degree_all[chan] = interp(self.freqs)

            pl = self.loss_params[chan]['compression_degree']
            interp = scipy.interpolate.interp1d(self.loss_params[chan]['freqs'], pl, bounds_error=False, fill_value=(pl[0], pl[-1]))
            passive_loss_all[chan] = interp(self.freqs)
        print(self.freqs)
        print(compresison_degree_all)
        print(passive_loss_all)
        
        #TODO : this is for debug only
        compression_degree = [0.] * len(self.freqs)
        
        self.coefficients_pgc = [None]*self.nb_channel
        self.coefficients_hpaf = [None]*self.nb_channel
        for c, chan in enumerate(channels):
            self.coefficients_pgc[c], self.coefficients_hpaf[c], levels, band_overlap_gain = make_cgc_filter(self.freqs, compresison_degree_all[chan],
                                        self.level_max, self.level_step, self.sample_rate, dtype=self.dtype)
        self.coefficients_pgc = np.concatenate(self.coefficients_pgc, axis =0)
        self.coefficients_hpaf = np.concatenate(self.coefficients_hpaf, axis =0)
        
        self.band_overlap_gain = band_overlap_gain
        self.levels = levels
        
        
        # make decays per band
        samedecay = np.exp(-2./self.tau_level/self.sample_rate)
        # same decay for all band
        self.expdecays = np.ones((self.nb_freq_band), dtype = self.dtype) * samedecay
        # one decay per band (for testing)
        #~ self.expdecays=  np.exp(-2.*self.freqs/nbcycle_decay/self.sample_rate).astype(self.dtype)

        
    """
    def make_filters_old(self):
        
        if len(self.loss_weigth) ==1 and self.nb_channel!=1:
            self.loss_weigth = self.loss_weigth*self.nb_channel
        
        assert len(self.loss_weigth) == self.nb_channel, 'The nb_channel given in loss_weight is not nb_channel {} {}'.format(len(self.loss_weigth), self.nb_channel)
        
        self.total_channel = self.nb_freq_band*self.nb_channel
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
        #TODO remove first and last band global gain!!!!
         
        self.band_overlap_gain_db = -np.mean(20*np.log10(all))
        self.band_overlap_gain = 10**(self.band_overlap_gain_db/20.)
        
        if self.debug_mode:
            print('band_overlap_gain_db', self.band_overlap_gain_db)
        
        
        # make decays per band
        samedecay = np.exp(-2./self.tau_level/self.sample_rate)
        # same decay for all band
        self.expdecays = np.ones((self.nb_freq_band), dtype = self.dtype) * samedecay
        # one decay per band (for testing)
    """

    def initlalize_cl(self):

        #~ if not hasattr(self, 'coefficients_pgc'):
            # first call
            #~ self.make_filters()
        
        #~ self.dtype = self.input.params['dtype']
        assert self.dtype == np.dtype('float32')
        
        #host arrays
        self.in_channel = np.zeros((self.chunksize, self.nb_channel), dtype= self.dtype)
        
        self.in_pgc1 = np.zeros((self.total_channel, self.chunksize), dtype= self.dtype)
        self.out_pgc1 = np.zeros((self.total_channel, self.chunksize), dtype= self.dtype)
        self.zi_pgc1 = np.zeros((self.total_channel, self.coefficients_pgc.shape[1], 2), dtype= self.dtype)
        
        smooth_sample = int(self.sample_rate*self.smooth_time)
        smooth_sample = 1
        self.previouslevel = np.zeros((self.total_channel, smooth_sample), dtype = self.dtype)
        self.out_levels = np.zeros((self.total_channel, self.chunksize), dtype= self.dtype)
        
        self.out_hpaf = np.zeros((self.total_channel, self.chunksize), dtype= self.dtype)
        self.zi_hpaf = np.zeros((self.total_channel, self.coefficients_hpaf.shape[2], 2), dtype= self.dtype)
        
        self.out_pgc2 = np.zeros((self.total_channel, self.chunksize), dtype= self.dtype)
        self.zi_pgc2 = np.zeros((self.total_channel, self.coefficients_pgc.shape[1], 2), dtype= self.dtype)
        #set initial state to minimize initiale state
        #~ for chan in range(self.total_channel):
            #~ for section in range(self.coefficients_pgc.shape[1]):
                #~ coeff = self.coefficients_pgc[chan, section, :]
                #~ b, a = coeff[:3], coeff[3:]
                #~ zi = scipy.signal.lfilter_zi(b, a)
                #~ self.zi_pgc2[chan, section, :] = zi[::-1]
                
        
        
        #GPU buffers
        self.in_channel_cl = pyopencl.Buffer(self.ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=self.in_channel)
        
        self.coefficients_pgc_cl = pyopencl.Buffer(self.ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=self.coefficients_pgc)
        
        self.in_pgc1_cl = pyopencl.Buffer(self.ctx, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf=self.in_pgc1)
        self.out_pgc1_cl = pyopencl.Buffer(self.ctx, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf=self.out_pgc1)
        self.zi_pgc1_cl = pyopencl.Buffer(self.ctx, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf=self.zi_pgc1)
        
        self.expdecays_cl = pyopencl.Buffer(self.ctx, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf=self.expdecays)
        self.previouslevel_cl = pyopencl.Buffer(self.ctx, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf=self.previouslevel)
        self.out_levels_cl = pyopencl.Buffer(self.ctx, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf=self.out_levels)
        
        self.outs_hpaf_cl = [pyopencl.Buffer(self.ctx, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf=self.out_hpaf) for _ in range(self.backward_ratio) ]
        
        self.zi_hpaf_cl = pyopencl.Buffer(self.ctx, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf=self.zi_hpaf)
        self.coefficients_hpaf_cl = pyopencl.Buffer(self.ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=self.coefficients_hpaf)
        
        self.out_pgc2_cl = pyopencl.Buffer(self.ctx, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf=self.out_pgc2)
        self.zi_pgc2_cl = pyopencl.Buffer(self.ctx, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf=self.zi_pgc2)
        
        
        # compialtion
        
        kernel = cl_code%dict(chunksize=self.chunksize,
                                            nb_level=len(self.levels),
                                            levelavgsize=smooth_sample,
                                            calibration=self.calibration,
                                            levelstep=self.level_step,
                                            levelmax=self.level_max,
                                            )
        prg = pyopencl.Program(self.ctx, kernel)
        self.opencl_prg = prg.build(options='-cl-mad-enable')

    def set_bypass(self, bypass):
        self.bypass = bypass

    def proccesing_func(self, pos, data):
        
        assert data.shape == (self.chunksize, self.nb_channel), 'data.shape error {} {}'.format(data.shape, (self.chunksize, self.nb_channel))
        
        returns = {}
        
        if self.bypass:
            # TODO make same latency as proccessing
            assert not self.debug_mode, 'debug mode do not support bypass'
            
            returns['main_output'] = (pos, data)
            return returns
        
        
        
        chunkcount = pos // self.chunksize
        ring_pos = (chunkcount-1) % self.backward_ratio
        
        # repeat each channels in nb_freq_band
        #~ for chan in range(self.nb_channel): #this is the numpy version for comparison
            #~ self.in_pgc1[chan*self.nb_freq_band:(chan+1)*self.nb_freq_band, :] = data[:, chan]
        #~ pyopencl.enqueue_copy(self.queue,  self.in_pgc1_cl, self.in_pgc1)
        
        # This is the opencl version
        if not data.flags['C_CONTIGUOUS']:
            data = data.copy()
        pyopencl.enqueue_copy(self.queue,  self.in_channel_cl, data)
        global_size = (self.nb_freq_band, self.nb_channel)
        local_size = (self.nb_freq_band, 1,)
        event = self.opencl_prg.transpose_and_repeat_channel(self.queue, global_size, local_size,
                                self.in_channel_cl, self.in_pgc1_cl, np.int32(self.nb_channel), np.int32(self.nb_freq_band))
        event.wait()
        
        
        #pgc1
        nb_section = self.coefficients_pgc.shape[1]
        global_size = (self.total_channel, nb_section,)
        local_size = (1, nb_section, )
        event = self.opencl_prg.forward_filter(self.queue, global_size, local_size,
                                self.in_pgc1_cl, self.out_pgc1_cl, self.coefficients_pgc_cl, self.zi_pgc1_cl, np.int32(nb_section))
        event.wait()
        if self.debug_mode:
            ev = pyopencl.enqueue_copy(self.queue,  self.out_pgc1, self.out_pgc1_cl)
            #~ self.outputs['pgc1'].send(self.out_pgc1.T, index=pos)
            returns['pgc1'] = (pos, self.out_pgc1.T)
        
        
        #levels
        
        global_size = (self.total_channel, )
        local_size = (1,  )
        event = self.opencl_prg.estimate_leveldb(self.queue, global_size, local_size,
                                self.out_pgc1_cl, self.out_levels_cl, self.previouslevel_cl, self.expdecays_cl, np.int64(chunkcount))  #TODO change chnkcount by pos directly
        event.wait()
        if self.debug_mode:
            pyopencl.enqueue_copy(self.queue,  self.out_levels, self.out_levels_cl)
            #~ self.outputs['levels'].send(self.out_levels.T, index=pos)
            returns['levels'] = (pos, self.out_levels.T)
        
        
        # hpaf
        nb_section = self.coefficients_hpaf.shape[2]
        global_size = (self.total_channel, nb_section,)
        local_size = (1, nb_section, )
        event = self.opencl_prg.dynamic_sos_filter(self.queue, global_size, local_size,
                                self.out_pgc1_cl, self.out_levels_cl, self.outs_hpaf_cl[ring_pos], self.coefficients_hpaf_cl,
                                self.zi_hpaf_cl, np.int32(nb_section))
        event.wait()
        
        
        if self.debug_mode:
            pyopencl.enqueue_copy(self.queue,  self.out_hpaf, self.outs_hpaf_cl[ring_pos])
            #~ self.outputs['hpaf'].send(self.out_hpaf.T, index=pos)
            returns['hpaf'] = (pos, self.out_hpaf.T)
        
        pos2 = pos - self.backward_chunksize + self.chunksize
        #~ print('ici', 'pos', pos,  'pos2', pos2)
        #~ print('chunkcount', chunkcount, 'ring_pos', ring_pos)
        
        
        if pos2<=0:
            if self.debug_mode:
                returns['pgc2'] = (None, None)
            
            returns['main_output'] = (None, None)
            return returns
        
        else:
        
            # pgc2
            #~ pyopencl.enqueue_copy(self.queue,  self.zi_pgc2_cl, self.zi_pgc2) # this make this by copy
            event = self.opencl_prg.reset_zis(self.queue, (self.total_channel, ), (1, ), self.zi_pgc2_cl)
            event.wait()

            nb_section = self.coefficients_pgc.shape[1]
            global_size = (self.total_channel, nb_section,)
            local_size = (1, nb_section, )
            for i in range(self.backward_ratio):
                rp = (chunkcount - i-1) % self.backward_ratio
                event = self.opencl_prg.backward_filter(self.queue, global_size, local_size,
                                        self.outs_hpaf_cl[rp], self.out_pgc2_cl, self.coefficients_pgc_cl, self.zi_pgc2_cl, np.int32(nb_section))
                event.wait()
            
            
            pyopencl.enqueue_copy(self.queue,  self.out_pgc2, self.out_pgc2_cl)
            out_pgc2_short = self.out_pgc2

            if self.debug_mode:
                #~ self.outputs['pgc2'].send(self.out_pgc2.T, index=pos2)
                returns['pgc2'] = (pos2, self.out_pgc2.T)
            
            out_buffer = np.empty((self.nb_channel, self.chunksize), dtype=self.dtype)
            
            # sum by channel block
            
            for chan in range(self.nb_channel):
                out_buffer[chan, :] = np.sum(out_pgc2_short[chan*self.nb_freq_band:(chan+1)*self.nb_freq_band, :], axis = 0)
            
            #gain
            out_buffer *= self.band_overlap_gain
            
        

        returns['main_output'] = (pos2, out_buffer.T)
        return returns

