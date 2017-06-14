import pytest
import hearinglosssimulator as hls

import matplotlib.pyplot as plt
from matplotlib.cm import get_cmap
import numpy as np


def test_cgc_filter():
    freqs = [5000.]
    #~ freqs = [ 125*2**i  for i in range(7) ]
    #~ freqs = hls.erbspace(80.,15000., 16.)
    
    #~ compression_degree = [1]
    #~ compression_degree = [0.25]
    compression_degree = [0]
    level_max = 100.
    level_step = 10.
    sample_rate = 44100.
    coefficients_pgc, coefficients_hpaf, levels, band_overlap_gain = hls.make_cgc_filter(freqs, compression_degree, level_max, level_step, sample_rate)
    
    fig, ax1 = plt.subplots()
    fig, ax2 = plt.subplots()
    fig, ax3 = plt.subplots()
    
    levels_colors = [ get_cmap('jet', len(levels))(l) for l, level in enumerate(levels) ]
    freqs_colors = [ get_cmap('jet', len(freqs))(f) for f, freq in enumerate(freqs) ]
    
    for f, freq in enumerate(freqs):
        gains = np.zeros(len(levels))
        for l, level in enumerate(levels):
            
            all_filter = np.concatenate([coefficients_pgc[f,:,:],coefficients_hpaf[f,l,:,:], coefficients_pgc[f,:,:]], axis = 0)
            w, h = hls.sosfreqz(all_filter, worN = 2**16,)
            gains[l] = np.max(20*np.log10(np.abs(h)))
            
            
            
            hls.plot_filter(all_filter, ax2, sample_rate, color=levels_colors[l])
            hls.plot_filter(coefficients_hpaf[f,l,:,:], ax3, sample_rate, color=levels_colors[l])
        
        hls.plot_filter(coefficients_pgc[f,:,:], ax3, sample_rate, color='k')
        ax3.axvline(freq, color='k')
        ax2.axvline(freq, color='k')
        
        ax1.plot(levels, levels+gains, label='{:0.1f}'.format(freq), color=freqs_colors[f])
    ax1.plot(levels,levels, color='r', ls='--')
        
        
    ax1.legend()
    ax2.set_ylim(-50,50)
    ax3.set_ylim(-50,50)
    
    plt.show()


def test_invcomp_filter():
    freqs = [1000.]
    #~ freqs = [5000.]
    #~ freqs = [ 125*2**i  for i in range(7) ]
    #~ freqs = hls.erbspace(80.,15000., 32.)
    
    #~ compression_degree = [1]* len(freqs) 
    #~ compression_degree = [0.5]
    #~ compression_degree = [0.25] * len(freqs)
    compression_degree = [0.] * len(freqs)
    #~ compression_degree = [0.5] * len(freqs)
    
    level_max = 100.
    level_step = 10.
    sample_rate = 44100.
    coefficients_pgc, gain_controlled, levels, band_overlap_gain = hls.make_invcomp_filter(freqs, compression_degree, level_max, level_step, sample_rate)
    #~ print(gain_controlled)
    #~ fig, ax = plt.subplots()
    
    #~ exit()
    
    fig, ax1 = plt.subplots()
    #~ fig, ax2 = plt.subplots()
    fig, ax3 = plt.subplots()
    
    levels_colors = [ get_cmap('jet', len(levels))(l) for l, level in enumerate(levels) ]
    freqs_colors = [ get_cmap('jet', len(freqs))(f) for f, freq in enumerate(freqs) ]
    
    for f, freq in enumerate(freqs):
        #~ gains = np.zeros(len(levels))
        gains = 20*np.log10(gain_controlled[f])
        
        #~ for l, level in enumerate(levels):
            
            #~ all_filter = np.concatenate([coefficients_pgc[f,:,:], coefficients_pgc[f,:,:]], axis = 0)
            #~ w, h = hls.sosfreqz(all_filter, worN = 2**16,)
            #~ gains[l] = np.max(20*np.log10(np.abs(h)))
            #~ gain = np.max(20*np.log10(np.abs(h)))
            
            #~ hls.plot_filter(all_filter, ax2, sample_rate, color=levels_colors[l])
            #~ hls.plot_filter(coefficients_hpaf[f,l,:,:], ax3, sample_rate, color=levels_colors[l])
        
        hls.plot_filter(coefficients_pgc[f,:,:], ax3, sample_rate, color='k')
        ax3.axvline(freq, color='k')
        #~ ax2.axvline(freq, color='k')
        
        ax1.plot(levels, levels+gains, label='{:0.1f}'.format(freq), color=freqs_colors[f])
        #~ ax1.plot(levels, gains, label='{:0.1f}'.format(freq), color=freqs_colors[f])
        
    ax1.plot(levels,levels, color='r', ls='--')
        
        
    ax1.legend()
    #~ ax2.set_ylim(-50,50)
    ax3.set_ylim(-50,50)
    
    plt.show()
    
    
if __name__ == '__main__':
    test_cgc_filter()
    #~ test_invcomp_filter()
    
