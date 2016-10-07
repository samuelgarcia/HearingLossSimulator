import pytest
import hearinglosssimulator as hls

import matplotlib.pyplot as plt
from matplotlib.cm import get_cmap
import numpy as np


from hearinglosssimulator import (gammatone, asymmetric_compensation_coeffs, loggammachirp, erbspace)
from hearinglosssimulator import sosfreqz

NFFT = 2**16

def debug_make_cgc_filter(freqs, compression_degree, level_max, level_step, sample_rate, dtype='float32', 
                    frat_law='irino'):
    """
    
    parameters
    ----
    
    freqs: vector of central freqquencies Hz
    
    compression_degree: vector of compression degree for each freq with:
        * 1=no compression impairement
        * 0= maximum compression impairement
    
    
    
    
    """
    freqs = np.asarray(freqs)
    compression_degree = np.asarray(compression_degree)
    
    nb_freq_band = len(freqs)
    
    # pgc filter coefficient
    b1 = 1.81
    c1 = -2.96
    
    # hpaf filter coefficient
    b2 = 2.17
    c2 = 2.2
    
    p0=2
    p1=1.7818*(1-0.0791*b2)*(1-0.1655*abs(c2))
    p2=0.5689*(1-0.1620*b2)*(1-0.0857*abs(c2))
    p3=0.2523*(1-0.0244*b2)*(1+0.0574*abs(c2))
    p4=1.0724

    coefficients_pgc = loggammachirp(freqs, sample_rate, b=b1, c=c1).astype(dtype)
    
    #noramlize PGC to 0 db at maximum 
    for f, freq in enumerate(freqs):
        w, h = sosfreqz(coefficients_pgc[f,:,:], worN =2**16,)
        gain = np.max(np.abs(h))
        coefficients_pgc[f,0, :3] /= gain
    
    # Construct hpaf filters : pre compute for all sound levels for each freq
    levels = np.arange(0, level_max+level_step,level_step)
    nlevel = levels.size
    
    # construct hpaf depending on compression_degree for each freq
    coefficients_hpaf = np.zeros((nb_freq_band, len(levels), 4, 6), dtype = dtype)
        
    alpha = compression_degree
    
    
    if frat_law=='irino':
        # Toshio Irino coefficient
        frat0r = 1 + 0.466 * (1-alpha)
        frat1r =  - 0.0109 * (1-alpha)
    elif frat_law=='garcia2015':
        # Samuel Garcia coefficient 2015
        w = (1-alpha) * 5 / 3
        frat1r = -w/65/2.
        frat0r = 1+w/2.
    elif frat_law=='garcia2016':
        # Samuel Garcia coefficient 2016
        frat0r = 1 + (1-alpha)*1.3333
        frat1r = - (1-alpha) * 0.0205
    
    for l, level in enumerate(levels):
        # minus for inverse compression = moving left
        frat = frat0r + frat1r * level
        freqs2 = freqs*frat
        coefficients_hpaf[:, l, : , : ] = asymmetric_compensation_coeffs(freqs2, sample_rate, b2,c2,p0,p1,p2,p3,p4)

    
    
    #noramlize for highest level
    for f, freq in enumerate(freqs):
        filter = np.concatenate([coefficients_pgc[f,:,:], coefficients_hpaf[f , -1, : , : ],coefficients_pgc[f,:,:] ], axis = 0)
        w, h = sosfreqz(filter, worN =NFFT)
        gain = np.max(np.abs(h))
        coefficients_hpaf[f , :, 0 , :3 ] /= gain
    
    # compensate final gain for sum
    all = np.zeros(NFFT)
    for f, freq in enumerate(freqs):
        all_filter = np.concatenate([coefficients_pgc[f,:,:],coefficients_hpaf[f,-1,:,:], coefficients_pgc[f,:,:]], axis = 0)
        w, h = sosfreqz(all_filter,worN = NFFT)
        all += np.abs(h) 
    
    # check this
    fft_freqs = w/np.pi*(sample_rate/2.)
    #all = all[(fft_freqs>freqs[0]) & (fft_freqs<freqs[-1])] 
    
    # this is bad because of side effect
    #dbgain_final = -np.mean(20*np.log10(all))
    
    dbgain_final = -np.max(20*np.log10(all))
    
    gain_final = 10**(dbgain_final/20.)
    
    #~ print('dbgain_final', dbgain_final)
    
    return coefficients_pgc, coefficients_hpaf, levels



