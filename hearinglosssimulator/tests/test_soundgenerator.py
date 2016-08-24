import pytest
import hearinglosssimulator as hls
import numpy as np

if __name__ == '__main__':
    from matplotlib import pyplot
    length = 512*1000
    #~ hls.play_with_vlc(hls.crossing_chirp(length))
    #~ hls.play_with_vlc(hls.several_sinus(length, freqs = [440.]))
    #~ hls.play_with_vlc(hls.moving_sinus(length))
    #~ hls.play_with_vlc(hls.whitenoise(length))
    #~ hls.play_with_vlc(hls.notchnoise(length))
    #~ hls.play_with_vlc(hls.whitenoise(length)+hls.moving_sinus(length)*.3)
    #~ hls.play_with_vlc(hls.bandfiltered_noise(length))
    #~ hls.play_with_vlc(hls.erb_noise(length))
    #~ hls.play_with_vlc(hls.moving_erb_noise(length))
    hls.play_with_vlc(hls.moving_erb_noise(length,  trajectorytype='sinus', speed = .1))
    #~ hls.play_with_vlc(hls.moving_mask_around_tone(length))
    
    
    #~ sound = hls.moving_mask_around_tone(length)
    #~ sound = moving_erb_noise(length,  trajectorytype='triangle',  f1 = 400, f2 = 1000, speed = .01, ampl = .1)
    #~ sound = notchnoise(length)
    
    #~ fig, ax = pyplot.subplots()
    #~ ax.plot(sound)
    #~ fig, ax = pyplot.subplots()
    #~ ax.specgram(sound, NFFT=1024, Fs=44100, noverlap=512,)
    #~ fig, ax = pyplot.subplots()
    #~ ax.psd(sound, Fs=44100, NFFT = 2**12, color = 'b')
    #~ pyplot.show()
    


