
from ..myqt import QT
import pyqtgraph as pg

from hearinglosssimulator.gui.myqt import DebugDecorator

from .protocol import ClientProtocol, NoAckError


import time
import socket #for error
import numpy as np
from . import packet_types as pt



_states = ['disconnected', 'connected', 'audio-loop', 'test-loop', 'spatialization-loop', ]


class Mutex(QT.QMutex):
    def __exit__(self, *args):
        self.unlock()

    def __enter__(self):
        self.lock()
        return self




class BaseThreadStream(QT.QThread):
    connection_broken = QT.Signal()
    loop_terminated = QT.Signal()
    
    #~ too_late_packet = QT.Signal(int)
    #~ missing_up_packet = QT.Signal(int)
    #~ missing_dw_packet = QT.Signal(int)
    
    def __init__(self, client_protocol,  parent=None):
        QT.QThread.__init__(self, parent)
        
        self.client_protocol = client_protocol
        
        self.running = False
        self.running_lock = Mutex()
        self.lock = Mutex()
    
    
    def is_running(self):
        with self.running_lock:
            return self.running

    def stop(self):
        with self.running_lock:
            self.running = False

    def initialize_loop(self):
        raise(NotImplementedError)

    def finalize_loop(self):
        raise(NotImplementedError)
    
    def process_one_packet(self, header, data):
        raise(NotImplementedError)
        
    def run(self):
        
        self.initialize_loop()
        
        last_packet_num = None
        
        self.nb_too_late = 0
        self.nb_missing_up = 0
        self.nb_missing_dw = 0
        
        with self.running_lock:
            self.running = True
        
        broken = False
        
        
        first_loop = True
        while True:
            if not self.is_running():
                break

            try:
            #~ if True:
                #recv
                if first_loop:
                    first_loop = False
                    timeout = 1.
                else:
                    timeout=pt.TIMEOUT_AUDIO
                
                header, data = self.client_protocol.receiv_one_packet(variable_size=1024, timeout=timeout)
                if not self.is_running():
                    break
                
                #deal with missing down packet
                if last_packet_num is not None and  header['packet_num']!=(last_packet_num+1):
                    n = header['packet_num'] - last_packet_num - 1
                    #~ self.missing_dw_packet.emit(n)
                    self.nb_missing_dw += n
                
                last_packet_num = header['packet_num']
                
                #deal with missing up and too late packet
                if header['option']>0:
                    if (header['option']&0xFFFF0000) != 0:
                        n = int((header['option']&0xFFFF0000)>>16)
                        #~ self.missing_up_packet.emit(n)
                        self.nb_missing_up += n
                    elif header['option']&0x0000FFFF != 0:
                        n = int(header['option']&0x0000FFFF)
                        #~ self.too_late_packet.emit(n)
                        self.nb_too_late += n
                
                if data is not None and header['type'] in (pt.AUDIO_DATA, pt.TEST_DATA, pt.SPAT_DATA):
                    packet_type, option, variable = self.process_one_packet(header, data)
                    if packet_type is not None:
                        self.client_protocol.send_one_packet(type=pt.AUDIO_DATA, option=header['option'], variable=variable)
                else:
                    print('PACKET NON DATA in stream loop!!!', header)
                
            except socket.timeout as e:
                print('erreur stream timeout', e)
                broken = True
                self.stop()
                break
            except Exception as e:
                print('erreur stream other problem', e)
                broken = True
                self.stop()
                break
        
        if broken:
            self.connection_broken.emit()
        else:
            # happy end
            self.finalize_loop()
            self.loop_terminated.emit()
            


class ThreadAudioStream(BaseThreadStream):
    def initialize_loop(self):
        pass

    def finalize_loop(self):
        pass
    
    def process_one_packet(self, header, data):
        packet_type = pt.AUDIO_DATA
        option = header['option']
        variable = data
        return packet_type, option, variable



class ThreadTestStream(BaseThreadStream):

    def initialize_loop(self):
        pass

    def finalize_loop(self):
        pass
    
    def process_one_packet(self, header, data):
        if data is None:
            print('data None')
            return None, None, None
        
        print('header', header)
        print('data', data)
        header2 = np.frombuffer(data[:12], dtype=pt.test_header)[0]
        data2 = data[12:]
        
        packet_type = pt.TEST_DATA
        option = header['option']
        variable = data
        return packet_type, option, variable


