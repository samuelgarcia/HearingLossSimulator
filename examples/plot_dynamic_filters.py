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
        nb_freq_band=16, low_freq = 100., hight_freq = 15000.,
        tau_level = 0.005, smooth_time = 0.0005, level_step =1., level_max = 120.,
        calibration =  93.979400086720375,
        loss_weigth = [ [(50,0.), (1000., -35), (2000., -40.), (6000., -35.), (25000,0.),]]*nb_channel,
        chunksize=512, backward_chunksize=1024,
    )

node = hls.MainProcessing()
node._configure(**params)

# hack to avoid input and output conenction
node.nb_channel = nb_channel
node.sample_rate = sample_rate
node.dtype = 'float32'
node.total_channel = node.nb_freq_band*node.nb_channel
node.make_filters()



levels_colors = [ get_cmap('jet', len(node.levels))(i) for i in range(len(node.levels)) ]
freq_colors = [ get_cmap('jet', len(node.freqs))(i) for i in range(len(node.freqs)) ]


fig1, ax1s = plt.subplots(nrows = 2, sharex = True)
fig2, ax2 = plt.subplots(nrows = 1, sharex = True)
fig3, ax3 = plt.subplots(nrows = 1, sharex = True)

for f, freq in enumerate(node.freqs):
    gain_max1 = [ ]
    gain_max2 = [ ]    
    for l, level in enumerate(node.levels):
        hpaffilter = node.coefficients_hpaf[f,l,:,:]
        #lpaffilter = node.lpaffilters[f,l,:,:]
        pgcfilter = node.coefficients_pgc[f,:,:]
        
        hls.plot_filter(hpaffilter, ax1s[1], sample_rate, label = '{}db'.format(level), color = levels_colors[l])
        
        filter1 = np.concatenate([pgcfilter, hpaffilter, pgcfilter], axis = 0)
        label = '{}db'.format(level) if f ==0 else None
        hls.plot_filter(filter1, ax1s[0], sample_rate, label = label, color = levels_colors[l])
        w, h = hls.sosfreqz(filter1, worN = 4096*4,)
        
        gain = np.max(20*np.log10(np.abs(h)))
        gain_max1.append(gain)
        ax3.plot(w/np.pi*(sample_rate/2.), 20*np.log10(h)-gain, color = levels_colors[l])
        
    gain_max1 = np.array(gain_max1)#+8.41
    print('correction', gain_max1[-1], freq)
    #gain_max1 -= gain_max1[-1]
    
    ax2.plot(node.levels, gain_max1+node.levels, label = '{}Hz'.format(freq), color = freq_colors[f])
    ax2.plot(node.levels, node.levels, ls = '--', color = 'm')

    hls.plot_filter(node.coefficients_pgc[f,:,:], ax1s[1], sample_rate, label = 'pGC', color = 'k')

    ax1s[0].axvline(freq, color = 'm')
    ax1s[1].axvline(freq, color = 'm')

ax1s[0].set_title('cGC')
ax1s[1].set_title('HP-AF and pGC')
ax1s[0].set_ylim(-35,35)
ax1s[1].set_ylim(-35,35)

ax1s[0].legend(loc ='upper right')
ax2.legend(loc ='lower right')    

plt.show()