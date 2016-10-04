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


# compute the sound numpy buffer
out_sound = hls.compute_numpy(in_sound, sample_rate,
        nb_freq_band=16, low_freq = 100., hight_freq = 15000.,
        tau_level = 0.005, smooth_time = 0.0005, level_step =1., level_max = 120.,
        calibration =  93.979400086720375,
        loss_weigth = [ [(50,0.), (1000., -35), (2000., -40.), (6000., -35.), (25000,0.),]]*nb_channel,
        chunksize=512, backward_chunksize=512*4, 
    )



# play with VLC
sounds = {'in_sound' : in_sound, 'out_sound' : out_sound }
hls.play_with_vlc(sounds, sample_rate=sample_rate)
