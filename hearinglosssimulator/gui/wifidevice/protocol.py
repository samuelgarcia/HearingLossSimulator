
import threading 
import socket
import time
import re

import numpy as np
from  . import packet_types as pt


class NoAckError(Exception):
    pass

class ClientProtocol:
    def __init__(self, udp_ip, udp_port, debug=False):
        
        self.udp_ip = udp_ip
        self.udp_port = udp_port
        
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.packet_num = 0
        self.debug = debug
    
    def send_one_packet(self, type=None, option=0, variable=None):
        assert type is not None
        
        self.packet_num += 1
        header = np.zeros(1, dtype=pt.frame_header)
        header['type'] = type
        header['packet_num'] = self.packet_num
        header['option'] = option
        if variable is None:
            header['length'] = 0
            packet = header
        else:
            if not isinstance(variable, np.ndarray):
                variable = np.frombuffer(variable, dtype='uint8')
            header['length'] = variable.nbytes
            packet = np.concatenate([header.view('uint8'), variable.view('uint8')])
        if self.debug:
            print('send header ', header, 'packet.nbytes', packet.nbytes)
        self.socket.sendto(packet.tobytes(), (self.udp_ip, self.udp_port))
    
    def receiv_one_packet(self, timeout=None, variable_size=0):
        if timeout is not None:
            self.socket.settimeout(timeout)
        
        #~ data, server = self.socket.recvfrom(pt.header_size+variable_size)
        #~ print('data',  len(data), 'server', server)
        
        #~ data = self.socket.recv(pt.header_size+variable_size)
        data = self.socket.recv(pt.MAX_PACKET_LEN)
        #~ print('data',  len(data))
        
        header = np.frombuffer(data[:pt.header_size], dtype=pt.frame_header)[0]
        #~ print('receiv header', header)
        if self.debug:
            print('receiv header', header)
        if header['length']>0:
            #~ print(header['length'])
            data2 = data[pt.header_size:pt.header_size+header['length']]
            #~ print('data2', len(data2))
            return header, data2
        else:
            return header, None
    
    def wait_for_ack(self, timeout_per_packet=0.5, nb_try=3, reason=''):
        #~ print('wait_for_ack', timeout_per_packet, nb_try )
        done = False
        for i in range(nb_try):
            #~ print('i', i)
            header, data = self.receiv_one_packet(timeout=timeout_per_packet)
            #~ print(header)
            if header['type'] == pt.ACK:
                if header['option'] == self.packet_num:
                    done = True
                    break
                
                elif header['option'] == 0:
                    raise(NoAckError('NO-ACK'))
                
                else:
                    print('!!!!! ACK with bad num_paquet', self.packet_num, header['option'] )
                
        
        #~ assert done, 'No ACK for packet {} {}'.format(self.packet_num, reason)
        if not done:
            raise(NoAckError('NO-ACK for packet {} {}'.format(self.packet_num, reason)))
        
        if self.debug:
            print('ACK for packet {} {}'.format(self.packet_num, reason))
    
    def connect(self):
        self.send_one_packet(type=pt.CONNECTION)
        self.wait_for_ack(reason='CONNECTION')
    
    def reset(self):
        self.send_one_packet(type=pt.RESET)
        self.wait_for_ack(reason='RESET')
        if self.debug:
            print('RESET OK')
    
    def ping_pong(self):
        self.send_one_packet(type=pt.PING)
        header, data = self.receiv_one_packet(timeout=pt.TIMEOUT_PING_PONG)
        assert header['type'] == pt.PONG, 'No pong on ping'
    
    def send_start_stream(self, stream_type='audio'):
        self.send_one_packet(type=pt.START_STREAM, option=pt.stream_types[stream_type])
        self.wait_for_ack(timeout_per_packet=pt.TIMEOUT_ACK_START_STREAM, reason='START_STREAM '+ stream_type, nb_try=3)

    def send_stop_stream(self, stream_type='audio', insist=False):
        self.send_one_packet(type=pt.STOP_STREAM, option=pt.stream_types[stream_type])
        if insist:
            try:
                self.wait_for_ack(reason='STOP_STREAM '+ stream_type, nb_try=15)
            except:
                for i in range(5):
                    print('NEW TRY stop stream', i)
                    try:
                        self.send_one_packet(type=pt.STOP_STREAM, option=pt.stream_types[stream_type])
                        self.wait_for_ack(reason='STOP_STREAM '+ stream_type,  timeout_per_packet=0.1, nb_try=3,)
                        #~ self.send_one_packet(type=pt.CONNECTION)
                        #~ self.wait_for_ack(reason='CONNECTION')
                        #~ self.ping_pong()
                        break
                    except:
                        print('NEW TRY stop stream  FAIL', i)
                        #~ print('CONNECTION after stop stream fail', i)
                
                raise(Exception('STOP STREAM: All temptative fail!!'))
                
        else:
            self.wait_for_ack(reason='STOP_STREAM '+ stream_type, nb_try=10)
            self.ping_pong()
    
    param_types = {'SYSTEM_INFO':pt.SYSTEM_INFO,
                'NETWORK_CONF':pt.NETWORK_CONF,
                'TEST_CONF':pt.TEST_CONF,
                'AUDIO_CONF':pt.AUDIO_CONF,
                'ACC_CONF':pt.ACC_CONF,
                'GPS_CMD':pt.GPS_CMD,
        }
    
    def get_params(self, param_type):
        assert param_type in self.param_types.keys()
        
        option = self.param_types[param_type]
        
        self.send_one_packet(type=pt.GET_PARAMS, option=option)
        header, params = self.receiv_one_packet(timeout=pt.TIMEOUT_GET_PARAMS)
        if self.debug:
            print('get_params', header, params)
        assert header['type'] == pt.PARAMS_DATA
        
        for e in [0x00,0xff, 0x00,0xff, ]:
            while params[-1] == e:
                params = params[:-1]
        
        return params
    
    
    def set_params(self, param_type, params):
        if self.debug:
            print('set_params')
            print(param_type)
            print(params)
        
        assert type(params)==bytes
        
        if params[-1] != 0x00 :
            if self.debug:
                print('Ajjout de x0 a  al fin')
            params = params + b'\x00'
        
        option = self.param_types[param_type]
        self.send_one_packet(type=pt.SET_PARAMS, option=option, variable=params)
        
        self.wait_for_ack(reason='SET_PARAMS',timeout_per_packet=pt.TIMEOUT_ACK_SET_PARAMS)
    
    def get_one_params(self, param_type, param_key):
        param_key = param_key.encode('ascii')
        params = self.get_params(param_type)
        #~ print('params', params)
        pattern =  param_key + b'[ \t]=[ \t](\S+)'
        r = re.findall(pattern, params)
        assert len(r)==1, 'Error get_one_params {} {}'.format(param_type, param_key)
        return r[0]
    
    def set_one_params(self, param_type, param_key, v):
        assert type(v)==bytes, 'Error set_one_params v is not bytes'
        param_key = param_key.encode('ascii')
        params = self.get_params(param_type)
        new_params= b''
        for line in params.split(b'\n'):
            if param_key in line:
                new_line =  param_key + b'\t= '+v
            else:
                new_line = line
            new_params = new_params + new_line + b'\n'
        self.set_params(param_type, new_params)
        
    file_modes = {'w':pt.WRITE,
                'r':pt.READ,
        }
        
    def f_open(self, filename, inode, parent, mode):
        file = np.zeros(1, dtype=pt.file_header)
        file['inode'] = inode
        file['parent'] = parent
        file['mode'] = self.file_modes[mode]
        if filename[-1] != 0x00 :
            filename = filename + b'\x00'
        filename = np.frombuffer(filename, dtype='uint8')
        var = np.concatenate([file.view('uint8'), file.view('uint8')])   # inserer le nom du fichier a la place du second champ
        self.send_one_packet(type=pt.F_OPEN, option=0, variable=var)
        self.wait_for_ack(reason='F_OPEN', timeout_per_packet=pt.TIMEOUT_ACK_SET_PARAMS)
        if self.debug:
            print('F_OPEN OK')
            
    def f_close(self):
        self.send_one_packet(type=pt.F_CLOSE)
        self.wait_for_ack(reason='F_CLOSE', timeout_per_packet=pt.TIMEOUT_ACK_SET_PARAMS)
        if self.debug:
            print('F_CLOSE OK')
            
    def f_write(self, data):
        self.send_one_packet(type=pt.F_WRITE, variable=data)
        self.wait_for_ack(reason='F_WRITE', timeout_per_packet=pt.TIMEOUT_ACK_SET_PARAMS)
        
    def f_read(self):
        self.send_one_packet(type=pt.F_READ)
        header, data = self.receiv_one_packet(variable_size=1024, timeout=pt.TIMEOUT_ACK_SET_PARAMS)
        print('F_READ OK')
        return header, data

    def get_speaker_gain(self):
        v = self.get_one_params('AUDIO_CONF', 'spk_vol')
        db_gain = float(v)/2.
        return db_gain
    
    def set_speaker_gain(self, db_gain):
        assert -63.5<=db_gain<=24
        int_gain = int(db_gain*2)
        self.set_one_params('AUDIO_CONF', 'spk_vol', str(int_gain).encode('ascii'))

    def get_microphone_gain(self):
        v = self.get_one_params('AUDIO_CONF', 'mic_vol')
        db_gain = float(v)/2.
        return db_gain
    
    def set_microphone_gain(self, db_gain):
        assert -12<=db_gain<=20
        int_gain = int(db_gain*2)
        self.set_one_params('AUDIO_CONF', 'mic_vol', str(int_gain).encode('ascii'))
    
    def get_audio_latency(self):
        latency = self.get_one_params('AUDIO_CONF', 'lat')
        latency = int(latency)
        return latency

    def set_audio_latency(self, latency):
        latency = int(latency)
        assert latency>=2
        self.set_one_params('AUDIO_CONF', 'lat', str(latency).encode('ascii'))

    def get_ssid(self):
        return self.get_one_params( 'NETWORK_CONF', 'ssid').decode('ascii')
    
    def set_ssid(self, new_ssid):
        self.set_one_params('NETWORK_CONF', 'ssid', new_ssid.encode('ascii'))
        self.reset()

    def get_sample_rate(self):
        sr = self.get_one_params( 'AUDIO_CONF', 'freq')
        sr = float(sr)
        return  sr
    
    def set_sample_rate(self, sr):
        self.set_one_params('AUDIO_CONF', 'freq', str(sr).encode('ascii'))
        self.reset()



