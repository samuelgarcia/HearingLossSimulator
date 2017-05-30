from setuptools import setup
import os


on_rtd = os.environ.get('READTHEDOCS') == 'True'

if on_rtd:
    install_requires = []
    extras_require = {}
    data_files = data_files
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
    
    data_files = [('kernels', ['hearinglosssimulator/cl_processing.cl'])]
    
#import hearinglosssimulator
#version = hearinglosssimulator.__version__

#version = '1.0.0.dev'

version = open("./hearinglosssimulator/version.py").readline().split('=')[1].replace(' ', '').replace("'", '')

setup(
    name = "hearinglosssimulator",
    version = version,
    packages = ['hearinglosssimulator', ],
    install_requires=install_requires,
    extras_require = extras_require,
    data_files = data_files,
    author = "Samuel Garcia",
    author_email = "samuel.garcia@cnrs.fr",
    description = "Near real time hearing loss simulator in python based on Compressive Gammachirp.",
    long_description = open('README.rst').read(),
    entry_points={
          'console_scripts': ['hls=hearinglosssimulator.scripts:hls',
                                            'hlswifi=hearinglosssimulator.scripts:open_hls_wifi',
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
