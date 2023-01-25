from serial import Serial
from threading import Thread, Event
from queue import Queue
from collections import deque
from collections.abc import Iterable
import json
import time
#import IPython

from .packets import *
import logging
from collections import defaultdict
from collections.abc import Callable
import threading

_LOGGER = logging.getLogger(__name__)

class HKV():
  
    def __init__(self,name='HKV'):
        self._dev = None
        self.name = name
        self._thread = None
        self._events = {
            HKVLogPacket:Event(),
            HKVHelloPacket:Event(),
            HKVAckPacket:Event(),
            HKVNAckPacket:Event(),
            HKVTempChannelPacket:Event(),
            HKVRelaisChannelPacket:Event(),
            HKVTempDataPacket:Event(),
            HKVRelaisDataPacket:Event(),
            HKVConnectionDataPacket:Event(),
            HKVStatusDataPacket:Event(),
            }
        self._temp_data_event = Event()
        self._packets = deque(maxlen=10000)
        self._known_addr = []
        self._plock = threading.Lock()
        self._handler = {}
    
    def recv(self):
        while True:
            try: 
                data = self._dev.readall()
                if len(data):
                    for iline,line in enumerate(data.split(b'\n')):
                        line = line.strip()
                        if len(line)==0: continue
                        # print(f"RX{self.name}-{iline:02d}: {line}")
                        try:
                            packet = HKVPacket.from_doc(line)
                            if not packet.SRC in self._known_addr:
                                self._known_addr.append(packet.SRC) 
                            if isinstance(packet,HKVLogPacket):
                                levels= defaultdict(default_factory=lambda:logging.CRITICAL)
                                levels.update({'D':logging.DEBUG,
                                               'I':logging.INFO,
                                               'W':logging.WARNING,
                                               'E':logging.ERROR})
                                logging.getLogger(f"{__name__}.SRC{packet.SRC}").log(levels[packet.LTYPE],f"{packet.MSG}")
                                continue
                            _LOGGER.debug(f"HKV-{self.name}-{iline:02d}: {packet}")
                            event = self._events.get(packet.__class__,None)
                            if event:
                                event.param = packet
                                event.set()
                            #self._packets.put(packet,timeout=1)
                            with self._plock:
                                self._packets.append(packet)
                            for pt,handlers in self._handler.items():
                                if isinstance(packet,pt):
                                    for h in handlers.copy():
                                        h(packet)
                                    
                        except Exception as e:
                            _LOGGER.error(f"{e}")
            except:
                pass
            time.sleep(.1)
    
    def register_packet_handler(self,handler:Callable,packet_type:HKVPacket):
        handlers = self._handler.get(packet_type,[])
        if handler in handlers: return 
        else:
            if len(handlers):
                handlers.append(handler)
            else:
                self._handler[packet_type] = [handler]
    
    async def packets_pop(self):
        with self._plock:
            packets = list(self._packets)
            self._packets.clear()
            return packets
    
    def connect(self,port:str='/dev/ttyUSB0',baud:int=115200):
        self._dev = Serial(port, baud,timeout=1)
        #time.sleep(1)
        self._dev.flushInput()
        self._dev.flushOutput()
        self._thread = Thread(target=self.recv,daemon=True)
        self._thread.start()
      
    def reboot(self,dst:int=0, timeout=5):
        evt = self._events[HKVAckPacket]
        evt_err = self._events[HKVNAckPacket]
        return self._write(evt, evt_err, SRC=99, DST=int(dst), TYPE="B", timeout=timeout)
    
    def hello(self,dst:int=0, timeout=5):
        evt = self._events[HKVHelloPacket]
        evt_err = self._events[HKVNAckPacket]
        return self._write(evt, evt_err, SRC=99, DST=int(dst), TYPE="H", HTYPE="R", timeout=timeout)
    
    def get_status(self,dst:int=0, timeout=30):
        evt = self._events[HKVStatusDataPacket]
        evt_err = self._events[HKVNAckPacket]
        return self._write(evt,evt_err,SRC=99, DST=int(dst), TYPE="S", STYPE="G", timeout=timeout)
    
    def get_connections(self,dst:int=0, timeout=30):
        evt = self._events[HKVConnectionDataPacket]
        evt_err = self._events[HKVNAckPacket]
        return self._write(evt,evt_err,SRC=99, DST=int(dst), TYPE="C", CTYPE="G", timeout=timeout)
    
    def add_connection(self,addr:int,stype:int,dst:int=0, timeout=30):
        evt = self._events[HKVAckPacket]
        evt_err = self._events[HKVNAckPacket]
        return self._write(evt,evt_err,SRC=99, DST=int(dst), TYPE="C", CTYPE="A", ADDR=int(addr), STYPE=int(stype), timeout=timeout)
    
    def remove_connection(self,addr:int,stype:int,dst:int=0, timeout=5):
        evt = self._events[HKVAckPacket]
        evt_err = self._events[HKVNAckPacket]
        return self._write(evt,evt_err,SRC=99, DST=int(dst), TYPE="C", CTYPE="A", ADDR=int(addr), STYPE=int(stype), timeout=timeout)
    
    def clear_connections(self,dst:int=0, timeout=5):
        evt = self._events[HKVAckPacket]
        evt_err = self._events[HKVNAckPacket]
        return self._write(evt,evt_err,SRC=99, DST=int(dst), TYPE="C", CTYPE="C", timeout=timeout)
    
    def get_relais(self,*chan,dst:int=0, timeout=30):
        '''
        Get relais states.
        ::param chan: the channels (all channels if empty)
        ::param dst: the destination device address (default: 0, the connected device) 
        '''
        evt_err = self._events[HKVNAckPacket]
        if len(chan):
            evt = self._events[HKVRelaisChannelPacket]
            res = []
            for c in chan:
                res.append(self._write(evt, evt_err, SRC=99, DST=int(dst), TYPE="R", RTYPE="G", CHAN=c, timeout=timeout))
            if len(res)>1:
                return res
            else:
                return res[0]
        else:
            evt = self._events[HKVRelaisDataPacket]
            return self._write(evt, evt_err, SRC=99, DST=int(dst), TYPE="R", RTYPE="G", timeout=timeout)
      
    def set_relais(self,*vals,dst:int=0, timeout=30):
        assert len(vals)>0
        evt = self._events[HKVAckPacket]
        evt_err = self._events[HKVNAckPacket]
        if len(vals)==1 and not isinstance(vals[0],Iterable):
            return self._write(evt, evt_err, SRC=99, DST=int(dst), TYPE="R", RTYPE="S", VAL=vals[0], timeout=timeout)
        else:
            chan = 0
            res = []
            for v in vals:
                if isinstance(v,Iterable):
                    chan, val = v[0],v[1]
                    if chan<1 or chan>6:
                        raise ValueError(f"Invalid channel number ({chan=}! Channel number must be in range [1,6].")
                else:
                    chan += 1
                    val = v
                res.append(self._write(evt, evt_err, SRC=99, DST=int(dst), TYPE="R", RTYPE="S", CHAN=chan, VAL=val, timeout=timeout))
            return res
    
    def calibrate_temps(self,dst:int=0, timeout=5):
        evt = self._events[HKVAckPacket]
        evt_err = self._events[HKVNAckPacket]
        return self._write(evt,evt_err,SRC=99, DST=int(dst), TYPE="T", TTYPE="C", timeout=timeout)
    
    def get_temps(self,*chan,dst:int=0, timeout=30):
        '''
        Get temperatures.
        ::param chan: the channels (all channels if empty)
        ::param dst: the destination device address (default: 0, the connected device) 
        '''
        evt_err = self._events[HKVNAckPacket]
        if len(chan):
            evt = self._events[HKVTempChannelPacket]
            res = []
            for c in chan:
                res.append(self._write(evt, evt_err, SRC=99, DST=int(dst), TYPE="T", TTYPE="G",CHAN=int(c), timeout=timeout))
            if len(res)>1:
                return res
            else:
                return res[0]
        else:
            evt = self._events[HKVTempDataPacket]
            return self._write(evt, evt_err, SRC=99, DST=int(dst), TYPE="T", TTYPE="G", timeout=timeout)
        
    def set_temps_transmit_period(self,delay=None,period=None,dst:int=0, timeout=30):
        kargs = {}
        if not delay is None: kargs['DELAY'] = int(delay)
        if not period is None: kargs['PERIOD'] = int(period)
        evt = self._events[HKVAckPacket]
        evt_err = self._events[HKVNAckPacket]
        return self._write(evt, evt_err, SRC=99, DST=int(dst), TYPE="T", TTYPE="P", timeout=timeout,**kargs)
        
    def set_temps_measure_period(self,delay=None,period=None,dst:int=0, timeout=30):
        kargs = {}
        if not delay is None: kargs['DELAY'] = int(delay)
        if not period is None: kargs['PERIOD'] = int(period)
        evt = self._events[HKVAckPacket]
        evt_err = self._events[HKVNAckPacket]
        return self._write(evt, evt_err, SRC=99, DST=int(dst), TYPE="T", TTYPE="M", timeout=timeout, **kargs)
      
    def _write(self, evt=None, *evt_err, timeout=30, **kw):
        data = json.dumps(kw)+'\r\n'
        n = self._dev.write(data.encode())
        #time.sleep(.1)
        _LOGGER.info(f"{n} bytes written.(data: {data}")
        if evt:
            evt.clear()
            if evt.wait(timeout=timeout):
                return len(data)==n, evt.param
            else:
                err_packets = []
                for e in evt_err:
                    if e.is_set():
                        err_packets.append(e.param)
                return False,err_packets if len(err_packets)>1 else err_packets[0] if len(err_packets)==1 else None
        return len(data)==n, None
      