def test_ping_pong():
    
    client_protocol = ClientProtocol("192.168.1.1", 6666, debug=True)
    #~ client_protocol = ClientProtocol("127.0.0.1", 6666)
    client_protocol.connect()
    
    for i in range(5):
        client_protocol.ping_pong()
        print('ping_pong OK')


def test_reset():
    client_protocol = ClientProtocol("192.168.1.1", 6666, debug=True)
    #~ client_protocol = ClientProtocol("127.0.0.1", 6666)
    client_protocol.connect()
    
    client_protocol.reset()
    
    

def test_get_params():
    client_protocol = ClientProtocol("192.168.1.1", 6666, debug=True)
    #~ client_protocol = ClientProtocol("127.0.0.1", 6666)
    client_protocol.connect()
    
    for k in ['SYSTEM_INFO', 'NETWORK_CONF', 'TEST_CONF', 'AUDIO_CONF']:
        p = client_protocol.get_params(k)
        print()
        print('*'*3, k, '*'*3)
        print(p)
        print('*'*3, k, '*'*3)
        print(p.replace(b'\xff', b'').decode('ascii'))

    #~ p = client_protocol.get_params('NETWORK_CONF')
    #~ print(p)

    #~ p = client_protocol.get_params('TEST_CONF')
    #~ print(p)

    #~ p = client_protocol.get_params('AUDIO_CONF')
    #~ print(p)


