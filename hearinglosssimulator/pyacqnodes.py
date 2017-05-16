from pyqtgraph.Qt import QtCore
import pyqtgraph as pg
import numpy as np

try:
    import pyacq
    HAS_PYACQ = True
except ImportError:
    HAS_PYACQ = False




class Mutex(QtCore.QMutex):
    def __exit__(self, *args):
        self.unlock()

    def __enter__(self):
        self.lock()
        return self    

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

        
    def after_input_connect(self, inputname):
        # this automatically propagate 'sample_rate', 'dtype', 'shape'
        # to output spec
        # in case of a Node that change sample_rate or the number of channel 
        # this must be overwirtten
        self.nb_channel = self.input.params['shape'][1]
        for k in ['sample_rate', 'dtype', 'shape']:
            self.outputs['signals'].spec[k] = self.input.params[k]
        
    
    def _initialize(self):
        print('_initialize')
        self.thread = NodeThread(self.input, self.outputs['signals'], self.proccesing_func)
    
    def _start(self):
        self.thread.last_pos = None
        self.thread.start()
    
    def _stop(self):
        self.thread.stop()
        self.thread.wait()
    
    def proccesing_func(self, pos, data):
        raise(NotImplementedError)
    



class BasePyacqNode(BaseProcessingNode):
    _processing_class = None

    
    def _configure(self, **params):
        """
        Parameters for configure
        -------
        coefficients: per channel sos filter coefficient shape (nb_channel, nb_section, 6)
        
        """
        
        self.params = params
        self.debug_mode = self.params.get('debug_mode', False)
        


    
    def after_input_connect(self, inputname):
        BaseProcessingNode.after_input_connect(self, inputname)

        self.nb_channel = self.input.params['shape'][1]
        self.sample_rate = self.input.params['sample_rate']
        self.dtype = self.input.params['dtype']
    
        # maybe patch here to test if harware support float64
        assert self.input.params['dtype'] == np.dtype('float32')

        
        
        for k in ['sample_rate', 'dtype', 'shape']:
            self.outputs['signals'].spec[k] = self.input.params[k]
        
        total_channel = self.params['nb_freq_band']*self.nb_channel
        
        if self.debug_mode:
            steps = ['pgc1', 'levels', 'hpaf', 'pgc2', 'passive']
            for step in steps:
                self._output_specs[step] = dict(streamtype='signals', shape=(-1,total_channel),
                        sample_rate=self.sample_rate)
            self.outputs = {name:pyacq.OutputStream(spec=spec, node=self, name=name) for name, spec in self._output_specs.items()}
        
    
    def _initialize(self):
        BaseProcessingNode._initialize(self)
        self.mutex = Mutex()
        self.processing = self._processing_class(nb_channel=self.nb_channel, sample_rate=self.sample_rate, dtype='float32',
                            apply_configuration_at_init=True, **self.params )
    
    
    def set_bypass(self, bypass):
        with self.mutex:
            self.processing.bypass = bypass
        
    
    def proccesing_func(self, pos, data):
        with self.mutex:
            returns = self.processing.proccesing_func(pos, data)
        
        if self.processing.debug_mode:
            
            for k, (pos, chunk) in returns.items():
                if k =='main_output':
                    continue
                self.outputs[k].send(chunk, index=pos)
        
        return returns['main_output']
        

from .invcgc import InvCGC

class HLSNode(BasePyacqNode):
    _processing_class = InvComp

    def online_configure(self, **params):
        
        self.params = params
        self.debug_mode = self.params.get('debug_mode', False)
        
        print(params)
        t0 = time.perf_counter()
        self.processing.configure(**params)
        t1 = time.perf_counter()
        print(t1-t0)
        self.processing._load_or_make_filters()
        t2 = time.perf_counter()
        print(t2-t1)
        with self.mutex:        
            self.processing.initlalize_cl()
        t3 = time.perf_counter()
        print(t3-t2)
        print(t3-t0)
    

