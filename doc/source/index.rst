HearingLossSimulator
======================

Near real time hearing loss simulator in python based on Compressive Gammachirp. 


Documentation:
   http://hearinglosssimulator.readthedocs.io/

Source code repository and issue tracker:
   https://github.com/samuelgarcia/HearingLossSimulator/

Python Package Index:
    Not done...
    
License:
   MIT -- see the file ``LICENSE`` for details.


Overview
--------

The concept of *Compressive Gammachirp* is from Toshio Irino, Roy Patterson et al.

This code derive from original matlab code of Toshio Irino.
Is is not an exact port but it is very similar.

The 2 goals of the actual recoding was:
  * to make the algorithm near real time.
  * to get an opensource version.

The aim of this module is to simulate an hearing impairement to:
  * demonstrate to normal listeners what a hearing loss is
  * run experimental protocols with a fake hearing loss


It can be used:
  * offline in python script for testing the algorithm.
  * online (on close loop on the audio device).

The algorithm simulate both outer hair cell (OHC) loss and  inner hair cells (IHC) loss.
The OHC loss is simulated by a deficit in compression and IHC loss with a passive loss.



Requirements
------------

**Python 3 scientific stack**:
    Of course you need python and the classical scientific stack.
    You need at least python 3.5.
        
    On linux, you can get it is often already installed.
    On debian/unbuntu/mint::
        
        sudo apt-get python3 python3-numpy python3-scipy python3-pyopencl
        pip3 install sounddevice
        
    On other platform, the easiest convinient way is to install anaconda_ python distribution.
    Choose python 3.5 (or more), and then::
        
        conda install numpy scipy pyopencl sounddevice

**OpenCL**:
    OpenCL, the GPU language progamming. The central part of the simulator is done
    with OpenCL. While OpenCL is an open implementation, OpenCL drivers by themself
    are not opensource. You need to install OpenCL driver of your GPU device (and sometime
    the opencl sdk) manually.
    GPU manufacturer provide these drivers:
      * Nvidia : https://developer.nvidia.com/opencl
      * AMD: http://support.amd.com/en-us/kb-articles/Pages/OpenCL2-Driver.aspx
      * Intel : https://software.intel.com/en-us/intel-opencl
    
    You will that for some of GPU vendors you need to give some personal
    information about you before downloading drivers. It can provoke irritating
    feeling.


**For the GUI**:
    For using the GUI you also need:
        * PyQt5
        * pyqtgraph
        * matplotlib.
        
    In terminal::
        
        sudo apt-get python3-pyqt5 python3-matplotlib
        pip3 install pyqtgraph
        
    Or::
        
        conda install python3-pyqt5 python3-matplotlib pyqtgraph

**For read/write wavefile**:
    For playing with wav file you need soundfile_::
    
        pip3 install soundfile
    
    Or::
    
        conda install soundfile
    

.. _anaconda: https://www.continuum.io/downloads/
.. _soundfile: http://pysoundfile.readthedocs.io/


Installation
------------

When all requirements are installed you are almost done!!

hearinglosssimulator is work in progrees so you must install github version,
there is no python packge yet::

    git clone https://github.com/samuelgarcia/HearingLossSimulator.git
    cd HearingLossSimulator
    python setup.py install 

.. warning::
    On actual ubuntu/debian python is python2 so you need to change all python by python3.



Start GUI
---------
    
To start the main GUI::

    python start_online_hearingloss.py

On some windows installation, you can also double click on the *start_online_hearingloss.py*.

You should see this:

.. image:: img/screenshot.png

Algorithm principle
-------------------

Toshio Irino and Roy Pattersonet al. are main inventor of the hearing loss simulator based on the compressive gammachirp model.

For more detail you should read at leat these references:
  * A dynamic compressive gammachirp auditory filterbank : Irino,T. and and Patterson,R.D. : IEEE Trans.ASLP, Vol.14, Nov.2006.
  * Accurate Estimation of Compression in Simultaneous Masking Enables the Simulation of Hearing Impairment for Normal-Hearing Listeners : Irino T, Fukawatase T, Sakaguchi M, Nisimura R, Kawahara H, Patterson RD : Adv Exp Med Biol. 2013
  * Hearing impairment simulator based on compressive gammachirp filter : Misaki Nagae, Toshio Irino, Ryuich Nisimura, Hideki Kawahara, Roy D Patterson : Signal and Information Processing Association Annual Summit and Conference (APSIPA), 2014 Asia-Pacific

.. note:: The orignal algorithm has evoluted along the last decade. The actual python/opencl version is a mixed of one of them!

.. note:: The very last version of Toshio Irino is now based on minimum phase filter for the synthesis part (the level estimation  part remian the same as before) : this is not yet ported in python/opencl.


The main processing diagram is the following:

.. image:: img/processing_diagram.png

Steps:
  1. **PGC1** : The input sound is filtered by a bank of N passive gammachirp filter. N is tipycally 32.
  2. **Level estimation** : The instantaneous level is estimated in dB for each band. Sample by sample.
  3. **HP-AF** : A Highpass filter filter where the central frequency is dynamically controled by level.
  4. **PGC2** : Time reversal passive gammachirp. Identical to **PGC1**. The is for phase regulation in between bands. This induced a delay for realtime.
  5. **passive gain** : a passive gain for each band.
  6. **sum** : sum all bands for resynthesis.


Steps 1, 2, 3, 4:  togother are the inverse compressive gammachrip (**InvCGC**). This model the outer hair cell (OHC) impairement by cancelling the natural compression.

Step 5: This model inner hair cells (IHC) loss with a static gain.


As example here the 1000 Hz band

The PGC filter (in black) and HP-AF (color) levelled controled frequency repsonse.
Blue are low levels and red high levels.
Note that the **HP-AF** is moving from left (low, blue) to right (high, red).

.. image:: img/filter_pgc_and_hpaf.png

The sum of the PGC1 + HP-AF + PGC2 is the InvCGC (Inverse Compressive Gammachirp).
Blue are low levels and red high levels.
Note that for low level there is a negative gain. For high level, the gain tend to zero dB:

.. image:: img/filter_cgc.png

Here the input/output inverse compressive gammachrip. So it is an expander.

.. image:: img/input_output_gain.png



Algorithm parameters
--------------------



.. automethod:: hearinglosssimulator.invcgc.InvCGC.__init__()
.. automethod:: hearinglosssimulator.invcgc.InvCGC.configure()


Calibration
-----------




Implementation details
----------------------

  * All filters bank are compute on time domain. So there is no window/overlap/add.
    All processing are done sample by sample, even level estimation.
  * Practically, processing are applied on chunk (typically 512 samples) but
    thre is no border effect since filters state are kept for next chunk. So chunksize
    do not affect the processing (only latency).
  * Filter are all biquadratic (more stable) = SOS (second order section)
  * Implementation of SOS is done with `form II`_.
  * number of sections: 8 (PGC1) + 4 (dynamic HP-AF) + 8 (PGC2)
  * backward proccsing for PGC2 (time reversal) filter induce a delay.
    *delay=backward_chunksize-chunksize*. backward_chunksize affect the processing.
    If it is too small, it lead to distrotion in low frequencies.
  * All HP-AF filters a precomputed for each band and each levels before running.
    Filter coefficient are not computed on the fly.
  * Python/scipy is used for computing each filter (easy to debug)
  * OpenCl is used for applying filters (faster)
  * N sections for each channel are more or less computed in parralel.
    
    
.. _`form II` : https://en.wikipedia.org/wiki/Digital_biquad_filter#Direct_form_2



GUI
---


Examples
--------

:doc:`examples`



API Documentation
-----------------

    