def test_start_stop_test_loop():
    import matplotlib.pyplot as plt
    
    client_protocol = ClientProtocol("192.168.1.1", 6666, debug=False)
    #~ client_protocol = ClientProtocol("127.0.0.1", 6666)
    client_protocol.connect()
    
    for i in range(5):
        client_protocol.ping_pong()
        print('ping_pong OK')
    
    client_protocol.send_start_stream(stream_type='test')
    
    nloop = 1000
    recv_times = []
    test_infos = []
    for i in range(nloop):
        #~ print('test loop', i)
        header, data = client_protocol.receiv_one_packet(variable_size=1024, timeout=pt.TIMEOUT_TEST)
        recv_times.append(time.perf_counter())
        #~ print('option', header['option'])
        test_info = np.frombuffer(data[:12], dtype=pt.test_header)[0]
        test_infos.append(test_info)
        
        #~ print(test_info)
        data2 = data[12:]
        
        client_protocol.send_one_packet(type=pt.TEST_DATA, option=header['option'], variable=data)
    
    print('STOP')
    client_protocol.send_stop_stream(stream_type='test')
 
    recv_times = np.array(recv_times)
    print('system times ',np.median(np.diff(recv_times)))
    test_infos = np.array(test_infos)
    
    
    keep = test_infos['test_packet']>0
    test_infos = test_infos[keep]
    #~ print(test_infos[:200])
    print(test_infos)
    
    #~ print(test_infos)
    d = (test_infos['recv_time'].astype('float64') - test_infos['send_time'].astype('float64'))
    d /= 1000 #ms
    #~ print(d)
    print('device times', np.median(d))
    
    count, bins = np.histogram(d, bins=np.arange(0,20,.1))
    fig, ax = plt.subplots()
    ax.plot(bins[:-1], count)
    ax.axvline(params.delta_time*1000., ls='--', color='r')
    ax.set_title('nb error={}/{}'.format(np.sum(d>(params.delta_time*1000)), nloop))
    fig, ax = plt.subplots()
    ax.plot(d)
    ax.axhline(params.delta_time*1000., ls='--', color='r')
    ax.set_ylim(0, 20.)
    
    plt.show()
    
    

