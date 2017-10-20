"""

"""
import numpy as np
import scipy.signal
import os
import tempfile

try:
    import soundfile
    HAS_SOUNDFILE = True
except ImportError:
    HAS_SOUNDFILE = False
#~ import pyaudio

try:
    import sounddevice as sd
    HAS_SOUNDDEVICE = True
except ImportError:
    HAS_SOUNDDEVICE = False
except OSError:
    # not portaudio
    HAS_SOUNDDEVICE = False



def sosfreqz(coeff,worN = 4096):
    # in scipy soon
    w, h = scipy.signal.freqz(coeff[0, :3], coeff[0, 3:], worN=  worN)
    for i in range(1, coeff.shape[0]):
        w, rowh = scipy.signal.freqz(coeff[i, :3], coeff[i, 3:], worN= worN)
        h *= rowh
    return w, h


def plot_filter(coeff, ax, sample_rate, worN = 4096, **kargs):
    w, h = sosfreqz(coeff,worN = worN)
    ax.plot(w/np.pi*(sample_rate/2.), 20*np.log10(np.abs(h)), **kargs)



def rms_level(sound):
    rms_value = np.sqrt(np.mean((sound-np.mean(sound))**2))
    rms_dB = 20.0*np.log10(rms_value/2e-5)
    return rms_dB


    
    

def play_with_vlc(sounds, sample_rate = 44100):
    assert HAS_SOUNDFILE, 'soundfile need to be installed'
    dir = tempfile.gettempdir()+'/play_with_vlc/'
    if not os.path.exists(dir):
        os.mkdir(dir)
    
    if isinstance(sounds, np.ndarray):
        sounds = { 'one_sound' : sounds }
    
    
    soundfilenames = [ ]
    for name, sound_buffer in sounds.items():
        soundfilename = dir+name+'.wav'
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
    #~ os.system('vlc '+' '.join(soundfilenames))
    if sys.platform.startswith('darwin'):
        vlc = '/Applications/VLC.app/Contents/MacOS/VLC'
    else:
        vlc = 'vlc'
    os.system(vlc+" "+' '.join('"{}"'.format(f) for f in soundfilenames))



def play_on_device(sound, sample_rate=44100, device=None, chunksize=1024):
    assert HAS_SOUNDDEVICE, 'sounddevice need to be installed'
    sound = sound.astype('float32')
    sd.play(sound, samplerate=sample_rate, blocksize=chunksize, blocking=True)




#~ def online_processing():
    




