from setuptools import setup
import os

install_requires = ['numpy',
                    'scipy',
                    'pyopencl',
                    'sounddevice',
                    #~ 'soundfile',
                    #~ 'pyacq',
                    #~ 'PyQt5',
                    ]

import hearinglosssimulator



setup(
    name = "hearinglosssimulator",
    version = hearinglosssimulator.__version__,
    packages = ['hearinglosssimulator', ],
    install_requires=install_requires,
    author = "Samuel Garcia",
    author_email = "sgarcia at olfac.univ-lyon1.fr",
    description = "Near real time hearing loss simulator in python based on DCGC.",
    long_description = "",
    license = "MIT",
    url='http://neuralensemble.org/neo',
    classifiers = [
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.5',
        'Topic :: Scientific/Engineering']
)
