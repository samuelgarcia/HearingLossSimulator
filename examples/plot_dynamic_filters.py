"""
This illustrate the main concept of dynamic filters depending on levels.

"""

import hearinglosssimulator as hls


params = dict(
        #~ sample_rate,
        nb_freq_band=16, low_freq = 100., hight_freq = 15000.,
        tau_level = 0.005, smooth_time = 0.0005, level_step =1., level_max = 120.,
        calibration =  93.979400086720375,
        loss_weigth = [ [(50,0.), (1000., -35), (2000., -40.), (6000., -35.), (25000,0.),]]*nb_channel,
        chunksize=512, backward_chunksize=1024,
    )

node = hls.MainProcessing()
node.configure(**params)





def plot_dynamic_filter(processing):

    levels_colors = [ get_cmap('jet', len(processing.levels))(i) for i in range(len(processing.levels)) ]
    freq_colors = [ get_cmap('jet', len(processing.freqs))(i) for i in range(len(processing.freqs)) ]


    fig1, ax1s = pyplot.subplots(nrows = 2, sharex = True)
    fig2, ax2 = pyplot.subplots(nrows = 1, sharex = True)
    fig3, ax3 = pyplot.subplots(nrows = 1, sharex = True)

    for f, freq in enumerate(processing.freqs):
        gain_max1 = [ ]
        gain_max2 = [ ]    
        for l, level in enumerate(processing.levels):
            hpaffilter = processing.hpaffilters[f,l,:,:]
            #~ lpaffilter = processing.lpaffilters[f,l,:,:]
            pgcfilter = processing.pgcfilters[f,:,:]
            
            hl.plot_filter(hpaffilter, ax1s[1], samplerate, label = '{}db'.format(level), color = levels_colors[l])
            
            filter1 = np.concatenate([pgcfilter, hpaffilter, pgcfilter], axis = 0)
            label = '{}db'.format(level) if f ==0 else None
            hl.plot_filter(filter1, ax1s[0], samplerate, label = label, color = levels_colors[l])
            w, h = hl.sosfreqz(filter1, worN = 4096*4,)
            
            gain = np.max(20*np.log10(np.abs(h)))
            gain_max1.append(gain)
            ax3.plot(w/np.pi*(samplerate/2.), 20*np.log10(h)-gain, color = levels_colors[l])
            
        gain_max1 = np.array(gain_max1)#+8.41
        print 'correction', gain_max1[-1], freq
        #~ gain_max1 -= gain_max1[-1]
        
        ax2.plot(processing.levels, gain_max1+processing.levels, label = '{}Hz'.format(freq), color = freq_colors[f])
        ax2.plot(processing.levels, processing.levels, ls = '--', color = 'm')

        hl.plot_filter(processing.pgcfilters[f,:,:], ax1s[1], samplerate, label = 'pGC', color = 'k')

        ax1s[0].axvline(freq, color = 'm')
        ax1s[1].axvline(freq, color = 'm')

    ax1s[0].set_title('cGC')
    ax1s[1].set_title('HP-AF and pGC')
    ax1s[0].set_ylim(-35,35)
    ax1s[1].set_ylim(-35,35)

    ax1s[0].legend(loc ='upper right')
    ax2.legend(loc ='lower right')    