def test_start_stop_audio_loop():
    
    client_protocol = ClientProtocol("192.168.1.1", 6666, debug=True)
    #~ client_protocol = ClientProtocol("127.0.0.1", 6666)
    client_protocol.connect()
    
    for i in range(5):
        client_protocol.ping_pong()
        print('ping_pong OK')
    
    client_protocol.send_start_stream(stream_type='audio')
    
    for i in range(100):
        print('audio loop', i)
        header, data = client_protocol.receiv_one_packet(variable_size=1024, timeout=pt.TIMEOUT_AUDIO)
        client_protocol.send_one_packet(type=pt.AUDIO_DATA, variable=data)
    
    client_protocol.send_stop_stream(stream_type='audio')
    

def test_infinite_audio_loop():
    
    client_protocol = ClientProtocol("192.168.1.1", 6666, debug=False)
    #~ client_protocol = ClientProtocol("127.0.0.1", 6666)
    client_protocol.connect()
    
    for i in range(5):
        client_protocol.ping_pong()
        print('ping_pong OK')
    
    client_protocol.send_start_stream(stream_type='audio')
    
    #~ for i in range(100):
    
    while True:
        #~ print('audio loop', i)
        try:
            header, data = client_protocol.receiv_one_packet(variable_size=1024, timeout=pt.TIMEOUT_AUDIO)
            client_protocol.send_one_packet(type=pt.AUDIO_DATA, variable=data)
        except Exception as e:
            print('dead loop', client_protocol.packet_num)
            print(e)
            break
    
    #~ client_protocol.send_stop_stream(stream_type='audio')

 
 

def test_set_audio_params():
    client_protocol = ClientProtocol("192.168.1.1", 6666, debug=True)
    client_protocol.connect()
    
    audio_params = client_protocol.get_params('AUDIO_CONF')
    #~ print(audio_params)
    audio_params = audio_params.replace(b'\xff', b'')
    print('*'*3, 'AUDIO_CONF', '*'*3)
    print(audio_params)
    print(audio_params.decode('ascii'))
    print()
    
    new_params = b'''freq	= 44100
loop	= no
mic_en	= yes
mic_vol	= 0
spk_en	= yes
spk_vol	= -40
buff_nb	= 12
lat	= 6
buff_delay	= 2'''
    
    client_protocol.set_params('AUDIO_CONF', new_params)
    #~ exit()
    
    audio_params = client_protocol.get_params('AUDIO_CONF')
    audio_params = audio_params.replace(b'\xff', b'')
    print('*'*3, 'AUDIO_CONF', '*'*3)
    print(audio_params)
    print(audio_params.decode('ascii'))
    print()
    
    #~ exit()

