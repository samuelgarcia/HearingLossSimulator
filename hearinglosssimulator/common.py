import numpy as np
import joblib
import os
import sys
import pickle

# this make readthedocs work
try:
    import pyopencl
    mf = pyopencl.mem_flags
    HAS_PYOPENCL = True
except ImportError:
    HAS_PYOPENCL = False


class BaseMultiBand:
    """
    Common class hierited by InvCGC and InvComp.
    Both are multi band filter bank.
    """
    _attr_to_save = None
    
    def __init__(self, nb_channel=1, sample_rate=44100., dtype='float32',
                apply_configuration_at_init=True, use_filter_cache=True, **params):
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
        
        self.use_filter_cache = use_filter_cache

        self.ctx = None
        
        self.configure(**params)
        
        if apply_configuration_at_init:
            self.initialize()
        
        
    
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

    
    def configure(self, **kargs):
        self.configuration_kargs = dict(kargs)
        self._configure(**kargs)
    
    def _configure(self, nb_freq_band=32, low_freq = 100., high_freq = 15000.,
                tau_level = 0.005,  level_step =1., level_max = 100.,
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
        #~ print('self.configure', nb_freq_band, low_freq, high_freq, level_step, level_max)
        assert high_freq<self.sample_rate/2., 'high_freq is hiher that nyquist (sample_rate/2)'
        
        self.nb_freq_band = nb_freq_band
        self.low_freq = low_freq
        self.high_freq = high_freq
        self.tau_level = tau_level
        #~ self.smooth_time = smooth_time
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

    def _get_filter_cache_filename(self):
        d = {}
        d.update(self.configuration_kargs)
        d.update({'nb_channel' : self.nb_channel, 'sample_rate':self.sample_rate, 'dtype' : self.dtype.str})
        hash = joblib.hash(d)
        
        #TODO put this somewhere esle
        #~ cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache_filters')

        if sys.platform.startswith('win'):
            dirname = os.path.join(os.environ['APPDATA'], 'HearingLossSimulator')
        elif  sys.platform.startswith('darwin'):
            dirname = os.path.expanduser('~/Library/Application Support/HearingLossSimulator/')
        else:
            dirname = os.path.expanduser('~/.config/HearingLossSimulator')
        
        cache_dir = os.path.join(dirname, 'cache_filters')
        print('cache_dir', cache_dir)
        filename = os.path.join(cache_dir, self.__class__.__name__, hash)
        return filename

    def _save_filters(self):
        
        filename = self._get_filter_cache_filename()
        dir = os.path.dirname(filename)
        if not os.path.exists(dir):
            os.makedirs(dir)
        
        d = { k:getattr(self, k) for k in self._attr_to_save }
        with open(filename, mode='wb') as f:
            pickle.dump(d, f)
    
    def _load_filters(self):
        filename = self._get_filter_cache_filename()
        with open(filename, mode='rb') as f:
            d = pickle.load(f)
        for k in self._attr_to_save:
            setattr(self, k, d[k])
    
    def _load_or_make_filters(self):
        filename = self._get_filter_cache_filename()
        if os.path.exists(filename):
            self._load_filters()
            print('Load cache for filters', self.__class__.__name__, )
        else:
            print('Compute filters', self.__class__.__name__)
            self.make_filters()
            print('Save cache for filters', self.__class__.__name__)
            self._save_filters()
        
    
    def initialize(self):
        if self.use_filter_cache and self._attr_to_save is not None:
            self._load_or_make_filters()
        else:
            self.make_filters()
        
        if self.ctx is None:
            self.create_opencl_context()
        
        self.initlalize_cl()
        
        

    def set_bypass(self, bypass):
        self.bypass = bypass

    
