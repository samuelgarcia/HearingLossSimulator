import numpy as np
import scipy.signal
import os
import tempfile

import soundfile


def sosfreqz(coeff,worN = 4096):
    # in scipy soon
    w, h = scipy.signal.freqz(coeff[0, :3], coeff[0, 3:], worN=  worN)
    for i in range(1, coeff.shape[0]):
        w, rowh = scipy.signal.freqz(coeff[i, :3], coeff[i, 3:], worN= worN)
        h *= rowh
    return w, h


def plot_filter(coeff, ax, samplerate, worN = 4096, **kargs):
    w, h = sosfreqz(coeff,worN = worN)
    ax.plot(w/np.pi*(samplerate/2.), 20*np.log10(h), **kargs)



def rms_level(sound):
    rms_value = np.sqrt(np.mean((sound-np.mean(sound))**2))
    rms_dB = 20.0*np.log10(rms_value/2e-5)
    return rms_dB

def play_with_vlc(sounds, samplerate = 44100):
    dir = tempfile.gettempdir()+'/play_with_vlc/'
    if not os.path.exists(dir):
        os.mkdir(dir)
    
    if isinstance(sounds, np.ndarray):
        sounds = { 'one_sound' : sounds }
    
    soundfilenames = [ ]
    for name, sound_buffer in sounds.items():
        soundfilename = dir+name+'.wav'
        print(sound_buffer.ndim)
        if sound_buffer.ndim==1:
            nchannels = 1
        else:
            nchannels = sound_buffer.shape[0]
        print (sound_buffer.transpose().shape, np.asarray(sound_buffer.transpose()).ndim)
        soundfile.write(soundfilename, sound_buffer.transpose(), int(samplerate), subtype = 'FLOAT')        
        soundfilenames.append(soundfilename)
    
    #~ print ' '.join(soundfilenames)
    os.system('vlc '+' '.join(soundfilenames))
    
    