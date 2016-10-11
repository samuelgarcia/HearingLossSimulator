HearingLossSimulator
======================

Near real time hearing loss simulator in python based on Compressive Gammachirp. 

Main documentation is here: http://hearinglosssimulator.readthedocs.io/

The concept of *Compressive Gammachirp* is from Toshio Irino, Roy Patterson et al.

This code derive from original matlab code of Toshio Irino.
Is is not an exact port but it is very similar.

It can be used:
  * offline in python script for testing the algorithm.
  * online (on close loop on the audio device).

The algorithm simulate both outer hair cell (OHC) loss and  inner hair cells (IHC) loss.
The OHC loss is simulated by a deficit in compression and IHC loss with a passive loss.

The module come with a GUI for the online simulator:

.. image:: doc/source/img/screenshot.png


Here the block diagram of the algorithm:

.. image:: doc/source/img/processing_diagram.png



Ref:
 * Irino,T. and and Patterson,R.D. : IEEE Trans.ASLP, Vol.14, Nov. 2006.
 * Irino T, Fukawatase T, Sakaguchi M, Nisimura R, Kawahara H, Patterson RD : Adv Exp Med Biol. 2013







