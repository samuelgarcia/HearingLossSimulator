import numpy as np
import scipy.signal
import scipy.interpolate
import matplotlib.pyplot as plt

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
    
    returns
    ---
        
        coefficients_pgc: sos coefficient of pgc filters shape is (freqs.size, 8, 6)
        
        coefficients_hpaf: sos coefficient of hpaf (level dependant). Filter shape is
            (freqs.size, levels.size, 4, 6)
        
        levels: vector of levels.
        
        band_overlap_gain: gain for conpensating the overlap between bands. this depend
          the number of band
        
    
    
    
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
    #pcg_freqs = np.zeros_like(freqs)  #for testing
    for f, freq in enumerate(freqs):
        w, h = sosfreqz(coefficients_pgc[f,:,:], worN =2**16,)
        gain = np.max(np.abs(h))
        coefficients_pgc[f,0, :3] /= gain
        #pcg_freqs[f] = (w/np.pi*(sample_rate/2.))[np.argmax(np.abs(h))] #for testing
    
    # Construct hpaf filters : pre compute for all sound levels for each freq
    levels = np.arange(0, level_max+level_step,level_step)
    nlevel = levels.size
    
    # construct hpaf depending on compression_degree for each freq
    coefficients_hpaf = np.zeros((nb_freq_band, len(levels), 4, 6), dtype = dtype)
        
    alpha = compression_degree
    
    # Toshio Irino coefficient (if this is correct)
    # need to be check with irino
    frat0r = 1 + 0.466 * (1-alpha)
    frat1r =  - 0.0109 * (1-alpha)
    
    # Samuel Garcia coefficient 2015
    #~ w = (1-alpha) * 5 / 3
    #~ frat1r = -w/65/2.
    #~ frat0r = 1+w/2.

    # Samuel Garcia coefficient 2016
    #~ frat0r = 1 + (1-alpha)*1.3333
    #~ frat1r = - (1-alpha) * 0.0205
    
    for l, level in enumerate(levels):
        # minus for inverse compression = moving left
        frat = frat0r + frat1r * level
        freqs2 = freqs*frat
        #freqs2 = pcg_freqs*frat #for testing
        coefficients_hpaf[:, l, : , : ] = asymmetric_compensation_coeffs(freqs2, sample_rate, b2,c2,p0,p1,p2,p3,p4)
    
    #noramlize for highest level
    for f, freq in enumerate(freqs):
        #~ print('freq', freq)
        filter = np.concatenate([coefficients_pgc[f,:,:], coefficients_hpaf[f , -1, : , : ],coefficients_pgc[f,:,:] ], axis = 0)
        w, h = sosfreqz(filter, worN =NFFT)
        gain = np.max(np.abs(h))
        coefficients_hpaf[f , :, 0 , :3 ] /= gain
    
    # compensate final gain of sum of all band freqs
    all = np.zeros(NFFT)
    for f, freq in enumerate(freqs):
        #~ print('freq', freq)
        all_filter = np.concatenate([coefficients_pgc[f,:,:],coefficients_hpaf[f,-1,:,:], coefficients_pgc[f,:,:]], axis = 0)
        w, h = sosfreqz(all_filter,worN = NFFT)
        all += np.abs(h) 
    
    # check this
    fft_freqs = w/np.pi*(sample_rate/2.)
    #all = all[(fft_freqs>freqs[0]) & (fft_freqs<freqs[-1])] 
    
    # this is bad because of side effect
    #dbgain_final = -np.mean(20*np.log10(all))
    
    band_overlap_gain_db = -np.max(20*np.log10(all))
    
    band_overlap_gain = 10**(band_overlap_gain_db/20.)
    
    #~ print('band_overlap_gain_db', band_overlap_gain_db)
    
    return coefficients_pgc, coefficients_hpaf, levels, band_overlap_gain


