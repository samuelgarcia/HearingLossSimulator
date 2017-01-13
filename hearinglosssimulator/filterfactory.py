"""
This tools copied from biean.hearing and aim for creating filters coefficient.

Unilike biran cascade of filter are represented like matlab sosfilter and scipy (>0.15) sos filter:
dim = (ncascade x 6) = (ncascade x [b0, b1, b2, a0, a1, a2])

In case of multiple channel the filter is 
dim = (nchannel x ncascade x 6) = (nchannel x ncascade x [b0, b1, b2, a0, a1, a2])


All function are from brian.hear (and from aim-mat)


"""

import numpy as np
from numpy import exp, cos, sin, pi, sqrt #abs, sum


def gammatone(freqs, sample_rate, b=1.019, erb_order=1, ear_Q=9.26449, min_bw=24.7,):
    cf = freqs = np.asarray(freqs)
    T = 1./sample_rate
    
    erb = ((cf/ear_Q)**erb_order + min_bw**erb_order)**(1/erb_order)
    #~ print erb
    B = b*2*pi*erb
#        B = 2*pi*b
    #~ B = B.astype('float128')
    #~ print('B', type(B), B.dtype)
    #~ print('T', type(T))
    #~ print('2*B*T', type(2*B*T), (2*B*T).dtype)
    #~ print('2*B*T', 2*B*T)
    #~ T = np.float64(T)
    #~ B = float(B)
    #~ i=1j
    #~ print('yep1')
    #~ yep1 = exp(2*B*T)
    #~ print('yep2')
    #~ yep2 = exp(4*i*cf*pi*T)
    #~ print('hooooo')
    
    
    
    i=1j
    gain=abs((-2*exp(4*i*cf*pi*T)*T+2*exp(-(B*T)+2*i*cf*pi*T)*T*(cos(2*cf*pi*T)-sqrt(3-2**(3./2))*sin(2*cf*pi*T)))*(-2*exp(4*i*cf*pi*T)*T+\
                        2*exp(-(B*T)+2*i*cf*pi*T)*T*(cos(2*cf*pi*T)+sqrt(3-2**(3./2))*sin(2*cf*pi*T)))*(-2*exp(4*i*cf*pi*T)*T+\
                        2*exp(-(B*T)+2*i*cf*pi*T)*T*(cos(2*cf*pi*T)-\
                        sqrt(3+2**(3./2))*sin(2*cf*pi*T)))*(-2*exp(4*i*cf*pi*T)*T+2*exp(-(B*T)+2*i*cf*pi*T)*T*(cos(2*cf*pi*T)+\
                        sqrt(3+2**(3./2))*sin(2*cf*pi*T)))/(-2/exp(2*B*T)-2*exp(4*i*cf*pi*T)+\
                        2*(1+exp(4*i*cf*pi*T))/exp(B*T))**4)

    B1 = -2*cos(2*cf*pi*T)/exp(B*T)
    B2 = exp(-2*B*T)
    
    coeff = np.zeros((len(freqs), 4, 6))
    coeff[:, 0, 0] = T/gain
    coeff[:, 1:, 0] = T
    coeff[:, 0, 1] = -(2*T*cos(2*cf*pi*T)/exp(B*T) + 2*sqrt(3+2**1.5)*T*sin(2*cf*pi*T) / exp(B*T))/2/gain
    coeff[:, 1, 1] = -(2*T*cos(2*cf*pi*T)/exp(B*T)-2*sqrt(3+2**1.5)*T*sin(2*cf*pi*T)/exp(B*T))/2
    coeff[:, 2, 1] = -(2*T*cos(2*cf*pi*T)/exp(B*T)+2*sqrt(3-2**1.5)*T*sin(2*cf*pi*T)/exp(B*T))/2
    coeff[:, 3, 1] = -(2*T*cos(2*cf*pi*T)/exp(B*T)-2*sqrt(3-2**1.5)*T*sin(2*cf*pi*T)/exp(B*T))/2
    coeff[:, :, 2] = 0.
    coeff[:, :, 3] = 1.
    coeff[:, :, 4] = B1[:, None]
    coeff[:, :, 5] = B2[:, None]
    
    return coeff
    

def asymmetric_compensation_coeffs(freqs, sample_rate,b,c,p0,p1,p2,p3,p4, ncascade=4):
    freqs = np.asarray(freqs)
    ERBw=24.7*(4.37e-3*freqs+1.)
    coeff = np.zeros((len(freqs), ncascade, 6))
    for k in range(ncascade):
        r=exp(-p1*(p0/p4)**(k)*2*pi*b*ERBw/sample_rate) #k instead of k-1 because range 0 N-1
        Dfr=(p0*p4)**(k)*p2*c*b*ERBw
        phi=2*pi*np.maximum((freqs+Dfr), 0)/sample_rate
        psy=2*pi*np.maximum((freqs-Dfr), 0)/sample_rate
        ap=np.vstack((np.ones(r.shape),-2*r*cos(phi), r**2)).T
        bz=np.vstack((np.ones(r.shape),-2*r*cos(psy), r**2)).T
        vwr=exp(1j*2*pi*freqs/sample_rate)
        vwrs=np.vstack((np.ones(vwr.shape), vwr, vwr**2)).T
        ##normilization stuff
        nrm=abs(np.sum(vwrs*ap, 1)/np.sum(vwrs*bz, 1))
        bz=bz*np.tile(nrm,[3,1]).T
        
        coeff[:,k,:3] = bz
        coeff[:,k,3:] = ap

    return coeff



def loggammachirp(freqs, sample_rate, b=1.019, c=1, ncascade_asym_comp=4):
    """
    A gammatone and lpfilter in cascade.
    """
    coeff0 = gammatone(freqs, sample_rate,b)
    p0=2
    p1=1.7818*(1-0.0791*b)*(1-0.1655*abs(c))
    p2=0.5689*(1-0.1620*b)*(1-0.0857*abs(c))
    p3=0.2523*(1-0.0244*b)*(1+0.0574*abs(c))
    p4=1.0724
    coeff1 = asymmetric_compensation_coeffs(freqs, sample_rate, b, c, p0, p1, p2, p3, p4, ncascade = ncascade_asym_comp)
    coeff = np.concatenate([ coeff0, coeff1], axis = 1)

    return coeff



def erbspace(low, high, N, earQ=9.26449, minBW=24.7, order=1):
    '''
    This a copy/paste from brian
    
    Returns the centre frequencies on an ERB scale.
    
    ``low``, ``high``
        Lower and upper frequencies
    ``N``
        Number of channels
    ``earQ=9.26449``, ``minBW=24.7``, ``order=1``
        Default Glasberg and Moore parameters.
    '''
    low = float(low)
    high = float(high)
    cf = -(earQ * minBW) + exp((np.arange(N)) * (-np.log(high + earQ * minBW) + \
            np.log(low + earQ * minBW)) / (N-1)) * (high + earQ * minBW)
    cf = cf[::-1]
    return cf

