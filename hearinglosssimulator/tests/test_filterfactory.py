import pytest
import hearinglosssimulator as hls
import numpy as np


def apply_and_plot(func, *args, **kargs):
    #~ from tools import sosfreqz
    from matplotlib import pyplot
    freqs = [ 1000.]
    #~ freqs = [  200., 1000.,  5000. ]
    #~ freqs = [  200.,  758.18944907,  2042.9450242,   5000.        ]
    sample_rate = 44100.
    
    coeff = func(freqs, sample_rate,*args, **kargs)
    
    fig, ax = pyplot.subplots()
    for f, freq in enumerate(freqs):
        w, h = hls.sosfreqz(coeff[f,:,:], worN = 4096*10)
        ax.plot(w,20*np.log10(h), label = '{}Hz'.format(freq))
    ax.set_ylim(-30,10)
    pyplot.show()



def test_gammatone():
    b1=1.81
    apply_and_plot(hls.gammatone, b = b1)

def test_asymmetric_compensation_coeffs():
    b = 1.81
    c = -2.96
    p0=2
    p1=1.7818*(1-0.0791*b)*(1-0.1655*abs(c))
    p2=0.5689*(1-0.1620*b)*(1-0.0857*abs(c))
    p3=0.2523*(1-0.0244*b)*(1+0.0574*abs(c))
    p4=1.0724
    apply_and_plot(hls.asymmetric_compensation_coeffs, b,c,p0,p1,p2,p3,p4, ncascade=4)
    
    
    #~ b2 = 2.17
    #~ c2 = 2.2
    #~ p0=2
    #~ p1=1.7818*(1-0.0791*b2)*(1-0.1655*abs(c2))
    #~ p2=0.5689*(1-0.1620*b2)*(1-0.0857*abs(c2))
    #~ p3=0.2523*(1-0.0244*b2)*(1+0.0574*abs(c2))
    #~ p4=1.0724    
    
    #~ apply_and_plot(hls.asymmetric_compensation_coeffs, b2,c2,p0,p1,p2,p3,p4, ncascade=4)




def test_loggammachirp():
    b1 = 1.81
    c1 = -2.96
    apply_and_plot(hls.loggammachirp,  b = b1, c = c1)


def test_erbspace():
    freqs = hls.erbspace(200., 5000., 4)
    print(freqs)
    ERBw=24.7*(4.37e-3*freqs+1.)
    print(ERBw)
    erb_order=1
    ear_Q=9.26449
    min_bw=24.7
    erb = ((freqs/ear_Q)**erb_order + min_bw**erb_order)**(1/erb_order)
    print(erb)

if __name__ == '__main__':
    #~ test_gammatone()
    test_asymmetric_compensation_coeffs()
    #~ test_loggammachirp()
    #~ test_erbspace()