def test_set_test_params():
    client_protocol = ClientProtocol("192.168.1.1", 6666, debug=True)
    client_protocol.connect()
    
    test_params = client_protocol.get_params('TEST_CONF')
    #~ print(test_params)
    test_params = test_params.replace(b'\xff', b'')
    print('*'*3, 'TEST_CONF', '*'*3)
    print(test_params)
    print(test_params.decode('ascii'))
    print()
    #~ exit()
    
    #
    new_params = b'''delay	= 5800
load	= 1024
buff_nb	= 30'''
    
    client_protocol.set_params('TEST_CONF', new_params)
    #~ exit()
    
    test_params = client_protocol.get_params('TEST_CONF')
    test_params = test_params.replace(b'\xff', b'')
    print('*'*3, 'TEST_CONF', '*'*3)
    print(test_params)
    print(test_params.decode('ascii'))
    print()


def test_dbgain():
    client_protocol = ClientProtocol("192.168.1.1", 6666, debug=True)
    client_protocol.connect()

    dbgain = client_protocol.get_speaker_gain()
    print('speaker_gain', dbgain)

    client_protocol.set_speaker_gain(-5)
    
    dbgain = client_protocol.get_speaker_gain()
    print('speaker_gain', dbgain)




    dbgain = client_protocol.get_microphone_gain()
    print('microphone_gain', dbgain)

    client_protocol.set_microphone_gain(3.5)
    
    dbgain = client_protocol.get_microphone_gain()
    print('microphone_gain', dbgain)
    
    

 
def test_change_ssid():
    client_protocol = ClientProtocol("192.168.1.1", 6666, debug=True)
    client_protocol.connect()
    
    ssid = client_protocol.get_ssid()
    print('ssid', ssid)
    
    client_protocol.set_ssid('CasqueSam')

    ssid = client_protocol.get_ssid()
    print('ssid', ssid)

 
 
def test_send_sinus():
    import matplotlib.pyplot as plt


    duration = 5.
    #~ duration = 120.
    sr = params.sample_rate
    length = int(duration*sr)
    length = length - length%params.nb_sample
    freq = 1000.
    ampl = 2**15
    #~ ampl = 2**15
    
    times = np.arange(length, dtype='float32')/sr
    outsound = np.sin(2*np.pi*times*freq) * ampl
    outsound = np.tile(outsound[:, None], (1,2))
    outsound = outsound.astype('int16')
    outsound[:,0] = 0
    
    #~ fig, ax = plt.subplots()
    #~ ax.plot(times, outsound[:, 0])
    #~ ax.set_xlim(1,1.01)
    #~ plt.show()
    #~ exit()
    

    client_protocol = ClientProtocol("192.168.1.1", 6666, debug=False)
    client_protocol.connect()
    
    client_protocol.send_start_stream(stream_type='audio')
    
    count_missing = 0
    count_too_late = 0
    
    nloop = length//params.nb_sample
    recv_times = []
    for i in range(nloop):
        #~ print()
        #~ print('audio loop', i)
        header, data = client_protocol.receiv_one_packet(variable_size=1024, timeout=pt.TIMEOUT_AUDIO)
        recv_times.append(time.perf_counter())
        
        ind = i * params.nb_sample
        #~ print(outsound[ind:ind+params.nb_sample, :].flags)
        #~ print(outsound[ind:ind+params.nb_sample, :].dtype)
        outdata = outsound[ind:ind+params.nb_sample, :].tostring()
        if header['option']>0:
            if (header['option']&0xFFFF0000) != 0:
                print('missing', i, (header['option']&0xFFFF0000)>>16)
                count_missing += (header['option']&0xFFFF0000)>>16
            elif header['option']&0x0000FFFF != 0:
                print('too late', i, (header['option']&0x0000FFFF))
                count_too_late += (header['option']&0x0000FFFF)
        #~ print(len(outdata))
        
        
        client_protocol.send_one_packet(type=pt.AUDIO_DATA, variable=outdata)
    
    client_protocol.send_stop_stream(stream_type='audio')
    
    recv_times = np.array(recv_times)
    
    print(np.median(np.diff(recv_times)), np.min(np.diff(recv_times)), np.max(np.diff(recv_times)))


