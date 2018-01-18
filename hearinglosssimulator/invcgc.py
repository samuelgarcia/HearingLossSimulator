import os
import time
import concurrent.futures

import numpy as np
#import scipy.signal
import scipy.interpolate


# this make readthedocs work
try:
    import pyopencl
    mf = pyopencl.mem_flags
    HAS_PYOPENCL = True
except ImportError:
    HAS_PYOPENCL = False

from .filterfactory import (erbspace)
from .cgcfilter import make_cgc_filter
from .common import BaseMultiBand




# read opencl source code
cl_code_filename = os.path.join(os.path.dirname(__file__), 'cl_processing.cl')
with open(cl_code_filename, mode='r') as f:
    cl_code = f.read()



class InvCGC(BaseMultiBand):
    """
    Class for computing the InvCGC filter bank.
    
    """
    _attr_to_save=['total_channel', 'freqs', 'passive_gain', 
                    'coefficients_pgc', 'coefficients_hpaf', 'band_overlap_gain', 
                    'levels', 'expdecays']    
    
    def make_filters(self):
        print('InvCGC.make_filters')
        self.total_channel = self.nb_freq_band*self.nb_channel
        self.freqs = erbspace(self.low_freq,self.high_freq, self.nb_freq_band)
        
        channels = ('left', 'right')[:self.nb_channel]
        # interpolate compression_degree and passive_loss
        compresison_degree_all = {}
        passive_loss_db_all = {}
        self.passive_gain = []
        for c, chan in enumerate(channels):
            cg = self.loss_params[chan]['compression_degree']
            interp = scipy.interpolate.interp1d(self.loss_params[chan]['freqs'], cg, bounds_error=False, fill_value=(cg[0], cg[-1]))
            compresison_degree_all[chan] = interp(self.freqs)

            pl = self.loss_params[chan]['passive_loss_db']
            interp = scipy.interpolate.interp1d(self.loss_params[chan]['freqs'], pl, bounds_error=False, fill_value=(pl[0], pl[-1]))
            passive_loss_db_all[chan] = interp(self.freqs)
            
            self.passive_gain.extend(10**(-passive_loss_db_all[chan]/20.))
            
        #~ print(self.freqs)
        #~ print(compresison_degree_all)
        #~ print(passive_loss_db_all)
        
        self.passive_gain = np.array(self.passive_gain, dtype=self.dtype)[:, None]
        #~ print(self.passive_gain)
        #~ exit()
        
        
        
        #TODO : this is for debug only
        #~ compression_degree = [0.] * len(self.freqs)
        
        self.coefficients_pgc = [None]*self.nb_channel
        self.coefficients_hpaf = [None]*self.nb_channel
        for c, chan in enumerate(channels):
            self.coefficients_pgc[c], self.coefficients_hpaf[c], levels, band_overlap_gain = make_cgc_filter(self.freqs, compresison_degree_all[chan],
                                        self.level_max, self.level_step, self.sample_rate, dtype=self.dtype)
            print(chan, 'band_overlap_gain', band_overlap_gain)
        self.coefficients_pgc = np.concatenate(self.coefficients_pgc, axis =0)
        self.coefficients_hpaf = np.concatenate(self.coefficients_hpaf, axis =0)
        
        self.band_overlap_gain = band_overlap_gain
        self.levels = levels
        
        
        # make decays per band
        samedecay = np.exp(-2./self.tau_level/self.sample_rate)
        # same decay for all band
        self.expdecays = np.ones((self.total_channel), dtype = self.dtype) * samedecay
        # one decay per band (for testing)
        #~ self.expdecays=  np.exp(-2.*self.freqs/nbcycle_decay/self.sample_rate).astype(self.dtype)
    
    def initlalize_cl(self):
        assert self.dtype == np.dtype('float32')
        
        #host arrays
        self.in_channel = np.zeros((self.chunksize, self.nb_channel), dtype= self.dtype)
        
        self.in_pgc1 = np.zeros((self.total_channel, self.chunksize), dtype= self.dtype)
        self.out_pgc1 = np.zeros((self.total_channel, self.chunksize), dtype= self.dtype)
        self.zi_pgc1 = np.zeros((self.total_channel, self.coefficients_pgc.shape[1], 2), dtype= self.dtype)
        
        #~ smooth_sample = int(self.sample_rate*self.smooth_time)
        #~ smooth_sample = 1
        #~ self.previouslevel = np.zeros((self.total_channel, smooth_sample), dtype = self.dtype)
        self.previouslevel = np.zeros((self.total_channel), dtype = self.dtype)
        self.out_levels = np.zeros((self.total_channel, self.chunksize), dtype= self.dtype)
        
        self.out_hpaf = np.zeros((self.total_channel, self.chunksize), dtype= self.dtype)
        self.zi_hpaf = np.zeros((self.total_channel, self.coefficients_hpaf.shape[2], 2), dtype= self.dtype)
        
        self.out_pgc2 = np.zeros((self.total_channel, self.chunksize), dtype= self.dtype)
        self.zi_pgc2 = np.zeros((self.total_channel, self.coefficients_pgc.shape[1], 2), dtype= self.dtype)
        
        self.out_passive = np.zeros((self.total_channel, self.chunksize), dtype= self.dtype)
        
        self.out_channel = np.zeros((self.chunksize, self.nb_channel), dtype= self.dtype)
        
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
        
        self.passive_gain_cl = pyopencl.Buffer(self.ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=self.passive_gain.flatten().copy())
        self.out_passive_cl = pyopencl.Buffer(self.ctx, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf=self.out_passive)
        
        self.out_channel_cl = pyopencl.Buffer(self.ctx, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf=self.out_channel)
        
        # compialtion
        # dans opencl define levelavgsize %(levelavgsize)d
        
        kernel = cl_code%dict(chunksize=self.chunksize,
                                            nb_level=len(self.levels),
                                            #~ levelavgsize=smooth_sample,
                                            calibration=self.calibration,
                                            levelstep=self.level_step,
                                            levelmax=self.level_max,
                                            )
        prg = pyopencl.Program(self.ctx, kernel)
        self.opencl_prg = prg.build(options='-cl-mad-enable')
        
        
        self.kern_transpose_and_repeat_channel = getattr(self.opencl_prg, 'transpose_and_repeat_channel')
        self.kern_sos_filter = getattr(self.opencl_prg, 'sos_filter')
        #~ self.kern_forward_filter = getattr(self.opencl_prg, 'forward_filter')
        self.kern_estimate_leveldb = getattr(self.opencl_prg, 'estimate_leveldb')
        self.kern_dynamic_sos_filter = getattr(self.opencl_prg, 'dynamic_sos_filter')
        self.kern_reset_zis = getattr(self.opencl_prg, 'reset_zis')
        #~ self.kern_backward_filter = getattr(self.opencl_prg, 'backward_filter')
        self.kern_bychannel_gain = getattr(self.opencl_prg, 'bychannel_gain')
        self.kern_sum_channel_and_gain = getattr(self.opencl_prg, 'sum_channel_and_gain')
        


    def proccesing_func(self, pos, data, asynch=False):
        
        assert data.shape == (self.chunksize, self.nb_channel), 'data.shape error {} {}'.format(data.shape, (self.chunksize, self.nb_channel))
        
        returns = {}
        
        if self.bypass:
            assert not asynch
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
        event = self.kern_transpose_and_repeat_channel(self.queue, global_size, local_size,
                                self.in_channel_cl, self.in_pgc1_cl, np.int32(self.nb_channel), np.int32(self.nb_freq_band))
        #~ event.wait()
        
        
        #pgc1
        nb_section = self.coefficients_pgc.shape[1]
        global_size = (self.total_channel, nb_section,)
        local_size = (1, nb_section, )
        #~ event = self.kern_forward_filter(self.queue, global_size, local_size,
                                #~ self.in_pgc1_cl, self.out_pgc1_cl, self.coefficients_pgc_cl, self.zi_pgc1_cl,
                                #~ np.int32(nb_section))
        event = self.kern_sos_filter(self.queue, global_size, local_size,
                                self.in_pgc1_cl, self.out_pgc1_cl, self.coefficients_pgc_cl, self.zi_pgc1_cl,
                                np.int32(1), np.int32(nb_section))
        #~ event.wait()
        
        
        #levels
        
        global_size = (self.total_channel, )
        local_size = (1,  )
        event = self.kern_estimate_leveldb(self.queue, global_size, local_size,
                                self.out_pgc1_cl, self.out_levels_cl, self.previouslevel_cl, self.expdecays_cl, np.int64(chunkcount))  #TODO change chnkcount by pos directly
        #~ event.wait()
        
        # hpaf
        nb_section = self.coefficients_hpaf.shape[2]
        global_size = (self.total_channel, nb_section,)
        local_size = (1, nb_section, )
        event = self.kern_dynamic_sos_filter(self.queue, global_size, local_size,
                                self.out_pgc1_cl, self.out_levels_cl, self.outs_hpaf_cl[ring_pos], self.coefficients_hpaf_cl,
                                self.zi_hpaf_cl, np.int32(nb_section))
        #~ event.wait()
        
        pos2 = pos - self.backward_chunksize + self.chunksize
        #~ print('ici', 'pos', pos,  'pos2', pos2)
        #~ print('chunkcount', chunkcount, 'ring_pos', ring_pos)
        
        
        if pos2<=0:
            if not asynch:
                event.wait()
                returns['main_output'] = (None, None)
                return returns
            else:
                return FuturBuffer(None, None, None, None, event) 
            
        else:
        
            # pgc2
            event = self.kern_reset_zis(self.queue, (self.total_channel, ), (1, ), self.zi_pgc2_cl)
            #~ event.wait()

            nb_section = self.coefficients_pgc.shape[1]
            global_size = (self.total_channel, nb_section,)
            local_size = (1, nb_section, )
            for i in range(self.backward_ratio):
                rp = (chunkcount - i-1) % self.backward_ratio
                #~ event = self.kern_backward_filter(self.queue, global_size, local_size,
                                        #~ self.outs_hpaf_cl[rp], self.out_pgc2_cl, self.coefficients_pgc_cl, self.zi_pgc2_cl,
                                        #~ np.int32(nb_section))
                event = self.kern_sos_filter(self.queue, global_size, local_size,
                                        self.outs_hpaf_cl[rp], self.out_pgc2_cl, self.coefficients_pgc_cl, self.zi_pgc2_cl,
                                        np.int32(-1), np.int32(nb_section))
            
            # passive gain by band
            
            #NUMPY VERSION (is fasert but do not allow asynch=True)
            #~ event.wait()
            #~ pyopencl.enqueue_copy(self.queue,  self.out_pgc2, self.out_pgc2_cl)
            #~ self.out_passive = self.out_pgc2 * self.passive_gain # NUMPY VERSION

            #~ out_buffer = np.empty((self.nb_channel, self.chunksize), dtype=self.dtype)
            
            #~ # sum by channel block
            #~ for chan in range(self.nb_channel):
                #~ out_buffer[chan, :] = np.sum(self.out_passive[chan*self.nb_freq_band:(chan+1)*self.nb_freq_band, :], axis = 0)
            
            #compensate band_overlap_gain
            #~ out_buffer *= self.band_overlap_gain
            #~ out_buffer = out_buffer.T
            
            
            #OPENCL VERSION
            mwgs = self.ctx.devices[0].get_info(pyopencl.device_info.MAX_WORK_GROUP_SIZE)
            global_size = (self.total_channel, self.chunksize, )
            local_size = (1, min(mwgs, self.chunksize), )
            event = self.kern_bychannel_gain(self.queue, global_size, local_size,
                                        self.out_pgc2_cl, self.out_passive_cl, self.passive_gain_cl)
            
            global_size = (self.chunksize,)
            local_size = None
            event = self.kern_sum_channel_and_gain(self.queue, global_size, local_size,
                                    self.out_passive_cl, self.out_channel_cl, 
                                    np.int32(self.nb_freq_band), np.int32(self.nb_channel),
                                    np.float32(self.band_overlap_gain))
            
            out_buffer = np.empty((self.chunksize, self.nb_channel), dtype=self.dtype)
            
            if not asynch:
                event.wait()
                pyopencl.enqueue_copy(self.queue,  out_buffer, self.out_channel_cl)
                returns['main_output'] = (pos2, out_buffer)
                
            else:
                assert not self.debug_mode
                return FuturBuffer(pos2, self.queue, out_buffer, self.out_channel_cl, event)
        
        
        if self.debug_mode:
            ev = pyopencl.enqueue_copy(self.queue,  self.out_pgc1, self.out_pgc1_cl)
            returns['pgc1'] = (pos, self.out_pgc1.T)

            pyopencl.enqueue_copy(self.queue,  self.out_levels, self.out_levels_cl)
            returns['levels'] = (pos, self.out_levels.T)

            pyopencl.enqueue_copy(self.queue,  self.out_hpaf, self.outs_hpaf_cl[ring_pos])
            returns['hpaf'] = (pos, self.out_hpaf.T)

            if pos2<=0:
                returns['pgc2'] = (None, None)
                returns['passive'] = (None, None)
            
            else:
                pyopencl.enqueue_copy(self.queue,  self.out_pgc2, self.out_pgc2_cl)
                returns['pgc2'] = (pos2, self.out_pgc2.T)

                pyopencl.enqueue_copy(self.queue,  self.out_passive, self.out_passive_cl)
                returns['passive'] = (pos2, self.out_passive.T)

        
        return returns


class FuturBuffer(concurrent.futures.Future):
    def __init__(self, pos2, queue, out_buffer,  out_channel_cl, cl_event):
        concurrent.futures.Future.__init__(self)
        self.pos2 = pos2
        self.queue = queue
        self.out_buffer = out_buffer
        self.out_channel_cl = out_channel_cl
        self.cl_event = cl_event
    
    def cancel(self):
        return False

    def result(self, timeout=None):
        self.cl_event.wait()
        returns = {}
        
        if self.pos2 is None:
            returns['main_output'] = (None, None)
        else:
            pyopencl.enqueue_copy(self.queue,  self.out_buffer, self.out_channel_cl)
            returns['main_output'] = (self.pos2, self.out_buffer)
            
        return returns
