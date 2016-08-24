import hearinglosssimulator as hls
import pyacq

import time


man = pyacq.create_manager()
ng = man.create_nodegroup()
dev = ng.create_node('PyAudio')
default_input = dev.default_input_device()
print(default_input)
dev.configure(nb_channel=1, sample_rate=44100., input_device_index=default_input,
              format='int16', chunksize=1024)
dev.output.configure(protocol='tcp', interface='127.0.0.1', transfertmode='plaindata')
dev.initialize()

dev.start()
time.sleep(3)

dev.stop()



man.close()