def test_send_sinus_other_sample_rate():
    
    #~ import matplotlib.pyplot as plt

    #~ client_protocol = ClientProtocol("192.168.1.1", 6666, debug=False)
    #~ client_protocol.connect()
    
    for sr in [ 30000., 25000., 44100., ]:
        print()
        print('*'*50)
        print('***', sr)
        print('*'*50)
        
        duration = 6.
        length = int(duration*sr)
        length = length - length%params.nb_sample
        freq = 1000.
        ampl = 2**14
        
        times = np.arange(length, dtype='float32')/sr
        outsound = np.sin(2*np.pi*times*freq) * ampl
        outsound = np.tile(outsound[:, None], (1,2))
        outsound = outsound.astype('int16')
        outsound[:,1] = 0
    
        new_params = '''freq	= {}
loop	= no
mic_en	= yes
mic_vol	= 0
spk_en	= yes
spk_vol	= 0
buff_nb	= 12
lat	= 6
buff_delay	= 2'''.format(int(sr)).encode('ascii')
    
    
        while True:
            try:
                client_protocol = ClientProtocol("192.168.1.1", 6666, debug=False)
                client_protocol.connect()
                break
            except:
                pass
            print('Step 1 switch off device and then reconnect wifi')
        
        client_protocol.set_params('AUDIO_CONF', new_params)
        audio_params = client_protocol.get_params('AUDIO_CONF')

        print(audio_params.decode('ascii'))
        
        client_protocol.reset()
        
        while True:
            print('Step 2: switch off device and then reconnect wifi')
            try:
                client_protocol = ClientProtocol("192.168.1.1", 6666, debug=False)
                client_protocol.connect()
                break
            except:
                pass
        
        client_protocol.send_start_stream(stream_type='audio')
    
        nloop = length//params.nb_sample
        recv_times = []
        for i in range(nloop):
            header, data = client_protocol.receiv_one_packet(variable_size=1024, timeout=pt.TIMEOUT_AUDIO)
            
            ind = i * params.nb_sample
            outdata = outsound[ind:ind+params.nb_sample, :].tostring()
            
            client_protocol.send_one_packet(type=pt.AUDIO_DATA, variable=outdata)
        
        try:
            client_protocol.send_stop_stream(stream_type='audio', insist=True)
        except:
            print('erreur stop stream')

    


def test_missing_packet():
    client_protocol = ClientProtocol("192.168.1.1", 6666, debug=False)
    #~ client_protocol = ClientProtocol("127.0.0.1", 6666)
    client_protocol.connect()
    
    for i in range(5):
        client_protocol.ping_pong()
        print('ping_pong OK')
    
    client_protocol.send_start_stream(stream_type='audio')
    
    fake_missing = [100,101, 200, 250, 251]
    #~ fake_missing = []
    fake_too_late = [40,300]
    #~ fake_too_late = []
    
    count_missing = 0
    count_too_late = 0
    for i in range(500):
        #~ print('audio loop', i)
        header, data = client_protocol.receiv_one_packet(variable_size=1024, timeout=pt.TIMEOUT_AUDIO)
        if i in fake_missing:
            client_protocol.packet_num += 1
        elif i in fake_too_late:
            time.sleep(0.05)
            client_protocol.send_one_packet(type=pt.AUDIO_DATA, variable=data)
        else:
            client_protocol.send_one_packet(type=pt.AUDIO_DATA, variable=data)
        
        if header['option']>0:
            if (header['option']&0xFFFF0000) != 0:
                print('missing', i, (header['option']&0xFFFF0000)>>16)
                count_missing += (header['option']&0xFFFF0000)>>16
            elif header['option']&0x0000FFFF != 0:
                print('too late', i, (header['option']&0x0000FFFF))
                count_too_late += (header['option']&0x0000FFFF)
        
    client_protocol.send_stop_stream(stream_type='audio')
    print('count_missing', count_missing)
    print('count_too_late', count_too_late)
    

