import hearinglosssimulator as hls


in_filename = 'in_sound.wav'
out_filename = 'out_sound.wav'

# define loss parameters
loss_params = {  'left' : {'freqs' :  [125., 250., 500., 1000., 2000., 4000., 8000.],
                                            'compression_degree': [0., 0., 0., 0., 0., 0., 0.],
                                            'passive_loss_db' : [0., 0., 0., 0., 0., 0., 0.],
                                        },
                            'right' : {'freqs' :  [125., 250., 500., 1000., 2000., 4000., 8000.],
                                            'compression_degree': [0., 0., 0., 0., 0., 0., 0.],
                                            'passive_loss_db' : [0., 0., 0., 0., 0., 0., 0.],
                                        }
                        }

hls.compute_wave_file(in_filename, out_filename, 
        nb_freq_band=16, low_freq = 100., hight_freq = 15000.,
        tau_level = 0.005, smooth_time = 0.0005, level_step =1., level_max = 120.,
        calibration =  93.979400086720375,
        loss_params = loss_params,
        chunksize=512, backward_chunksize=1024, 
        duration_limit = 10.,
    )


