import hearinglosssimulator as hls


in_filename = 'in_sound.wav'
out_filename = 'out_sound.wav'

hls.compute_wave_file(in_filename, out_filename, 
        nb_freq_band=16, low_freq = 100., hight_freq = 15000.,
        tau_level = 0.005, smooth_time = 0.0005, level_step =1., level_max = 120.,
        calibration =  93.979400086720375,
        loss_weigth = [ [(50,-40.), (1000., -35), (2000., -40.), (6000., -35.), (25000,-40.),]],
        chunksize=512, backward_chunksize=1024, 
        duration_limit = 10.,
    )


