import hearinglosssimulator as hls
import numpy as np


sample_rate = 44100.
duration = 4. #s
length = int(sample_rate*duration)
nb_channel = 2

# there are some helper for creating in_sounds in hls.in_soundgenerators
in_sound = hls.whitenoise(length, sample_rate=sample_rate,)
#~ in_sound = hls.moving_erb_noise(length,  trajectorytype='sinus', speed = .1)

# the shape must (length, nb_channel) so
in_sound = np.tile(in_sound[:, None],(1, nb_channel))

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

# compute the sound numpy buffer
out_sound = hls.compute_numpy(in_sound, sample_rate,
        #~ processing_class=hls.InvComp,
        processing_class=hls.InvCGC,
        nb_freq_band=32, low_freq = 100., high_freq = 15000.,
        tau_level = 0.005, level_step =1., level_max = 100.,
        calibration =  93.979400086720375,
        loss_params = loss_params,
        chunksize=512, backward_chunksize=512*4, 
    )



# play with VLC
sounds = {'in_sound' : in_sound, 'out_sound' : out_sound }
hls.play_with_vlc(sounds, sample_rate=sample_rate)
