import numpy as np
from pyqtgraph.Qt import QtCore
import pyqtgraph as pg
from pyqtgraph.util.mutex import Mutex
import pyacq
import time
import pyopencl
mf = pyopencl.mem_flags
import os


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
            self.output.spec[k] = self.input.params[k]
        
    
    def _initialize(self):
        self.thread = NodeThread(self.input, self.output, self.proccesing_func)
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
    def _configure(self, chunksize=None):
        self.chunksize = chunksize
    
    def proccesing_func(self, pos, data):
        time.sleep(self.chunksize/self.input.params['sample_rate']*0.8)
        return pos, data


class Gain(BaseProcessingNode):
    def _configure(self, factor=1.):
        self.factor = factor
    def proccesing_func(self, pos, data):
        #~ print(pos, data.shape, self.name, data[:10], )
        return pos, data*self.factor



class CL_SosFilter(CL_BaseProcessingNode):
    """
    Node for conputing sos filter on multi channel.
    
    """
    def _configure(self, coefficients=None, chunksize=512, backward_chunksize=1024, **kargs):
        """
        Parameters for configure
        -------
        coefficients: per channel sos filter coefficient shape (nb_channel, nb_section, 6)
        
        """
        CL_BaseProcessingNode._configure(self, **kargs)
        
        self.coefficients = coefficients
        self.chunksize = chunksize
        self.backward_chunksize = backward_chunksize
        
        assert self.chunksize is not None, 'chunksize for opencl must be fixed'
        
        self.coefficients = self.coefficients.astype('float32')
        assert self.coefficients.ndim == 3
        if not self.coefficients.flags['C_CONTIGUOUS']:
            self.coefficients = self.coefficients.copy()
        self.nb_section = self.coefficients.shape[1]

        #~ assert self.dtype == np.dtype('float32')
        #~ assert self.coefficients.shape[0]==self.nb_channel, 'wrong coefficients.shape'
        assert self.coefficients.shape[2]==6, 'wrong coefficients.shape'


    def initlalize_cl(self):
        self.dtype = self.input.params['dtype']
        assert self.dtype == np.dtype('float32')
        assert self.coefficients.shape[0]==self.nb_channel, 'wrong coefficients.shape'
        
        #host arrays
        self.zi1 = np.zeros((self.nb_channel, self.nb_section, 2), dtype= self.dtype)
        self.output1 = np.zeros((self.nb_channel, self.chunksize), dtype= self.dtype)
        
        #GPU buffers
        self.coefficients_cl = pyopencl.Buffer(self.ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=self.coefficients)
        self.zi1_cl = pyopencl.Buffer(self.ctx, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf=self.zi1)
        self.input1_cl = pyopencl.Buffer(self.ctx, mf.READ_WRITE, size=self.output1.nbytes)
        self.output1_cl = pyopencl.Buffer(self.ctx, mf.READ_WRITE, size=self.output1.nbytes)
        
        # compialtion
        kernel = cl_code%dict(forward_chunksize=self.chunksize, backward_chunksize=self.backward_chunksize,
                                                            nb_channel=self.nb_channel, max_chunksize=max(self.chunksize, self.backward_chunksize))
        prg = pyopencl.Program(self.ctx, kernel)
        self.opencl_prg = prg.build(options='-cl-mad-enable')
        
        self.global_size = None
        self.local_size = None
        self.global_size = (self.nb_channel, self.nb_section,)
        self.local_size = (1, self.nb_section, )
        
    
    def proccesing_func(self, pos, data):
        
        chunk = data.T
        if not chunk.flags['C_CONTIGUOUS']:
            chunk = chunk.copy()
        pyopencl.enqueue_copy(self.queue,  self.input1_cl, chunk)
        
        event = self.opencl_prg.forward_filter(self.queue, self.global_size, self.local_size,
                                self.input1_cl, self.output1_cl, self.coefficients_cl, self.zi1_cl, np.int32(self.nb_section))
        event.wait()
        
        pyopencl.enqueue_copy(self.queue,  self.output1, self.output1_cl)
        chunk_filtered = self.output1.T.copy()
        return pos, chunk_filtered
        