class QWifiClient(QT.QObject):
    """
    Client Qt qui dialogue avec le device WIFI et qui gere les etats:
      * disconnected
      * connected
      * audio-loop
    
    
    """
    
    state_changed = QT.Signal(str)
    
    def __init__(self, udp_ip, udp_port, debug=False, parent=None, ):
        QT.QObject.__init__(self, parent=parent)
        
        self.client_protocol = ClientProtocol(udp_ip, udp_port, debug=debug)
        
        self.state = 'disconnected'
        self.mutex = Mutex()
        
        self.timer_try_connect = QT.QTimer(singleShot=False, interval=int(pt.RECONNECT_INTERVAL*1000.))
        self.timer_try_connect.timeout.connect(self._try_connection)
        self.timer_ping = QT.QTimer(singleShot=False, interval=int(pt.PING_INTERVAL*1000.))
        self.timer_ping.timeout.connect(self._ping)
        self.timer_sleep = QT.QTimer(singleShot=True)
        self.timer_sleep.timeout.connect(self.after_sleep)
        
        
        self.thread_audiostream = ThreadAudioStream(self.client_protocol, parent=self)
        self.thread_audiostream.connection_broken.connect(self.on_connection_broken)
        
        self.thread_teststream = ThreadTestStream(self.client_protocol, parent=self)
        self.thread_teststream.connection_broken.connect(self.on_connection_broken)
        
        
        self.active_thread = None
        
    def change_state(self, new_state):
        assert new_state in _states
        print()
        print('   !!change_state', self.state, 'to',  new_state)
        with self.mutex:
            self.state = new_state
            self.state_changed.emit(self.state)
    
    def sleep_for_a_while(self, duration):
        print('sleep_for_a_while', duration)
        if self.timer_try_connect.isActive():
            self.timer_try_connect.stop()
        self.timer_sleep.setInterval(int(duration*1000.))
        self.timer_sleep.start()
    
    @DebugDecorator
    def after_sleep(self, ):
        c = self.client_protocol
        self.client_protocol = ClientProtocol(c.udp_ip, c.udp_port, debug=c.debug)
        self.try_connection()
    
    def try_connection(self):
        assert self.state == 'disconnected'
        self.timer_try_connect.start()

    def reset(self):
        assert self.state == 'connected'
        self.client_protocol.reset()
        
        self.timer_ping.stop()
        self.change_state('disconnected')
        self.try_connection()
        
    
    def _try_connection(self):
        try:
            self.client_protocol.connect()
            
            self.change_state('connected')
            self.timer_try_connect.stop()
            self.start_ping()
        except socket.timeout as e:
            print('erreur CONNECTION timeout', e)
        except NoAckError as e:
            print('erreur CONNECTION NoAckError', e)
            self.sleep_for_a_while(3.)
        except Exception as e:
            print('erreur CONNECTION other problem', e)
            self.sleep_for_a_while(3.)
    

    def start_ping(self):
        assert self.state == 'connected'
        self.timer_ping.start()
    
    def _ping(self):
        try :
            self.client_protocol.ping_pong()
            return
        except socket.timeout as e:
            print('erreur PING timeout', e)
        except Exception as e:
            print('erreur PING other problem', e)
        
        self.timer_ping.stop()
        self.change_state('disconnected')
        self.try_connection()
    
    
    def start_loop(self, thread, stream_type):
        print('start_loop', stream_type)
        assert self.state == 'connected'
        
        new_state = stream_type+'-loop'
        
        self.timer_ping.stop()
        
        try:
            self.client_protocol.send_start_stream(stream_type=stream_type)
            self.active_thread = thread
            self.active_thread.start()
            self.change_state(new_state)
        except Exception as e:
            print('ERREUR self.client_protocol.send_start_stream', e)
            self.change_state('disconnected')
            self.try_connection()
    
    def stop_loop(self, stream_type):
        print('stop_loop', stream_type)
        state = stream_type+'-loop'
        assert state == state
        print('stop_loop active_thread', self.active_thread)

        self.active_thread.stop()
        self.active_thread.wait()
        self.active_thread = None
        
        try:
            self.client_protocol.send_stop_stream(stream_type=stream_type, insist=True)
            self.change_state('connected')
            self.start_ping()
            
        except Exception as e:
            print('ERROR stop_loop', stream_type, e)
            #~ time.sleep(2.)
            # IN CASE of error new do send nothing, so th wifi device
            # break the conenction
            #TODO fix this:
            self.change_state('disconnected')
            #~ self.try_connection()
            self.sleep_for_a_while(3.)
        

    def start_audio_loop(self):
        self.start_loop(self.thread_audiostream, 'audio')

    def stop_audio_loop(self):
        self.stop_loop('audio')

    def start_test_loop(self):
        self.start_loop(self.thread_teststream, 'test')
        
    def stop_test_loop(self):
        self.start_loop('test')

    def on_connection_broken(self):
        #thread_audiostream or thread_teststream
        thread = self.sender()
        
        thread.wait()
        self.change_state('disconnected')
        self.sleep_for_a_while(3.)
        #~ self.try_connection()
    
    def secure_call(self, method_name, *args, **kargs):
        """
        Utility for to map client_protocol.:
          get_one_param/set_one_param/get_sample_rate/set_sample_rate/...
        """
        print('secure_call:',  method_name, args, kargs)

        assert self.state == 'connected', 'client.secure_call not connected'
        self.timer_ping.stop()
        
        method = getattr(self.client_protocol, method_name)
        #~ print('method', method)
        
        try:
            ret = method(*args, **kargs)
            self.timer_ping.start()
            return ret
            
        except Exception as e:
            print('secure_call', e)
            self.change_state('disconnected')
            self.try_connection()
            return None

    

    
    
