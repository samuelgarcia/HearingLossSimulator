# -*- coding: utf-8 -*- 
"""



"""



import numpy as np
import scipy
import scipy.signal
from .tools import play_with_vlc



def chirp(length, sample_rate = 44100., f1 = 50, f2 = 15000, ampl = .1):
    times = np.arange(length)/sample_rate
    sound = scipy.signal.chirp(times,f1,times[-1],f2)
    sound *= ampl
    return sound.astype('float32')


def crossing_chirp(length, sample_rate = 44100., f1 = 50, f2 = 15000, ampl = .1):
    times = np.arange(length)/sample_rate
    sound = scipy.signal.chirp(times,f1,times[-1],f2)+ scipy.signal.chirp(times,f2*.8,times[-1],f1*1.2)
    sound *= ampl
    return sound.astype('float32')

def several_sinus(length, sample_rate = 44100., freqs = [ 150, 203, 498, 1120],  ampl = .1):
    times = np.arange(length)/sample_rate
    sound = np.zeros_like(times)
    for f in freqs:
        sound += np.sin(np.pi*2*f*times) *  ampl
    return sound.astype('float32')


def moving_sinus(length, sample_rate = 44100., speed = .5,  f1 = 900., f2 = 1000,  ampl = .1):
    times = np.arange(length)/sample_rate
    f =  (np.sin(np.pi*2*speed*times)+1)/2 *  (f2-f1) + f1
    phase = np.cumsum(f/sample_rate)*2*np.pi
    sound = np.sin(phase) *  ampl
    return sound.astype('float32')

def whitenoise(length, sample_rate = 44100., ampl = .1):
    sound =np.random.randn(length) *  ampl
    return sound.astype('float32')

def notchnoise_fft(length, sample_rate = 44100.,  f1 = 1000., f2 = 2000., ampl = .1):
    sound =np.random.randn(length) *  ampl
    soundf = np.fft.fft(sound, n = sound.size)
    n1 =  int(f1/sample_rate*sound.size)
    n2 =  int(f2/sample_rate*sound.size)
    soundf[n1:n2] = 0.
    soundf[-n2:-n1] = 0.
    sound = np.real(np.fft.ifft(soundf))
    return sound.astype('float32')


def bandfiltered_noise(length, sample_rate = 44100., f1 = 200., f2 = 1200., ampl = .1):
    sound = whitenoise(length, sample_rate = sample_rate, ampl = ampl)
    soundf = np.fft.fft(sound, n = sound.size)
    n1 =  int(f1/sample_rate*sound.size)
    n2 =  int(f2/sample_rate*sound.size)
    soundf[:n1] = 0.
    soundf[-n1:] = 0.
    soundf[n2:-n2] = 0.
    sound = np.real(np.fft.ifft(soundf))
    return sound.astype('float32')
    
    
def erb_noise(length, sample_rate = 44100., f = 500, ampl = 0.1):
    w=24.7*(4.37e-3*f+1.)
    return bandfiltered_noise(length, sample_rate = sample_rate, f1 = f-w/2, f2 = f+w/2, ampl = ampl)


def moving_erb_noise(length, sample_rate = 44100., f1 = 200, f2 = 1200, speed = .1,
            trajectorytype = 'sinus', chunksize = 2**10, ampl = 0.1):
    times = np.arange(length)/sample_rate
    if trajectorytype=='sawtooth':
        trajectory = scipy.signal.waveforms.sawtooth(2*np.pi*speed*times, width = 1.)
    elif trajectorytype=='triangle':
        trajectory = scipy.signal.waveforms.sawtooth(2*np.pi*speed*times, width = .5)
    elif trajectorytype=='sinus':
        trajectory = (np.sin(np.pi*2*speed*times))
    trajectory = (trajectory +1)/2 *  (f2-f1) + f1
    
    trajectory = trajectory[::chunksize//2]
    
    w = np.hanning(chunksize)
    sound = np.zeros(length)
    for i in range(length//chunksize*2-1):
        sl = slice(i*chunksize//2, i*chunksize//2+chunksize)
        f = trajectory[i]
        s = erb_noise(chunksize,  sample_rate = sample_rate, f = f, ampl = ampl)
        sound[sl] += (s * w)
    return sound.astype('float32') 



def moving_mask_around_tone(length, sample_rate = 44100., freqs = [ 1000.], f1 = 2000., f2 = 2500.):
    noise = moving_erb_noise(length,  trajectorytype='triangle',  f1 = f1, f2 = f2, speed = .1, ampl = .5)
    tone = several_sinus(length, freqs = freqs,  ampl = .025)
    return noise+tone
    
    
    

    
    
    