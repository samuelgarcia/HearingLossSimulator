import pytest
import hearinglosssimulator as hls
import numpy as np


def test_play_with_vlc():
    sound = np.random.randn(1024*50, 2).astype('float64')
    sound *= .01
    hls.play_with_vlc(sound, sample_rate=44100.)
    

def test_play_with_pyaudio():
    sound = np.random.randn(1024*50, 2).astype('float64')
    sound *= .01
    hls.play_with_pyaudio(sound, sample_rate=44100., output_device_index=None, chunksize=1024)



if __name__ == '__main__':
    #~ test_play_with_vlc()
    test_play_with_pyaudio()