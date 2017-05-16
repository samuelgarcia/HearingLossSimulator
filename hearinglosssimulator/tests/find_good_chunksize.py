"""
chunksize and backward_chunksize variables have a strong impact
on the quality of backward filtering.

Normally the backward stage pgc2 shoudl be done offline for the whole buffer.
For online it is done chunk by  chunksize.

For low frequency this lead to bias the result because of side effect, so the chunksize and 
backward_chunksize should be choosen carefully.

The compute the error bewteen the offline and online backward filter for some
backward_chunksize

"""

import hearinglosssimulator as hls
import numpy as np
import scipy.signal
import matplotlib.pyplot as plt




def plot_residual():

    nb_channel = 1
    sample_rate =44100.
    chunksize = 256
    #~ chunksize = 512
    #~ chunksize = 1024
    #~ chunksize = 
    #~ nloop = 200
    nloop = 200
    
    nb_freq_band=10
    
    length = int(chunksize*nloop)

    in_buffer = hls.whitenoise(length, sample_rate=sample_rate,)
    in_buffer = np.tile(in_buffer[:, None],(1, nb_channel))
    
    
    #~ lost_chunksize = np.linspace(0,1024, 5).astype(int)
    lost_chunksize = np.arange(7).astype(int) * chunksize
    
    #~ backward_chunksizes = [512,1024,1536,2048]
    #~ backward_chunksizes = [1024,1536,2048]
    #~ backward_chunksizes = np.linspace(1024,2048, 5).astype(int)
    backward_chunksizes =  lost_chunksize + chunksize
    
    
    
    all_mean_residuals = np.zeros((len(backward_chunksizes), nb_freq_band))
    all_max_residuals = np.zeros((len(backward_chunksizes), nb_freq_band))
    
    for i, backward_chunksize in enumerate(backward_chunksizes):
        print('backward_chunksize', backward_chunksize)
        loss_params = {  'left' : {'freqs' :  [125., 250., 500., 1000., 2000., 4000., 8000.],
                                            'compression_degree': [0., 0., 0., 0., 0., 0., 0.],
                                            'passive_loss_db' : [0., 0., 0., 0., 0., 0., 0.],
                                        }}
        processing_conf = dict(nb_freq_band=nb_freq_band, low_freq = 40., high_freq = 500.,
                    level_max=100, level_step=100, debug_mode=True, 
                    chunksize=chunksize, backward_chunksize=backward_chunksize, loss_params=loss_params)
        
        processing = hls.InvCGC(nb_channel=nb_channel, sample_rate=sample_rate, dtype='float32', **processing_conf)
        online_arrs = hls.run_instance_offline(processing, in_buffer, chunksize, sample_rate, dtype='float32', 
                                buffersize_margin=backward_chunksize)

        #~ processing, online_arrs = hls.run_one_class_offline(hls.InvCGC, in_buffer, chunksize, sample_rate, processing_conf=processing_conf, buffersize_margin=backward_chunksize)
    
        #~ freq_band = 2
    
        online_hpaf = online_arrs['hpaf']
        online_pgc2 = online_arrs['pgc2']
        offline_pgc2 = online_pgc2.copy()
    
        n = processing.nb_freq_band
        for b in range(n):
            offline_pgc2[:, b] = scipy.signal.sosfilt(processing.coefficients_pgc[b, :,:], online_hpaf[::-1,b])[::-1]
    
        online_pgc2 = online_pgc2[:-backward_chunksize]
        offline_pgc2 = offline_pgc2[:-backward_chunksize]
    

        residual = np.abs((online_pgc2.astype('float64')-offline_pgc2.astype('float64'))/np.mean(np.abs(offline_pgc2.astype('float64')), axis=0))
        all_mean_residuals[i, :] = np.mean(residual, axis=0)
        all_max_residuals[i, :] = np.max(residual, axis=0)
        
    
    def my_imshow(m, ax):
        im = ax.imshow(m, interpolation='nearest', 
                    origin ='lower', aspect = 'auto', cmap = 'viridis')#, extent = extent, cmap=cmap)
        im.set_clim(0,0.05)
        ax.set_xticks(np.arange(processing.freqs.size))
        ax.set_xticklabels(['{:0.0f}'.format(f) for f in processing.freqs])
        ax.set_yticks(np.arange(len(backward_chunksizes)))
        ax.set_yticklabels(['{}'.format(f) for f in lost_chunksize])
        ax.set_xlabel('freq')
        ax.set_ylabel('lost_chunksize')
        
        return im

    print(all_max_residuals)
    fig, axs = plt.subplots(nrows = 2, sharex=True)
    im1 = my_imshow(all_mean_residuals, axs[0])
    im2 = my_imshow(all_max_residuals, axs[1])
    cax = fig.add_axes([0.92 , 0.05 , .02, 0.9 ] )
    fig.colorbar(im1, ax=axs[0], cax=cax, orientation='vertical')
    
    plt.show()
    
    
    
    
    
    
    
    
    

    
if __name__ =='__main__':
    plot_residual()
    