def test_plot_missing_vs_latency():
    import matplotlib.pyplot as plt

    client_protocol = ClientProtocol("192.168.1.1", 6666, debug=False)
    client_protocol.connect()
    
    nloop = 1000
    latencies = [2,3,4,5,6]
    
    all_missing = []
    all_too_late = []
    
    for latency in latencies:
        client_protocol.set_audio_latency(latency)
        latency2 = client_protocol.get_audio_latency()
        assert latency2==latency
    
        client_protocol.send_start_stream(stream_type='audio')
    
        count_missing = 0
        count_too_late = 0
        for i in range(nloop):
            header, data = client_protocol.receiv_one_packet(variable_size=1024, timeout=pt.TIMEOUT_AUDIO)
            client_protocol.send_one_packet(type=pt.AUDIO_DATA, variable=data)
            
            if header['option']>0:
                if (header['option']&0xFFFF0000) != 0:
                    #~ print('missing', i, (header['option']&0xFFFF0000)>>16)
                    count_missing += (header['option']&0xFFFF0000)>>16
                elif header['option']&0x0000FFFF != 0:
                    #~ print('too late', i, (header['option']&0x0000FFFF))
                    count_too_late += (header['option']&0x0000FFFF)
        
        client_protocol.send_stop_stream(stream_type='audio', insist=True)
        
        print('latency', latency)
        print('count_missing', count_missing)
        print('count_too_late', count_too_late)
        all_missing.append(count_missing)
        all_too_late.append(count_too_late)
    
    print(all_missing)
    print(all_too_late)
    fig, ax = plt.subplots()
    ax.plot(latencies, all_missing, label='missing', color='r', marker='*', lw=2)
    ax.plot(latencies, all_too_late, label='too_late', color='m', marker='o', lw=2)
    ax.set_xlabel('latency')
    ax.set_ylabel('nb error')
    ax.legend()
    plt.show()
    
    
def test_set_acc_params():
    client_protocol = ClientProtocol("192.168.1.1", 6666, debug=True)
    client_protocol.connect()
    
    acc_params = client_protocol.get_params('ACC_CONF')
    #~ print(audio_params)
    acc_params = acc_params.replace(b'\xff', b'')
    print('*'*3, 'ACC_CONF', '*'*3)
    print(acc_params)
    print(acc_params.decode('ascii'))
    print()
    
    new_params = b'''scal	= 1'''
    
    client_protocol.set_params('ACC_CONF', new_params)
    #~ exit()
    
    acc_params = client_protocol.get_params('ACC_CONF')
    acc_params = acc_params.replace(b'\xff', b'')
    print('*'*3, 'AUDIO_CONF', '*'*3)
    print(acc_params)
    print(acc_params.decode('ascii'))
    print()    

    
    
def test_set_gps_params():
    client_protocol = ClientProtocol("192.168.1.1", 6666, debug=True)
    client_protocol.connect()
    
    gps_params = client_protocol.get_params('GPS_CMD')
    #~ print(audio_params)
    gps_params = gps_params.replace(b'\xff', b'')
    print('*'*3, 'GPS_CMD', '*'*3)
    print(gps_params)
    print(gps_params.decode('ascii'))
    print()
    
    #~ 
    new_params = b'''$PSRF125*21\r
$PSRF131*22\r
$PSRF103,3,0,0,1,*0B\r
$PSRF103,3,0,10,1,*3A\r
'''
    
    client_protocol.set_params('GPS_CMD', new_params)
    #~ exit()
    
    gps_params = client_protocol.get_params('GPS_CMD')
    gps_params = gps_params.replace(b'\xff', b'')
    print('*'*3, 'GPS_CMD', '*'*3)
    print(gps_params)
    print(gps_params.decode('ascii'))
    print()    

    
    
def test_start_stop_spatialization_loop():
    
    client_protocol = ClientProtocol("192.168.1.1", 6666, debug=True)
    #~ client_protocol = ClientProtocol("127.0.0.1", 6666)
    client_protocol.connect()
    
    for i in range(5):
        client_protocol.ping_pong()
        print('ping_pong OK')
    
    client_protocol.send_start_stream(stream_type='spatialization')
    
    dt = np.dtype(pt.spatial_header)
    
    empty_audio = np.zeros((256,2), dtype='int16').tostring()
    for i in range(10000):
        print('spatialization loop', i)
        header, data = client_protocol.receiv_one_packet(variable_size=1024, timeout=pt.TIMEOUT_AUDIO) # Acc_X, Acc_Y, Acc_Z, Mag_X, Mag_Y, Mag_Z --> uint16 en big-endian
        if header['length']>0:
            pos = np.frombuffer(data[:12], dtype=dt)
            gps = data[12:].decode('ascii')
            print('i', i)
            print(pos)
            print()
            print(gps)
        
        client_protocol.send_one_packet(type=pt.AUDIO_DATA, variable=empty_audio)
    
    client_protocol.send_stop_stream(stream_type='spatialization') 
    
