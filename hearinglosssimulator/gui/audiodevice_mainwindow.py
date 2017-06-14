from .common_mainwindow import *




class AudioDeviceMainWindow(CommonMainWindow):
    _prefix_application = 'AudioDevice_'
    
    def __init__(self, parent = None):
        CommonMainWindow.__init__(self, parent)

        self.resize(1000,800)


        self.audioDeviceSelection = AudioDeviceSelection(parent=self)
        self.gpuDeviceSelection = GpuDeviceSelection(parent=self)
        self.calibrationWidget = Calibration(parent=self)
        self.simulatorParameter = SimulatorParameter(parent=self)
        
        self.createActions()
        self.createToolBars()


        v = QT.QVBoxLayout()
        self.mainlayout.addLayout(v)
        
        v.addWidget(QT.QLabel(u'<h1><b>Setup loss on each ear</b>'))
        self.hearingLossParameter = HearingLossParameter()
        v.addWidget(self.hearingLossParameter)
        
        
        self.audio_stream_done = False

        self.configuration_elements = { 'audiodevice' : self.audioDeviceSelection,
                                                'gpudevice' : self.gpuDeviceSelection,
                                                'hearingloss' : self.hearingLossParameter,
                                                'calibration' : self.calibrationWidget,
                                                'simulator' :  self.simulatorParameter,
                                                }
        self.load_configuration()
        self.change_audio_device()

        

    def createActions(self):
        self.actions = OrderedDict()
        

        
        self.dialogs = OrderedDict([ ('Configure audio', {'widget' :self.audioDeviceSelection}), 
                                ('Configure GPU', {'widget' :self.gpuDeviceSelection}), 
                                ('Calibration', {'widget' :self.calibrationWidget}),
                                ('Simulator', {'widget' :self.simulatorParameter}),
                            ])
        
        for name, attr in self.dialogs.items():
            act = self.actions[name] = QT.QAction(name, self, checkable = False) #, icon =QT.QIcon(':/TODO.png'))
            act.triggered.connect(self.open_dialog)
            attr['action'] = act
            attr['widget'].setWindowFlags(QT.Qt.Window)
            attr['widget'].setWindowModality(QT.Qt.NonModal)
            attr['dia'] = dia = QT.QDialog()
            layout  = QT.QVBoxLayout()
            dia.setLayout(layout)
            layout.addWidget(attr['widget'])

    def createToolBars(self):
        self.toolbar = QT.QToolBar()
        self.toolbar.setToolButtonStyle(QT.Qt.ToolButtonTextUnderIcon)
        self.addToolBar(self.toolbar)
        self.toolbar.setIconSize(QT.QSize(60, 40))
        
        for name, act in self.actions.items():
            self.toolbar.addAction(act)
    
    def after_dialog(self):
        self.change_audio_device()
        nb_channel = self.simulatorParameter.get_configuration()['nb_channel']
        self.hearingLossParameter.set_nb_channel(nb_channel)
    
    def change_audio_device(self):
        self.calibrationWidget.device = self.audio_device
    
    @property
    def sample_rate(self):
        return 44100.
    
    @property
    def audio_device(self):
        return (self.audioDeviceSelection.get_configuration()['input_device'], 
                        self.audioDeviceSelection.get_configuration()['output_device'])

    def setup_processing(self):
        #~ print('setup_processing')
        # take from UI
        calibration = self.calibrationWidget.get_configuration()['spl_calibration_at_zero_dbfs']
        
        loss_params = self.hearingLossParameter.get_configuration()

        #DEBUG
        loss_params = { 'left' : {'freqs' : [ 125*2**i  for i in range(7) ], 'compression_degree': [0]*7, 'passive_loss_db' : [0]*7 } }
        loss_params['right'] = loss_params['left']
        
        for k in loss_params:
            print(k)
            print(loss_params[k]['freqs'])
            print(loss_params[k]['compression_degree'])
            print(loss_params[k]['passive_loss_db'])

        
        simulator_params = self.simulatorParameter.get_configuration()
        simulator_engine = simulator_params.pop('simulator_engine')
        
        #make params
        params ={}
        params.update(simulator_params)
        params['calibration'] = calibration
        params['loss_params'] = loss_params
        params['bypass'] = self.but_enable_bypass.isChecked()
        #~ print(params)
        classes = {'InvCGC': hls.InvCGC, 'InvComp': hls.InvComp}
        _Class = classes[simulator_engine]
        #~ print(_Class)
        
        #~ print(self.sample_rate)
        self.processing = _Class(sample_rate=self.sample_rate, 
                    apply_configuration_at_init=False, use_filter_cache=True,
                    debug_mode=False, **params)
        
        
        platform_index = self.gpuDeviceSelection.get_configuration()['platform_index']
        device_index = self.gpuDeviceSelection.get_configuration()['device_index']
        self.processing.create_opencl_context(
                gpu_platform_index = platform_index,
                gpu_device_index = device_index)
        
        self.processing.initialize()
    
    def setup_audio_stream(self):
        
        nb_channel = self.processing.nb_channel
        chunksize = self.processing.chunksize
        
        self.index = 0
        def callback(indata, outdata, frames, time, status):
            if status:
                print(status, flush=True)
            self.index += frames
            with self.mutex:
                returns = self.processing.proccesing_func(self.index, indata)
            index2, out = returns['main_output']
            if index2 is not None:
                outdata[:] = out
            else:
                outdata[:] = 0
        
        latency = 'low'
        #~ latency = 'high'
        self.stream = sd.Stream(channels=nb_channel, callback=callback, samplerate=self.sample_rate,
                        blocksize=chunksize, latency=latency, device=self.audio_device)
        
        self.audio_stream_done = True

    def compute_filters(self):
        print('compute_filters')
        with self.mutex:
            try:
                self.setup_processing()
                self.setup_audio_stream()
            except Exception as e:
                print(e)
                
            else:
                self.but_start_stop.setEnabled(True)
                self.but_enable_bypass.setEnabled(True)
    
    
    def set_bypass(self, bypass):
        if self.processing is None:
            return
        self.processing.set_bypass(bypass)
        

    def running(self):
        if not self.audio_stream_done:
            return False
        
        return self.stream.active
        
    
    def start_stop_audioloop(self, checked):
        if checked:
            self.stream.start()
        else:
            self.stream.stop()
    

