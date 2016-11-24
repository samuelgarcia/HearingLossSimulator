HearingLossSimulator
======================

Near real time hearing loss simulator in python based on an Inverse Compressive Gammachirp. 


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

The original idea of the *Inverse Compressive Gammachirp* has been developed
by Toshio Irino, Roy Patterson et al.

This code is a transcription in Python of an original matlab code of Toshio Irino.
It is not an exact port but it is very similar.

The 2 main objectives of the actual recoding was:
  * to make the algorithm near real time.
  * to get an opensource version.

The aim of this module is to simulate an hearing impairement to:
  * demonstrate to normal listeners what a hearing loss is 
  * be used as a tool for sound designers to take into account hearing impairment
  * run experimental protocols with a simulated and controled hearing loss


It can be used:
  * offline in python script for testing the algorithm.
  * online (on close loop on the audio device).

The algorithm simulates both outer hair cell (OHC) loss and  inner hair cells (IHC) loss.
The OHC loss is simulated by a deficit in compression and IHC loss with a passive loss.



Requirements
------------

**Python 3 scientific stack**:
    Of course you need python and the classical scientific stack.
    You need at least python 3.5.
        
    On linux, you can get it is often already installed.
    On debian/unbuntu/mint::
        
        sudo apt-get install python3 python3-pip  python3-numpy python3-scipy python3-pyopencl python3-cffi
        sudo pip3 install sounddevice
        
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
    
    For some GPU manufacturers you will need to give some personal
    information about you before downloading drivers. Be aware that
    this can provoke very bad feeling.
    
    For some ubuntu distribution if you have nvidia search for package like::
    
        sudo apt-get install nvidia-opencl-icd-XXX
    
    
    For testing if you have opencl working lanch python3 and test this
    if the prompt propose or give a context related to your harware
    you are lucky!!::
    
        import pyopencl
        pyopencl.create_some_context()
        


**For the GUI**:
    For using the GUI you also need:
        * PyQt5
        * pyqtgraph
        * matplotlib.
        
    In terminal::
        
        sudo apt-get install python3-pyqt5 python3-matplotlib
        sudo pip3 install pyqtgraph
        
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

hearinglosssimulator project is still in progress so you must install github version,
there is no python packge yet::
    
    sudo apt-get install git
    git clone https://github.com/samuelgarcia/HearingLossSimulator.git
    cd HearingLossSimulator
    python3 setup.py install --user

.. warning::
    On actual ubuntu/debian python is python2 so you need python3.
    On other distro check if python is python3 or python2 and adapt this procedure.

    
Test it in python3::

    import hearinglosssimulator



Algorithm principle
-------------------

Toshio Irino and Roy Patterson et al. are the main contributors of the hearing loss simulator based on the compressive gammachirp model.

For more detail you should read at leat these references:
  * A dynamic compressive gammachirp auditory filterbank : Irino,T. and and Patterson,R.D. : IEEE Trans.ASLP, Vol.14, Nov.2006.
  * Accurate Estimation of Compression in Simultaneous Masking Enables the Simulation of Hearing Impairment for Normal-Hearing Listeners : Irino T, Fukawatase T, Sakaguchi M, Nisimura R, Kawahara H, Patterson RD : Adv Exp Med Biol. 2013
  * Hearing impairment simulator based on compressive gammachirp filter : Misaki Nagae, Toshio Irino, Ryuich Nisimura, Hideki Kawahara, Roy D Patterson : Signal and Information Processing Association Annual Summit and Conference (APSIPA), 2014 Asia-Pacific

.. note:: The orignal algorithm has evoluted along the last decade.
    The actual python/opencl version is a mixed of some of them!

.. note:: The very last version of Toshio Irino is now based on minimum phase filter for the synthesis part
    (the level estimation  part remains the same as before) : this has not been ported in python/opencl.


The main processing diagram is the following:

.. image:: img/processing_diagram.png

Steps:
  1. **PGC1** : The input sound is filtered by a bank of N passive gammachirp filter. N is typically 32.
  2. **Level estimation** : The instantaneous level is estimated in dB for each band. Sample by sample.
  3. **HP-AF** : A Highpass filter where the central frequency is dynamically controled by level.
  4. **PGC2** : Time reversal passive gammachirp. Identical to **PGC1**. This is used to cancel
     the phase delay induced by the PGC1 across frequency bands. This induced a delay for realtime.
  5. **passive gain** : provide an independent passive gain in each band.
  6. **sum** : sum all bands for resynthesis.


Steps 1, 2, 3, 4:  together are the inverse compressive gammachrip (**InvCGC**).
This model the outer hair cell (OHC) impairement by cancelling the natural compression.

Step 5: This step simulates a inner hair cells (IHC) loss with a static gain.


**As example here the 1000 Hz band:**


The PGC filter (in black) and HP-AF (color) levelled controled frequency response.
Blue is used for low levels and red is used for high levels.
Note that the **HP-AF** is moving from left (low, blue) to right (high, red).

.. image:: img/filter_pgc_and_hpaf.png

The sum of the PGC1 + HP-AF + PGC2 is the InvCGC (Inverse Compressive Gammachirp).
Blue is used for low levels and red is used for high levels.
Note that for low level there is a negative gain. For high level, the gain tends to zero dB:

