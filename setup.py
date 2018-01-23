from setuptools import setup
import os


on_rtd = os.environ.get('READTHEDOCS') == 'True'

if on_rtd:
    install_requires = []
    extras_require = {}
    package_data = {}
else:
    install_requires = ['numpy',
                        'scipy',
                        'pyopencl',
                        'sounddevice',
                        'joblib',
                        ]
    extras_require={ 'gui' : ['PyQt5', 'pyqtgraph', 'matplotlib'],
                                'soundfile': ['soundfile'], 
                                'pyacq' : 'pyacq',
                            }
    package_data={'hearinglosssimulator': ['cl_processing.cl']}

    
#import hearinglosssimulator
#version = hearinglosssimulator.__version__

#version = '1.0.0.dev'

version = open("./hearinglosssimulator/version.py").readline().split('=')[1].replace(' ', '').replace("'", '')

setup(
    name = "hearinglosssimulator",
    version = version,
    packages = ['hearinglosssimulator', 'hearinglosssimulator.gui', 'hearinglosssimulator.gui.icons', 'hearinglosssimulator.gui.wifidevice',],
    install_requires=install_requires,
    extras_require = extras_require,
    package_data = package_data,
    author = "Samuel Garcia",
    author_email = "samuel.garcia@cnrs.fr",
    description = "Near real time hearing loss simulator in python based on Compressive Gammachirp.",
    long_description = open('README.rst').read(),
    entry_points={
          'console_scripts': ['hls=hearinglosssimulator.scripts:hls',
                                            'hlswifi=hearinglosssimulator.scripts:open_wifidevice_mainwindow',
                                            'hls_debug_wifi=hearinglosssimulator.scripts:open_debug_wifi',
                                            'hls_debug_gpu=hearinglosssimulator.scripts:open_debug_gpu',
                                            ],
        },

    license = "MIT",
    url='http://hearinglosssimulator.readthedocs.io/',
    classifiers = [
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.5',
        'Topic :: Scientific/Engineering']
)
