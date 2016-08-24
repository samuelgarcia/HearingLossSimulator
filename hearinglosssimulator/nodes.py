import numpy as np
from pyqtgraph.Qt import QtCore
import pyqtgraph as pg
from pyqtgraph.util.mutex import Mutex
import pyacq



class NodeThread(pyacq.ThreadPollInput):
    def __init__(self, input_stream, output_stream, timeout = 200, parent = None):
        pyacq.ThreadPollInput.__init__(self, input_stream, timeout = timeout, return_data=True, parent = parent)
        self.output_stream = output_stream
        #~ self.mutex = Mutex()

    def process_data(self, pos, data):
        with self.mutex:
            chunk_filtered = self.filter_engine.compute_one_chunk(data)
        self.output_stream.send(chunk_filtered, index=pos)
        
    #~ def set_params(self, engine, coefficients, nb_channel, dtype, chunksize):
        #~ assert engine in sosfilter_engines
        #~ EngineClass = sosfilter_engines[engine]
        #~ with self.mutex:
            #~ self.filter_engine = EngineClass(coefficients, nb_channel, dtype, chunksize)


class BaseProcessingNode(Pyacq.Node,  QtCore.QObject):
    """
    """
    
    _input_specs = {'signals' : dict(streamtype = 'signals')}
    _output_specs = {'signals' : dict(streamtype = 'signals')}
    
    _proccessing_step = None
    
    def __init__(self, parent = None, **kargs):
        QtCore.QObject.__init__(self, parent)
        Node.__init__(self, **kargs)
    
    #~ def _configure(self, coefficients = None, engine='scipy', chunksize=None):
        #~ """
        #~ Set the coefficient of the filter.
        #~ See http://scipy.github.io/devdocs/generated/scipy.signal.sosfilt.html for details.
        #~ """
        #~ self.set_coefficients(coefficients)
        #~ self.engine = engine
        #~ self.chunksize = chunksize

    def after_input_connect(self, inputname):
        self.nb_channel = self.input.params['shape'][1]
        for k in ['sample_rate', 'dtype', 'shape']:
            self.output.spec[k] = self.input.params[k]
    
    def _initialize(self):
        self.thread = SosFilterThread(self.input, self.output)
        self.thread.set_params(self.engine, self.coefficients, self.nb_channel,
                            self.output.params['dtype'], self.chunksize)
    
    def _start(self):
        self.thread.last_pos = None
        self.thread.start()
    
    def _stop(self):
        self.thread.stop()
        self.thread.wait()
    
    def set_coefficients(self, coefficients):
        self.coefficients = coefficients
        if self.initialized():
            self.thread.set_params(self.engine, self.coefficients, self.nb_channel,
                                self.output.params['dtype'], self.chunksize)


class DoNothing(BaseProcessingNode):
    
    

pyacs.register_node_type(DoNothing)