class MainProcessing(CL_BaseProcessingNode):
    """
    Node for conputing DGCG filters.
    
    Variables:
    ----
    nb_channel: nb channel input
    tot_channel : total channel = nb_channelXnb_band
    
    
    """
    def _configure(self, nb_freq_band=16, chunksize=512, backward_chunksize=1024, **kargs):
        """
        Parameters for configure
        -------
        coefficients: per channel sos filter coefficient shape (nb_channel, nb_section, 6)
        
        """
        CL_BaseProcessingNode._configure(self, **kargs)
        
        self.nb_freq_band = nb_freq_band
        self.chunksize = chunksize
        self.backward_chunksize = backward_chunksize
        
        
        
        
        
        assert self.chunksize is not None, 'chunksize for opencl must be fixed'
        
        self.coefficients = self.coefficients.astype('float32')
        assert self.coefficients.ndim == 3
        if not self.coefficients.flags['C_CONTIGUOUS']:
            self.coefficients = self.coefficients.copy()
        self.nb_section = self.coefficients.shape[1]

        #~ assert self.dtype == np.dtype('float32')
        #~ assert self.coefficients.shape[0]==self.nb_channel, 'wrong coefficients.shape'
        assert self.coefficients.shape[2]==6, 'wrong coefficients.shape'
        
        # TODO filters init
        
        #TODO expdecays init
        #~ self.smooth_time = smooth_time
        #~ samedecay = np.exp(-2./tau1/samplerate)
        #~ print samedecay
        #~ self.expdecays = np.ones((self.nfreq), dtype = self.dtype) * samedecay


    def after_input_connect(self, inputname):
        CL_BaseProcessingNode.after_input_connect(self, inputname)

        self.nb_channel = self.input.params['shape'][1]
        self.sample_rate = self.input.params['sample_rate']
        
        
        for k in ['sample_rate', 'dtype', 'shape']:
            self.output.spec[k] = self.input.params[k]
        
        
        self.total_channel = self.nb_freq_band*self.nb_channel
        
        steps = ['pgc1', 'levels', 'hpaf', 'pgc2']
        for step in steps:
            self._output_specs[step] = dict(streamtype = 'signals', shape=(-1,self.total_channel),
                    sample_rate=self.sample_rate)
        
    
    def initlalize_cl(self):
        """
        
        Steps:
          * pgc1:
          * levels
          * hpaf: 
          * pgc2: 
        
        """
        self.dtype = self.input.params['dtype']
        assert self.dtype == np.dtype('float32')
        #~ assert self.coefficients.shape[0]==self.nb_channel, 'wrong coefficients.shape'
        
        #host arrays
        self.in_pgc1 = np.zeros((self.total_channel, self.chunksize), dtype= self.dtype)
        self.out_pgc1 = np.zeros((self.total_channel, self.chunksize), dtype= self.dtype)
        self.zi_pgc1 = np.zeros((self.total_channel, self.nb_section, 2), dtype= self.dtype)
        
        #~ self.previouslevel = np.zeros((self.total_channel, smooth), dtype = self.dtype)# TODO 
        self.previouslevel = np.zeros((self.total_channel, smooth), dtype = self.dtype)
        self.out_levels = np.zeros((self.total_channel, self.chunksize), dtype= self.dtype)
        
        self.out_hpaf = np.zeros((self.total_channel, self.chunksize), dtype= self.dtype)
        self.zi_hpaf = np.zeros((self.total_channel, self.nb_section, 2), dtype= self.dtype)
        
        self.in_pgc2 = np.zeros((self.total_channel, self.backward_chunksize), dtype= self.dtype)
        self.out_pgc2 = np.zeros((self.total_channel, self.chunksize), dtype= self.dtype)
        self.zi_pgc2 = np.zeros((self.total_channel, self.nb_section, 2), dtype= self.dtype)
        
        
        #GPU buffers
        self.coefficients_pgc_cl = pyopencl.Buffer(self.ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=self.coefficients_pgc)
        
        self.in_pgc1_cl = pyopencl.Buffer(self.ctx, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf=self.in_pgc1)
        self.out_pgc1_cl = pyopencl.Buffer(self.ctx, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf=self.out_pgc1)
        self.zi_pgc1_cl = pyopencl.Buffer(self.ctx, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf=self.zi_pgc1)
        
        self.expdecays_cl = cl.Buffer(self.ctx, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf=self.expdecays)
        self.previouslevel_cl = cl.Buffer(self.ctx, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf=self.previouslevel)
        self.out_levels_cl = pyopencl.Buffer(self.ctx, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf=self.out_levels)
        
        self.out_hpaf_cl = pyopencl.Buffer(self.ctx, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf=self.out_hpaf)
        self.zi_hpaf_cl = pyopencl.Buffer(self.ctx, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf=self.zi_hpaf)
        self.coefficients_hpaf_cl = pyopencl.Buffer(self.ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=self.coefficients_hpaf)
        
        self.in_pgc2_cl = pyopencl.Buffer(self.ctx, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf=self.in_pgc2)
        self.out_pgc2_cl = pyopencl.Buffer(self.ctx, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf=self.out_pgc2)
        self.zi_pgc2_cl = pyopencl.Buffer(self.ctx, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf=self.zi_pgc2)
        
        
        # compialtion
        kernel = cl_code%dict(forward_chunksize=self.chunksize, backward_chunksize=self.backward_chunksize,
                                                            nb_channel=self.total_channel, max_chunksize=max(self.chunksize, self.backward_chunksize))
        prg = pyopencl.Program(self.ctx, kernel)
        self.opencl_prg = prg.build(options='-cl-mad-enable')
        
        
    
    def proccesing_func(self, pos, data):
        self.chunkcount = #TODO
        
        chunk = data.T
        if not chunk.flags['C_CONTIGUOUS']:
            chunk = chunk.copy()
        pyopencl.enqueue_copy(self.queue,  self.input1_cl, chunk)
        
        #pgc1
        global_size = (self.total_channel, self.nb_section,)
        local_size = (1, self.nb_section, )
        event = self.opencl_prg.forward_filter(self.queue, global_size, local_size,
                                self.in_pgc1_cl, self.out_pgc1_cl, self.coefficients_pgc_cl, self.zi_pgc1_cl, np.int32(self.nb_section))
        event.wait()
        
        #levels
        global_size = (self.nchannel, )
        local_size = (1,  )
        event = self.opencl_prg.estimate_leveldb(self.queue, global_size, local_size,
                                self.out_pgc1_cl, self.out_levels_cl, self.previouslevel_cl, self.expdecays_cl, np.int64(self.chunkcount))  #TODO change chnkcount by pos directly
        event.wait()
        
        # hpaf
        global_size = (self.nchannel, self.ncascade,)
        local_size = (1, self.ncascade, )
        event = self.opencl_prg.dynamic_sos_filter(self.queue, global_size, local_size,
                                self.out_pgc1_cl, self.out_levels_cl, self.out_hpaf_cl, self.coefficients_hpaf_cl,
                                self.zi_hpaf_cl, np.int32(self.nb_section))
        event.wait()
        
        # pgc2
        # #TODO copy
        
        global_size = (self.total_channel, self.nb_section,)
        local_size = (1, self.nb_section, )
        event = self.opencl_prg.backward_filter(self.queue, global_size, local_size,
                                self.in_pgc2_cl, self.out_pgc2_cl, self.coefficients_pgc_cl, self.zi_pgc2_cl, np.int32(self.nb_section))
        event.wait()
        
        pyopencl.enqueue_copy(self.queue,  self.out_pgc2, self.out_pgc2_cl)
        
        
        # sum
        for chan in range(self.nchannelout):
            #~ self.output_buffers[0].nparray[chan, :] = np.mean(self.input_buffers[0].nparray[chan*self.blocksize:(chan+1)*self.blocksize, :], axis = 0)
            self.output_buffers[0].nparray[chan, :] = np.sum(self.input_buffers[0].nparray[chan*self.blocksize:(chan+1)*self.blocksize, :], axis = 0)



        pyopencl.enqueue_copy(self.queue,  self.output1, self.output1_cl)
        chunk_filtered = self.output1.T.copy()
        return pos, chunk_filtered

