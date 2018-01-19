# adress by default

MAX_PACKET_LEN = 1036
BUFFER_SIZE = 1024

sample_per_packet =256

header_size = 12

frame_header = [('type', 'uint16'),
                            ('length', 'uint16'),
                            ('packet_num', 'uint32'),
                            ('option', 'uint32')
                            ]

test_header = [('test_packet', 'uint32'),
                            ('send_time', 'uint32'),
                            ('recv_time', 'uint32'),
                            # variable BUFFER_SIZE-12
                            ]

spatial_header = [('acc_x', '>i2'),
                            ('acc_y', '>i2'),
                            ('acc_z', '>i2'),
                             ('mag_x', '>i2'),
                             ('mag_y', '>i2'),
                             ('mag_z', '>i2')]
                             
file_header = [('inode', 'uint32'),
                            ('parent', 'uint32'),
                            ('mode', 'uint32')]


# frame type uint16
CONNECTION = 1#return ACK
ACK = 2
PING = 3#return PONG
PONG = 4
RESET = 5#return ACK
START_STREAM = 6#return ACK
STOP_STREAM = 7#return ACK
GET_PARAMS = 8
SET_PARAMS = 9#return ACK
F_OPEN = 10#return ACK en v2.0.2
F_CLOSE = 11#return ACK
F_WRITE = 12#return ACK
F_READ = 13
AUDIO_DATA = 20
TEST_DATA = 21
PARAMS_DATA = 22
FILE_DATA = 23
SPAT_DATA = 24


# option int32
#START_STREAM STOP_STREAM
AUDIO_STREAM		= 0x10000000
TEST_STREAM		= 0x01000000
SPAT_STREAM               = 0x00100000


#option params
SYSTEM_INFO = 0xFFFF #RO
NETWORK_CONF = 0x0004 #RW
TEST_CONF = 0x0005#RW
AUDIO_CONF = 0x0006 #RW
GPS_CMD = 0x0008#RW
ACC_CONF = 0x0009 #RW

# file inodes
ROOT_DIR = 0x0001 # with file RO
SYS_DIR = 0x0002 # with file RO
HOME_DIR = 0x0003 # with file RO
NEW_FILE = 0x0000
AUDIO_REG = 0x0007# with file RO
ACC_REG = 0x000A# with file RO

# file option
WRITE = 0xFFFFFFFF
READ = 0x0000



# struct

stream_types = {'audio':AUDIO_STREAM, 'test':TEST_STREAM, 'spatialization':SPAT_STREAM}



# TIMEOUT
#~ TIMEOUT_AUDIO = 0.2 #s
TIMEOUT_AUDIO = 0.5 #s
TIMEOUT_TEST = 0.5 #s
TIMEOUT_PING_PONG = 0.3 #s
TIMEOUT_ACK_START_STREAM = 1.#s
TIMEOUT_GET_PARAMS = 8.#s
TIMEOUT_ACK_SET_PARAMS = 10.#s

PING_INTERVAL = .5 #s
RECONNECT_INTERVAL = 1.#s



"""
Dans la doc SLAA408A
dispo sur ti.com


*****
SPEAKER VOLUME
*****

D7-D0
R/W
0000 0000
Left DAC Channel Digital Volume Control Setting
0111 1111-0011 0001: Reserved. Do not use
0011 0000: Digital Volume Control = +24dB
0010 1111: Digital Volume Control = +23.5dB
...
0000 0001: Digital Volume Control = +0.5dB
0000 0000: Digital Volume Control = 0.0dB
1111 1111: Digital Volume Control = -0.5dB
...
1000 0010: Digital Volume Control = -63dB
1000 0001: Digital Volume Control = -63.5dB
1000 0000: Reserved. Do not use


*****
MICRO VOLUME
*****



D6-D0
R/W
000 0000
Left ADC Channel Volume Control
100 0000-110 0111: Reserved. Do not use
110 1000: Left ADC Channel Volume = -12dB
110 1001: Left ADC Channel Volume = -11.5dB
110 1010: Left ADC Channel Volume = -11.0dB
...
111 1111: Left ADC Channel Volume = -0.5dB
000 0000: Left ADC Channel Volume = 0.0dB
000 0001: Left ADC Channel Volume = 0.5dB
...
010 0110: Left ADC Channel Volume = 19.0dB
010 0111: Left ADC Channel Volume = 19.5dB
010 1000: Left ADC Channel Volume = 20.0dB
010 1001-111 1111: Reserved. Do not use



"""