.. image:: img/filter_cgc.png

Here is the input/output inverse compressive gammachrip. It is than an expander.

.. image:: img/input_output_gain.png



Algorithm parameters
--------------------

The algorithm is done in the class `InvCGC`.
Fixed parameters like `nb_channel` or `sample_arte` are provided
at __init__ and all others parameters can be changed on the fly
(but not instantenaously) in `configure(...)`


.. automethod:: hearinglosssimulator.invcgc.InvCGC.__init__()
.. automethod:: hearinglosssimulator.invcgc.InvCGC.configure()


Calibration
-----------

A major parameter of the algorithm is the `calibration`.

The compression loss depends both of the `compression_degree` and of the real
level estimated in dBSPL in each band. Theses levels must then represent the true
levels otherwise the compression loss is not applied correctly.

By internal convention, the `calibration` parameter corresponds to the relation
between dBSPL_ and dBFS_:

.. math::
    
    Level_{dBSPL} = Level_{dBFS} + calibration


Where:
  * dBSPL_ is the value of the accoustic pressure
  * dBFS_ is the classical scale for digital sound representation
    where 0 dBFS is the maximum value of a sound which is limited by the sound device.
    As in many convention 0 dBFS is then a sinus with amplitude 1. Bounds are then [-1., 1].

    
.. math::

    Level = 20 log_{10}(p/p_0) dBFS

    
Where:
  * p is the root mean square of the signal
  * p0 is the reference (0 dBFS) = root mean square of sinus of amplitude 1.

.. math::
        
        p_0=1/sqrt(2)


    

.. note::

    For online simulation the sound is clipped by [-1., 1]. But for offline simulation 
    there is not such limitation so the calibration level is **NOT** the maximum 
    of the input sound. The algorithm itself does not clip.


If you want to play with signal that represents a real units of sound pressure in pascal (Pa),
it is easy. In that case a sinus with amplitude equal to 1 represents 1 Pa.
In SPL the 0 dBSPL is given for 20µPa. So for 1Pa the **true** dBSPL is:

.. math ::
    
    Level_{dBSPL} = 20 log_{10}(p/p_0) = 20 log_{10}(1/sqrt(2)/20e-5) = 90.97

So for **calibration=90.97**, the sound represents the **true** sound presure in pascal.

    




.. _dBFS: https://en.wikipedia.org/wiki/DBFS
.. _dBSPL: https://en.wikipedia.org/wiki/Sound_pressure#Sound_pressure_level



Implementation details
----------------------

  * All filters banks are computed in the time domain with IIR. So there is no window/overlap/add.
  * All processing are done sample by sample, even level estimation.
  * Practically, processing are applied on chunks (typically 512 samples) but
    there is no border effect since all filter states are kept for the next chunk. So chunksize
    does not affect the processing (only latency).
  * Filters are all biquadratic (more stable) = SOS (second order section)
  * Implementation of SOS is done with `form II`_.
  * Nmber of sections: 8 (PGC1) + 4 (dynamic HP-AF) + 8 (PGC2)
  * backward processing for PGC2 (time reversal) filter induces a delay.
    *delay=backward_chunksize-chunksize*. backward_chunksize affects the processing.
    If it is too small, it leads to distortion in low frequencies.
  * All HP-AF filters are precomputed for each band and each level before running.
    Filter coefficients are not computed on the fly.
  * Python/scipy is used for computing each filter (easy to debug)
  * OpenCl is used for applying filters (faster)
  * N sections for each channel are more or less computed in parrallel but performances
    depend of the GPU model.
    
    
.. _`form II` : https://en.wikipedia.org/wiki/Digital_biquad_filter#Direct_form_2



GUI
---

To start the main GUI::

    python start_online_hearingloss.py

On some windows installation, you can also double click on the *start_online_hearingloss.py*.

You should see this:

.. image:: img/screenshot.png




On the top toolbar there is:
  * **configure audio**: this open a dialog box for chosing the good
    sound device for input and output. You can play a sinus sound
    to test the output. Be carreful with the sound level you use to avoid inducing a true hearing loss !!
  * **configure GPU** : this open a dialog box for choosing the GPU
  * **calibration** this dialog box provide help to set the correct `calibration` 
    parameter which is the relation between dbFS and dBSPL. See `calibration`.
    In this dialog box, you play on an output audio device a sinus with an internal level
    equals to -30dbFS (or what ever). Make a real measurement with a sound level meter.
    Report the measurement and the relation is automatically deduced.

On the bottom you can setup for each ear:
  * the **compression_degree** for each band. 100% means no compression loss
    0% means full compresison loss. This give you the magenta curve.
  * **hearing level** which you want to simulate. The black curve.

The passive loss between magenta and black curve is automatically deduced.

Before running with **play/stop** you need to compute at least once the filters.
This can take sevral second depending on the machine.

When running you can bypass the simulator.

You also recompute on the fly new filters.

On the left, there are some presets. And you can save/load your preset in json files.
Json files are easy to edit with a standart text editor.




Examples
--------

:doc:`examples`



API Documentation
-----------------

:doc:`api`