def make_invcomp_filter(freqs, compression_degree, level_max, level_step, sample_rate, dtype='float32'):
    """
    Similar than make_cgc_filter except coefficients_hpaf is replace by gain_controlled.
    
    Used by the class InvComp.
    
    parameters
    ----
    
    freqs: vector of central freqquencies Hz
    
    compression_degree: vector of compression degree for each freq with:
        * 1=no compression impairement
        * 0= maximum compression impairement
    
    returns
    ---
        
        coefficients_pgc: sos coefficient of pgc filters shape is (freqs.size, 8, 6)
        
        gain_controlled: gain level dependant. Filter shape is (freqs.size, levels.size)
        
        levels: vector of levels.
        
        band_overlap_gain: gain for conpensating the overlap between bands. this depend
          the number of band

    Note that  for computing gain_controlled we use the same dynamic that InvCGC.
    So internally HPAF is computed to extract the equivalent gain level controlled.
    Also note than this HPAF is alwas done at 1000Hz because the gain response is
    better in the middle of the spectrum.

    
    """
    freqs = np.asarray(freqs)
    compression_degree = np.asarray(compression_degree)
    assert np.all((compression_degree>=0.) & (compression_degree<=1.)), 'compression degree must in 0-1 range'
    
    
    
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
    #pcg_freqs = np.zeros_like(freqs)  #for testing
    for f, freq in enumerate(freqs):
        w, h = sosfreqz(coefficients_pgc[f,:,:], worN =2**16,)
        gain = np.max(np.abs(h))
        coefficients_pgc[f,0, :3] /= gain
        #pcg_freqs[f] = (w/np.pi*(sample_rate/2.))[np.argmax(np.abs(h))] #for testing
    
    # Construct hpaf filters : pre compute for all sound levels for each freq
    levels = np.arange(0, level_max+level_step,level_step)
    nlevel = levels.size
    
    # construct hpaf depending on compression_degree for each freq
    
        
    #for efficieny we compute only once each compression_degree for deifferent bands
    _freqs = np.array([1000.])
    pgc_1000Hz = loggammachirp(_freqs, sample_rate, b=b1, c=c1).astype(dtype)
    pgc_1000Hz = pgc_1000Hz[0,:,:]
    
    w, h = sosfreqz(pgc_1000Hz, worN =2**16,)
    gain = np.max(np.abs(h))
    pgc_1000Hz[0, :3] /= gain
    hpaf_1000Hz = np.zeros((len(levels), 4, 6), dtype = dtype)
    gain_controlled_by_alpha = {}
    #~ print('all alpha', np.unique(compression_degree))
    for alpha in np.unique(compression_degree):
        print('alpha', alpha)
        # Toshio Irino coefficient (if this is correct)
        # need to be check with irino
        frat0r = 1 + 0.466 * (1-alpha)
        frat1r =  - 0.0109 * (1-alpha)
        
        for l, level in enumerate(levels):
            print('level', level)
            # minus for inverse compression = moving left
            frat = frat0r + frat1r * level
            freqs2 = _freqs*frat
            #freqs2 = pcg_freqs*frat #for testing
            hpaf_1000Hz[l,:,:] = asymmetric_compensation_coeffs(freqs2, sample_rate, b2,c2,p0,p1,p2,p3,p4)
        
        #noramlize for highest level
        filter = np.concatenate([pgc_1000Hz, hpaf_1000Hz[-1, : , : ],pgc_1000Hz], axis = 0)
        w, h = sosfreqz(filter, worN =NFFT)
        gain = np.max(np.abs(h))
        hpaf_1000Hz[:, 0 , :3 ] /= gain
        
        gains = np.zeros(len(levels))
        for l, level in enumerate(levels):
            print('level', level)
            filter = np.concatenate([pgc_1000Hz, hpaf_1000Hz[l, : , : ],pgc_1000Hz], axis = 0)
            w, h = sosfreqz(filter, worN =NFFT)
            #~ gains[l] = np.max(20*np.log10(np.abs(h)))
            gains[l] = np.max(np.abs(h))
        gain_controlled_by_alpha[alpha] = gains
    
    
    
    
    #~ alpha = compression_degree
    
    
    # Samuel Garcia coefficient 2015
    #~ w = (1-alpha) * 5 / 3
    #~ frat1r = -w/65/2.
    #~ frat0r = 1+w/2.

    # Samuel Garcia coefficient 2016
    #~ frat0r = 1 + (1-alpha)*1.3333
    #~ frat1r = - (1-alpha) * 0.0205
    
    #~ for l, level in enumerate(levels):
        # minus for inverse compression = moving left
        #~ frat = frat0r + frat1r * level
        #~ freqs2 = freqs*frat
        #freqs2 = pcg_freqs*frat #for testing
        #~ coefficients_hpaf[:, l, : , : ] = asymmetric_compensation_coeffs(freqs2, sample_rate, b2,c2,p0,p1,p2,p3,p4)
    
    #noramlize for highest level
    #~ for f, freq in enumerate(freqs):
        #~ filter = np.concatenate([coefficients_pgc[f,:,:], coefficients_hpaf[f , -1, : , : ],coefficients_pgc[f,:,:] ], axis = 0)
        #~ w, h = sosfreqz(filter, worN =NFFT)
        #~ gain = np.max(np.abs(h))
        #~ coefficients_hpaf[f , :, 0 , :3 ] /= gain
    
    gain_controlled = np.zeros((freqs.size, levels.size), dtype=dtype)
    for f, freq in enumerate(freqs):
        alpha = compression_degree[f]
        gain_controlled[f, :] = gain_controlled_by_alpha[alpha]
    
    # compensate final gain of sum of all band freqs
    all = np.zeros(NFFT)
    for f, freq in enumerate(freqs):
        all_filter = np.concatenate([coefficients_pgc[f,:,:], coefficients_pgc[f,:,:]], axis = 0)
        w, h = sosfreqz(all_filter,worN = NFFT)
        all += np.abs(h) 
    
    # check this
    fft_freqs = w/np.pi*(sample_rate/2.)
    #all = all[(fft_freqs>freqs[0]) & (fft_freqs<freqs[-1])] 
    
    
    # this is bad because of side effect
    #dbgain_final = -np.mean(20*np.log10(all))
    
    band_overlap_gain_db = -np.max(20*np.log10(all))
    
    band_overlap_gain = 10**(band_overlap_gain_db/20.)
    
    #~ print('band_overlap_gain_db', band_overlap_gain_db)
    #~ print('band_overlap_gain', band_overlap_gain)
    #~ fig, ax = plt.subplots()
    #~ ax.plot(fft_freqs, all)
    #~ fig, ax = plt.subplots()
    #~ ax.plot(fft_freqs, 20*np.log10(all))
    #~ plt.show()

    return coefficients_pgc, gain_controlled, levels, band_overlap_gain