def test_write_new_file():
    client_protocol = ClientProtocol("192.168.1.1", 6666, debug=True)
    client_protocol.connect()
    
    file = b'''Ceci est du texte\n'''
    
    client_protocol.f_open(filename=b'''fichier.test\x00''', inode=pt.NEW_FILE, parent=pt.HOME_DIR, mode='w')
    client_protocol.f_write(file)
    client_protocol.f_write(file)
    client_protocol.f_write(file)
    client_protocol.f_close()

def test_write_file():
    client_protocol = ClientProtocol("192.168.1.1", 6666, debug=True)
    client_protocol.connect()
    
    file = np.zeros((1024,), dtype='uint8')
    
    client_protocol.f_open(filename=b'''fichier.test\x00''', inode=0x000B, parent=pt.HOME_DIR, mode='w')
    for i in range(19):
        file = np.full((1024,), i, dtype='uint8')
        client_protocol.f_write(file) # Idealement, il vaut mieux envoye le fichier par paquet de 1024 octets
    client_protocol.f_close()
    
def test_read_file():
    client_protocol = ClientProtocol("192.168.1.1", 6666, debug=True)
    client_protocol.connect()
    
    client_protocol.f_open(filename=b'''fichier.test\x00''', inode=0x000B, parent=pt.HOME_DIR, mode='r')
    end_of_file = 1
    while end_of_file>0:
        header, data = client_protocol.f_read()
        print(data)
        end_of_file = header['option']
    
    client_protocol.f_close()
    
def test_read_codec_reg_file():
    client_protocol = ClientProtocol("192.168.1.1", 6666, debug=True)
    client_protocol.connect()
    
    client_protocol.f_open(filename=b'''audio.reg\x00''', inode=pt.AUDIO_REG, parent=pt.SYS_DIR, mode='r')
    header, data = client_protocol.f_read()
    print(data)
    
    client_protocol.f_close()
    
def test_read_sys_dir():
    client_protocol = ClientProtocol("192.168.1.1", 6666, debug=True)
    client_protocol.connect()
    
    name = b'''home\x00'''
    client_protocol.f_open(filename=name, inode=pt.SYS_DIR, parent=pt.ROOT_DIR, mode='r')
    header, data = client_protocol.f_read()
    client_protocol.f_close()
    print(data)
    name = b'''sys\x00'''
    client_protocol.f_open(filename=name, inode=pt.HOME_DIR, parent=pt.ROOT_DIR, mode='r')
    header, data = client_protocol.f_read()
    client_protocol.f_close()
    print(data)
    
def test_read_all_system_files():
    client_protocol = ClientProtocol("192.168.1.1", 6666, debug=True)
    client_protocol.connect()
    
    name = b'''all\x00'''
    
    for i in range(7):
        client_protocol.f_open(filename=name, inode=(i + 4), parent=pt.SYS_DIR, mode='r')
        end_of_file = 1
        while end_of_file>=0:
            header, data = client_protocol.f_read()
            print(data.decode('ascii'))
            end_of_file = header['option']
        client_protocol.f_close()
     
 
if __name__=='__main__':
    #~ test_ping_pong()
    #~ test_reset()
    #~ test_get_params()
    #~ test_start_stop_test_loop()
    #~ test_start_stop_audio_loop()
    #~ test_infinite_audio_loop()
    #~ test_set_audio_params()
    #~ test_set_test_params()
    #~ test_dbgain()
    #~ test_change_ssid()
    #~ test_send_sinus()
    #~ test_send_sinus_other_sample_rate()
    
    #~ test_missing_packet()
    #~ test_plot_missing_vs_latency()
    #~ test_set_acc_params()
    #~ test_set_gps_params()
    test_start_stop_spatialization_loop()
    
    #~ test_read_codec_reg_file()
    #~ test_write_new_file()
    #~ test_read_file()
    #~ test_read_sys_dir()
    #~ test_write_file()
    #~ test_read_file()
    #~ test_read_all_system_files()
    
    
