import numpy as np
import scipy.signal
import os
import tempfile

import soundfile
import pyaudio

def sosfreqz(coeff,worN = 4096):
    # in scipy soon
    w, h = scipy.signal.freqz(coeff[0, :3], coeff[0, 3:], worN=  worN)
    for i in range(1, coeff.shape[0]):
        w, rowh = scipy.signal.freqz(coeff[i, :3], coeff[i, 3:], worN= worN)
        h *= rowh
    return w, h


def plot_filter(coeff, ax, sample_rate, worN = 4096, **kargs):
    w, h = sosfreqz(coeff,worN = worN)
    ax.plot(w/np.pi*(sample_rate/2.), 20*np.log10(h), **kargs)



def rms_level(sound):
    rms_value = np.sqrt(np.mean((sound-np.mean(sound))**2))
    rms_dB = 20.0*np.log10(rms_value/2e-5)
    return rms_dB


    
    

def play_with_vlc(sounds, sample_rate = 44100):
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
            nb_channel = 1
        else:
            nb_channel = sound_buffer.shape[1]
        #~ print (sound_buffer.transpose().shape, np.asarray(sound_buffer.transpose()).ndim)
        sound_buffer = sound_buffer.astype('float32')
        #~ soundfile.write(soundfilename, sound_buffer.transpose(), int(sample_rate), subtype = 'FLOAT')
        soundfile.write(soundfilename, sound_buffer, int(sample_rate), subtype = 'FLOAT')
        soundfilenames.append(soundfilename)
    
    #~ print ' '.join(soundfilenames)
    os.system('vlc '+' '.join(soundfilenames))



def play_with_pyaudio(sound, sample_rate = 44100, output_device_index=None, chunksize=1024):
    pa = pyaudio.PyAudio()
    
    if output_device_index is None:
        output_device_index = pa.get_default_output_device_info()['index']
        #~ print('output_device_index', output_device_index)
    
    if sound.ndim==1:
        nb_channel = 1
    else:
        nb_channel = sound.shape[1]
    
    sound = sound.astype('float32')
    audiostream = pa.open(rate=int(sample_rate), channels=int(nb_channel), format= pyaudio.paFloat32,
                    input=False, output=True, input_device_index=None, output_device_index=output_device_index,
                    frames_per_buffer=chunksize)
    
    nloop = sound.shape[0]//chunksize + 1
    for i in range(nloop):
        chunk = sound[i*chunksize:(i+1)*chunksize]
        if chunk.size>0:
            audiostream.write(bytes(chunk))
    
