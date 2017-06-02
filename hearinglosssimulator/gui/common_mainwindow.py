from .myqt import QT
import pyqtgraph as pg

import os, sys
import json
import time

from collections import OrderedDict

import sounddevice as sd

#~ import pyacq

import hearinglosssimulator as hls
from hearinglosssimulator.gui.lossparameters import HearingLossParameter
from hearinglosssimulator.gui.calibration import Calibration
from hearinglosssimulator.gui.audioselection import AudioDeviceSelection
from hearinglosssimulator.gui.gpuselection import GpuDeviceSelection



class Mutex(QT.QMutex):
    def __exit__(self, *args):
        self.unlock()

    def __enter__(self):
        self.lock()
        return self
