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




# read opencl source code
cl_code_filename = os.path.join(os.path.dirname(__file__), 'cl_processing.cl')
with open(cl_code_filename, mode='r') as f:
    cl_code = f.read()



class InvCGC:
    """
    Class for computing the InvCGC filter bank.
    
    """    
    def __init__(self, nb_channel=1, sample_rate=44100., dtype='float32',
                apply_configuration_at_init=True, **params):
        """
        Parameters:
            nb_channel (int) : 1 or 2 for mono/stereo
            sample_rate (float): sample rate in Hz
            dtype : internal dtype. Only tested with 'float32' at the moment.
            apply_configuration_at_init: if True use **params and configure at init
            **params: params for self.configure()
            
        """

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
    
    
    def configure(self, nb_freq_band=16, low_freq = 100., high_freq = 15000.,
                tau_level = 0.005, smooth_time = 0.0005, level_step =1., level_max = 120.,
                calibration =  93.979400086720375,
                loss_params = {},
                chunksize=512, backward_chunksize=1024, debug_mode=False, bypass=False):
        """
        Parameters:
            nb_freq_band (int): number of frequency band per channel
            low_freq (float): low freq limit
            high_freq (float): high freq limit
            tau_level (float): give inthe tau value in second for level estimation
            level_max (float) : maximum level for invers compression in dB.
                Over this level no more inv compression.
            level_step (float): level step in dB for precomputing HP-AF
            calibration (float): equivalent dbSPL for 0dBFs. 0dBFs is one sinus of amplitude 1
            loss_params (dict): dict with loss parameters. See below.
            chunksize (int): size in sample of each chunk of sound data
            backward_chunksize (int): size in sample of each backward chunk of sound data
                This must be  consider wisely because if too small, it lead to distortion in low frequency.
                If too high lead to much more comptation.
            bypass (bool): this bypass the processing. Convinience for the GUI.
            debug_mode (bool): False by default. If True each steps (pgc1, levels, hpaf, pgc2, 
                    passivei)s also copied to outputs.
                    
        **loss_params** is dict defined like this::
        
            loss_params = { 'left' : {'freqs' :  [125., 250., 500., 1000., 2000., 4000., 8000.],
                                    'compression_degree': [0., 0., 0., 0., 0., 0., 0.],
                                    'passive_loss_db' : [0., 0., 0., 0., -5., -10., -20.],
                                },
                                'right' : {'freqs' :  [125., 250., 500., 1000., 2000., 4000., 8000.],
                                    'compression_degree': [0., 0., 0., 0., 0., 0., 0.],
                                    'passive_loss_db' : [0., 0., 0., 0., -5., -10., -20.],
                                }
                            }
                        
        
        Where:
            * **freqs** are some frequencies. Others frequencies, for each band,  are interpolated,
                So size of freqs is  independant of `nb_freq_band`.
            * **compression_degree** is the healthyness of the compression for each band.
                1= no compression loss. 0=full compression loss.
            * **passive_loss_db** is a negative weigth in db for each band that represent
                the level independant loss in each band.
        
        In the previous example, all band have full compressive impairement and 2000. to 8000.
        Hz have a passive loss.
        
        """
        
        self.nb_freq_band = nb_freq_band
        self.low_freq = low_freq
        self.high_freq = high_freq
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
            
            self.passive_gain.extend(10**(passive_loss_db_all[chan]/20.))
            
        #~ print(self.freqs)
        #~ print(compresison_degree_all)
        #~ print(passive_loss_db_all)
        
        self.passive_gain = np.array(self.passive_gain, dtype=self.dtype)[:, None]
        #~ print(self.passive_gain)
        #~ exit()
        
        
        
        #TODO : this is for debug only
        compression_degree = [0.] * len(self.freqs)
        
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
        self.expdecays = np.ones((self.nb_freq_band), dtype = self.dtype) * samedecay
        # one decay per band (for testing)
        #~ self.expdecays=  np.exp(-2.*self.freqs/nbcycle_decay/self.sample_rate).astype(self.dtype)
    
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
        
        self.out_passive = np.zeros((self.total_channel, self.chunksize), dtype= self.dtype)
        
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
        
        self.passive_gain_cl = pyopencl.Buffer(self.ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=self.passive_gain.flatten().copy())
        self.out_passive_cl = pyopencl.Buffer(self.ctx, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf=self.out_passive)
        
        
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
                returns['passive'] = (None, None)
            
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
            
            
            if self.debug_mode:
                #~ pyopencl.enqueue_copy(self.queue,  self.out_pgc2, self.out_pgc2_cl)
                returns['pgc2'] = (pos2, self.out_pgc2.T)
            
            # passive gain by band
            # on very basic benchmark numpy is faster than opencl!!!
            pyopencl.enqueue_copy(self.queue,  self.out_pgc2, self.out_pgc2_cl)
            self.out_passive = self.out_pgc2 * self.passive_gain # NUMPY VERSION
            
            #~ mwgs = self.ctx.devices[0].get_info(pyopencl.device_info.MAX_WORK_GROUP_SIZE)
            #~ global_size = (self.total_channel, self.chunksize, )
            #~ local_size = (1, mwgs, )
            #~ event = self.opencl_prg.bychannel_gain(self.queue, global_size, local_size,
                                        #~ self.out_pgc2_cl, self.out_passive_cl, self.passive_gain_cl)
            
            #~ event.wait()
            #~ pyopencl.enqueue_copy(self.queue,  self.out_passive, self.out_passive_cl)
            
            if self.debug_mode:
                returns['passive'] = (pos2, self.out_passive.T)
            
            
            out_buffer = np.empty((self.nb_channel, self.chunksize), dtype=self.dtype)
            
            # sum by channel block
            
            for chan in range(self.nb_channel):
                #~ out_buffer[chan, :] = np.sum(self.out_pgc2[chan*self.nb_freq_band:(chan+1)*self.nb_freq_band, :], axis = 0)
                out_buffer[chan, :] = np.sum(self.out_passive[chan*self.nb_freq_band:(chan+1)*self.nb_freq_band, :], axis = 0)
            
            #compensate band_overlap_gain
            out_buffer *= self.band_overlap_gain
            

            
            
        

        returns['main_output'] = (pos2, out_buffer.T)
        return returns