if __name__=='__main__':
    import argparse,IPython
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev1",default="/dev/ttyUSB0", help="Serial device")
    parser.add_argument("--dev2",default=None, help="Serial device")
    args = parser.parse_args()
    
    hkv1 = HKV(name='1')
    hkv2 = HKV(name='2')
    if args.dev1:
        hkv1.connect(args.dev1)
    if args.dev2:
        hkv2.connect(args.dev2)
    #some_test_code(hkv1,hkv2)
    IPython.embed()
    
    
def some_test_code(hkv1,hkv2):
    
    #hkv1.connect('/dev/ttyUSB1')
    print(hkv1.hello())
    time.sleep(1)
    '''
    print(hkv1.set_relais(1))
    time.sleep(1)
    print(hkv1.set_relais(0))
    time.sleep(1)
    print(hkv1.set_relais((4,1),(5,1),(6,1)))
    time.sleep(1)
    print(hkv1.set_relais((1,1),(2,1),(3,1)))
    time.sleep(1)
    print(hkv1.set_relais(0))
    time.sleep(1)
    print(hkv1.connections())
    time.sleep(1)
    '''
    #print(hkv1.add_connection(6915625,2)) #D1 (HKV-Board)
    #print(hkv1.add_connection(5955124,2)) #ESP32 LORA (HKV-Board)
    
    #print(hkv1.add_connection(6915016,2)) #D1
    #print(hkv1.add_connection(6915683,2)) #D1
    #time.sleep(1)
    print(hkv1.connections())
    time.sleep(1)
    
    print(hkv1.get_temps(6915016))
    time.sleep(1)
    
    print(hkv1.get_temps(6915683))
    time.sleep(1)
    
    print(hkv1.get_temps(6915625))
    time.sleep(1)
    '''
    print(hkv1.get_temps())
    time.sleep(1)
    print(hkv1.get_temps(5955124))
    time.sleep(1)
    '''
