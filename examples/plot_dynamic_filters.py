"""
This illustrate the main concept of dynamic filters depending on levels.

"""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.cm import get_cmap

import hearinglosssimulator as hls

nb_channel=1
sample_rate = 44100.
level_max = 100.
level_step = 10.


freqs = [300., 1000., 4000., ]


# No compression loss
#compression_degree = [1]*len(freqs)

# Full compression loss
compression_degree = [0]*len(freqs)


coefficients_pgc, coefficients_hpaf, levels, band_overlap_gain = hls.make_cgc_filter(freqs, compression_degree, level_max, level_step, sample_rate)

fig1, ax1 = plt.subplots()
fig2, ax2 = plt.subplots()
fig3, ax3 = plt.subplots()

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
    
    hls.plot_filter(coefficients_pgc[f,:,:], ax3, sample_rate, color='k', lw=2)
    ax3.axvline(freq, color='k')
    ax2.axvline(freq, color='k')
    
    ax1.plot(levels, levels+gains, label='{:0.1f}'.format(freq), color=freqs_colors[f])
ax1.plot(levels,levels, color='r', ls='--')
    
    
ax1.legend()
ax1.set_xlabel('input level (dB SPL)')
ax1.set_ylabel('output level (dB SPL)')

for ax in [ax2, ax3]:
    ax.set_xlabel('freq (Hz)')
    ax.set_ylabel('filter gain (dB)')
    ax.set_xlim(0., 5000.)
    ax.set_ylim(-70,20)

#~ fig1.savefig('input_output_gain.png')
#~ fig3.savefig('filter_pgc_and_hpaf.png')
#~ fig2.savefig('filter_cgc.png')

plt.show()