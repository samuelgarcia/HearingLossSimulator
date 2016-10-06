import numpy as np
import scipy.signal
import scipy.interpolate

from .filterfactory import (gammatone, asymmetric_compensation_coeffs, loggammachirp, erbspace)
from .tools import sosfreqz

NFFT = 2**16

def make_cgc_filter(freqs, compression_degree, level_max, level_step, sample_rate, dtype='float32'):
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
    
    #~ if len(loss_weigth) ==1 and nb_channel!=1:
        #~ loss_weigth = loss_weigth*nb_channel
    
    #~ assert len(loss_weigth) == nb_channel, 'The nb_channel given in loss_weight is not nb_channel {} {}'.format(len(loss_weigth), nb_channel)
    
    #~ total_channel = nb_freq_band*nb_channel
    #~ freqs = erbspace(low_freq,hight_freq, nb_freq_band)
    
    # compute losses at ERB freq
    #~ losses = [ ]
    #~ for c in range(nb_channel):
        #~ lw = loss_weigth[c]
        #~ lw = [(0,0)]+lw + [(sample_rate/2, 0.)]
        #~ loss_freq, loss_db = np.array(lw).T
        #~ interp = scipy.interpolate.interp1d(loss_freq, loss_db)
        #~ losses.append(interp(freqs))
    #~ losses = np.array(losses)
    
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
    
    frat0 = 0.466
    frat1 = 0.0109
    frat1r = 0.016
    Pcr = 65.
    frat0r = frat0 + (frat1 - frat1r)*Pcr
    
    print(frat0r)
    print(frat1r)
    for l, level in enumerate(levels):
        frat = frat0r +(1-alpha) * frat1r * level # minus for inverse compression = moving left
        
        freqs2 = freqs*frat
        print()
        print(level)
        print(freq)
        print(frat)
        print(freqs2)
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
    
    print('dbgain_final', dbgain_final)
    
    return coefficients_pgc, coefficients_hpaf, levels