def find_frat_law():
    level_max = 100.
    level_step = 10.
    levels = np.arange(0, level_max+level_step,level_step)
    
    alphas = [0, 0.25, .5, .75, 1.]
    
    
    fig1, ax1 = plt.subplots()
    frat = 0.466 + 0.0109 * levels
    ax1.plot(levels, frat, label='irino compr', color='r')
    
    
    for alpha in alphas:
        lw =(1-alpha)*3 + .5 
        
        frat = 1 + (1-alpha)*.466 - (1-alpha) * 0.0109 * levels
        label='irino inv' if alpha ==0 else None
        ax1.plot(levels, frat, label=label, color='b',  lw=lw)
        
        
        label='garcia 2015 inv' if alpha ==0 else None
        frat = 1 + (1-alpha)* 0.833 - (1-alpha) * 0.0128 * levels
        ax1.plot(levels, frat, label=label, color='g', lw=lw)
        
        
        label='garcia 2016 inv' if alpha ==0 else None
        frat = 1 + (1-alpha)*1.3333 - (1-alpha) * 0.0205 * levels
        ax1.plot(levels, frat, label=label, color='c', lw=lw)
    
    ax1.axhline(1, color='k')
    ax1.set_ylim(0,2)
    ax1.legend()
    
    ax1.set_xlabel('With alpha=0')
    ax1.set_xlabel('level dBSPL')
    ax1.set_ylabel('frat')
    
    #~ freqs = [200, 1000., 5000.]
    freqs = [1000.]
    level_max = 100.
    level_step = 10.
    levels = np.arange(0, level_max+level_step,level_step)
    sample_rate = 44100.
    
    levels_colors = [ get_cmap('jet', len(levels))(l) for l, level in enumerate(levels) ]
    freqs_colors = [ get_cmap('jet', len(freqs))(f) for f, freq in enumerate(freqs) ]
    
    fig2, ax2s = plt.subplots(ncols=3)
    fig3, ax3s = plt.subplots(ncols=3)
    
    
    def plot_in_out_gain(ax, coefficients_pgc, coefficients_hpaf, lw=1, label=''):
        for f, freq in enumerate(freqs):
            gains = np.zeros(len(levels))
            for l, level in enumerate(levels):
                print(freq, level)
                
                all_filter = np.concatenate([coefficients_pgc[f,:,:],coefficients_hpaf[f,l,:,:], coefficients_pgc[f,:,:]], axis = 0)
                w, h = hls.sosfreqz(all_filter, worN = 2**16,)
                gains[l] = np.max(20*np.log10(np.abs(h)))
                
            ax.plot(levels, levels+gains, label='{:0.1f} {}'.format(freq, label), color=freqs_colors[f], lw=lw)
        ax.plot(levels,levels, color='r', ls='--')
        ax.legend()
        ax.set_xlim(0,level_max)
        ax.set_ylim(-60.,level_max)
    
    def plot_filters(ax,  coefficients_pgc, coefficients_hpaf):
        for f, freq in enumerate(freqs):
            gains = np.zeros(len(levels))
            for l, level in enumerate(levels):
                
                all_filter = np.concatenate([coefficients_pgc[f,:,:],coefficients_hpaf[f,l,:,:], coefficients_pgc[f,:,:]], axis = 0)
                w, h = hls.sosfreqz(all_filter, worN = 2**16,)
                
                #~ hls.plot_filter(all_filter, ax, sample_rate, color=levels_colors[l])
                hls.plot_filter(coefficients_hpaf[f,l,:,:], ax, sample_rate, color=levels_colors[l])
            
            hls.plot_filter(coefficients_pgc[f,:,:], ax, sample_rate, color='k')
            ax.axvline(freq, color='k')
            
        ax.set_ylim(-50,50)
    
    
    for alpha in alphas:
        lw =(1-alpha)*3 + .5 
        
        compression_degree = [alpha] * len(freqs)
        
        coefficients_pgc, coefficients_hpaf, levels = debug_make_cgc_filter(freqs, compression_degree, level_max, level_step, sample_rate,  frat_law='irino')
        plot_in_out_gain(ax2s[0], coefficients_pgc, coefficients_hpaf, lw=lw, label='alpha={:.2f}'.format(alpha))
        plot_filters(ax3s[0],  coefficients_pgc, coefficients_hpaf)

        coefficients_pgc, coefficients_hpaf, levels = debug_make_cgc_filter(freqs, compression_degree, level_max, level_step, sample_rate,  frat_law='garcia2015')
        plot_in_out_gain(ax2s[1], coefficients_pgc, coefficients_hpaf, lw=lw, label='alpha={:.2f}'.format(alpha))
        plot_filters(ax3s[1],  coefficients_pgc, coefficients_hpaf)

        coefficients_pgc, coefficients_hpaf, levels = debug_make_cgc_filter(freqs, compression_degree, level_max, level_step, sample_rate,  frat_law='garcia2016')
        plot_in_out_gain(ax2s[2], coefficients_pgc, coefficients_hpaf, lw=lw, label='alpha={:.2f}'.format(alpha))
        plot_filters(ax3s[2],  coefficients_pgc, coefficients_hpaf)
    
    for axs in [ax2s, ax3s]:
        axs[0].set_title('irino')
        axs[1].set_title('garcia2015')
        axs[2].set_title('garcia2016')
    
    fig1.savefig('find_good_frat_law fig1.png')
    fig2.savefig('find_good_frat_law fig2.png')
    fig3.savefig('find_good_frat_law fig3.png')
    
    plt.show()






    
    
if __name__ == '__main__':
    find_frat_law()
    