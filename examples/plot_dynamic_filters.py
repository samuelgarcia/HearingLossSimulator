"""
This illustrate the main concept of dynamic filters depending on levels.

"""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.cm import get_cmap

import hearinglosssimulator as hls

nb_channel=1
sample_rate = 44100.

params = dict(
        #~ sample_rate,
        nb_freq_band=8, low_freq = 100., hight_freq = 15000.,
        tau_level = 0.005, smooth_time = 0.0005, level_step =4., level_max = 120.,
        calibration =  93.979400086720375,
        #~ loss_weigth = [ [(50,0.), (1000., -35), (2000., -40.), (6000., -35.), (25000,0.),]]*nb_channel,
        loss_weigth = [ [(50,0.), (100., -35), (15000., -35.), (25000,0.),]]*nb_channel,
        
        chunksize=512, backward_chunksize=1024,
    )

processing = hls.InvCGC(nb_channel=nb_channel, sample_rate=sample_rate, dtype='float32', apply_configuration_at_init=False)
processing.configure(**params)

processing.make_filters()



levels_colors = [ get_cmap('jet', len(processing.levels))(i) for i in range(len(processing.levels)) ]
freq_colors = [ get_cmap('jet', len(processing.freqs))(i) for i in range(len(processing.freqs)) ]


fig1, ax1s = plt.subplots(nrows = 2, sharex = True)
fig2, ax2 = plt.subplots(nrows = 1, sharex = True)
fig3, ax3 = plt.subplots(nrows = 1, sharex = True)

for f, freq in enumerate(processing.freqs):
    gain_by_level = [ ]
    for l, level in enumerate(processing.levels):
        hpaffilter = processing.coefficients_hpaf[f,l,:,:]
        #lpaffilter = processing.lpaffilters[f,l,:,:]
        pgcfilter = processing.coefficients_pgc[f,:,:]
        
        hls.plot_filter(hpaffilter, ax1s[1], sample_rate, label = '{}db'.format(level), color = levels_colors[l])
        
        filter1 = np.concatenate([pgcfilter, hpaffilter, pgcfilter], axis = 0)
        label = '{}db'.format(level) if f ==0 else None
        hls.plot_filter(filter1, ax1s[0], sample_rate, label = label, color = levels_colors[l])
        w, h = hls.sosfreqz(filter1, worN = 4096*4,)
        
        gain = np.max(20*np.log10(np.abs(h)))
        gain_by_level.append(gain)
        ax3.plot(w/np.pi*(sample_rate/2.), 20*np.log10(h)-gain, color = levels_colors[l])
        
    gain_by_level = np.array(gain_by_level)
    
    ax2.plot(processing.levels, gain_by_level+processing.levels, label = '{}Hz'.format(freq), color = freq_colors[f])
    ax2.plot(processing.levels, processing.levels, ls = '--', color = 'm')

    hls.plot_filter(processing.coefficients_pgc[f,:,:], ax1s[1], sample_rate, label = 'pGC', color = 'k')

    ax1s[0].axvline(freq, color = 'm')
    ax1s[1].axvline(freq, color = 'm')

ax1s[0].set_title('cGC')
ax1s[1].set_title('HP-AF and pGC')
ax1s[0].set_ylim(-35,35)
ax1s[1].set_ylim(-35,35)

ax1s[0].legend(loc ='upper right')
ax2.legend(loc ='lower right')    

plt.show()