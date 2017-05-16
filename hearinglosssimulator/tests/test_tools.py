import pytest
import hearinglosssimulator as hls
import numpy as np


def test_play_with_vlc():
    sound = np.random.randn(1024*50, 2).astype('float64')
    sound *= .01
    hls.play_with_vlc(sound, sample_rate=44100.)
    

def test_play_on_device():
    sound = np.random.randn(1024*50, 2).astype('float64')
    sound *= .01
    hls.play_on_device(sound, sample_rate=44100., device=None, chunksize=1024)



if __name__ == '__main__':
    #~ test_play_with_vlc()
    test_play_on_device()