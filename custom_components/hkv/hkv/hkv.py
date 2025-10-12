import asyncio
import json
import logging
import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable, Iterable
from threading import Event

import serial_asyncio

from .packets import (
    HKVAckPacket,
    HKVConnectionDataPacket,
    HKVHelloPacket,
    HKVLogPacket,
    HKVNAckPacket,
    HKVPacket,
    HKVRelaisChannelPacket,
    HKVRelaisDataPacket,
    HKVStatusDataPacket,
    HKVTempChannelPacket,
    HKVTempDataPacket,
)

_LOGGER = logging.getLogger(__name__)

class HKV():

    def __init__(self, name='HKV', addr=99):
        self._reader = None
        self._writer = None
        self.name = name
        self._addr = addr
        self._events = {
            HKVLogPacket: Event(),
            HKVHelloPacket: Event(),
            HKVAckPacket: Event(),
            HKVNAckPacket: Event(),
            HKVTempChannelPacket: Event(),
            HKVRelaisChannelPacket: Event(),
            HKVTempDataPacket: Event(),
            HKVRelaisDataPacket: Event(),
            HKVConnectionDataPacket: Event(),
            HKVStatusDataPacket: Event(),
        }
        self._temp_data_event = Event()
        self._packets = deque(maxlen=10000)
        self._known_addr = []
        self._plock = threading.Lock()
        self._handler = {}
        self._block_handlers = False

    async def recv(self):
        while True:
            try:
                line = await self._reader.readline()
                line = line.decode().strip()
                if len(line) == 0: continue
                try:
                    packet = HKVPacket.from_doc(line)
                    if packet.SRC not in self._known_addr:
                        self._known_addr.append(packet.SRC)
                    if isinstance(packet, HKVLogPacket):
                        levels = defaultdict(lambda: logging.CRITICAL)
                        levels.update({'D': logging.DEBUG, 'I': logging.INFO, 'W': logging.WARNING, 'E': logging.ERROR})
                        logging.getLogger(f"{__name__}.SRC{packet.SRC}").log(levels[packet.LTYPE], f"{packet.MSG}")
                        continue
                    _LOGGER.debug(f"HKV-{self.name}: {packet}")
                    event = self._events.get(packet.__class__, None)
                    if event:
                        event.param = packet
                        event.set()
                    with self._plock:
                        self._packets.append(packet)

                    if self._block_handlers:
                        continue

                    for pt, handlers in self._handler.items():
                        if isinstance(packet, pt):
                            for h in handlers.copy():
                                h(packet)

                except Exception as e:
                    _LOGGER.error(f"RX{self.name}: {line=}")
                    _LOGGER.error(f"{e}", exc_info=False)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                _LOGGER.error(f"Recv error: {e}")
            await asyncio.sleep(0.1)

    def register_packet_handler(self, handler: Callable, packet_type: HKVPacket):
        handlers = self._handler.get(packet_type, [])
        if handler in handlers: return
        handlers.append(handler)
        self._handler[packet_type] = handlers

    async def packets_pop(self):
        with self._plock:
            packets = list(self._packets)
            self._packets.clear()
            return packets

    async def connect(self, port: str = '/dev/ttyUSB0', baud: int = 115200):
        self._reader, self._writer = await serial_asyncio.open_serial_connection(
            url=port, baudrate=baud, timeout=1
        )
        asyncio.create_task(self.recv())

    async def reboot(self, dst: int = 0, timeout=10):
        evt = self._events[HKVAckPacket]
        evt_err = self._events[HKVNAckPacket]
        return await self._write(evt, evt_err, SRC=self._addr, DST=int(dst), TYPE="B", timeout=timeout)

    async def hello(self, dst: int = 0, timeout=10):
        evt = self._events[HKVHelloPacket]
        evt_err = self._events[HKVNAckPacket]
        return await self._write(evt, evt_err, SRC=self._addr, DST=int(dst), TYPE="H", HTYPE="R", timeout=timeout)

    async def get_status(self, dst: int = 0, timeout=5):
        evt = self._events[HKVStatusDataPacket]
        evt_err = self._events[HKVNAckPacket]
        return await self._write(evt, evt_err, SRC=self._addr, DST=int(dst), TYPE="S", STYPE="G", timeout=timeout)

    async def get_connections(self, dst: int = 0, timeout=5):
        evt = self._events[HKVConnectionDataPacket]
        evt_err = self._events[HKVNAckPacket]
        return await self._write(evt, evt_err, SRC=self._addr, DST=int(dst), TYPE="C", CTYPE="G", timeout=timeout)

    async def add_connection(self, addr: int, stype: int, dst: int = 0, timeout=5):
        evt = self._events[HKVAckPacket]
        evt_err = self._events[HKVNAckPacket]
        return await self._write(evt, evt_err, SRC=self._addr, DST=int(dst), TYPE="C", CTYPE="A", ADDR=int(addr), STYPE=int(stype), timeout=timeout)

    async def remove_connection(self, addr: int, stype: int, dst: int = 0, timeout=5):
        evt = self._events[HKVAckPacket]
        evt_err = self._events[HKVNAckPacket]
        return await self._write(evt, evt_err, SRC=self._addr, DST=int(dst), TYPE="C", CTYPE="R", ADDR=int(addr), STYPE=int(stype), timeout=timeout)

    async def clear_connections(self, dst: int = 0, timeout=5):
        evt = self._events[HKVAckPacket]
        evt_err = self._events[HKVNAckPacket]
        return await self._write(evt, evt_err, SRC=self._addr, DST=int(dst), TYPE="C", CTYPE="C", timeout=timeout)

    async def get_relais(self, *chan, dst: int = 0, timeout=5):
        evt_err = self._events[HKVNAckPacket]
        if len(chan):
            evt = self._events[HKVRelaisChannelPacket]
            res = []
            for c in chan:
                res.append(await self._write(evt, evt_err, SRC=self._addr, DST=int(dst), TYPE="R", RTYPE="G", CHAN=c, timeout=timeout))
            return res if len(res) > 1 else res[0]
        else:
            evt = self._events[HKVRelaisDataPacket]
            return await self._write(evt, evt_err, SRC=self._addr, DST=int(dst), TYPE="R", RTYPE="G", timeout=timeout)

    async def set_relais(self, *vals, dst: int = 0, timeout=5):
        assert len(vals) > 0
        evt = self._events[HKVAckPacket]
        evt_err = self._events[HKVNAckPacket]
        if len(vals) == 1 and not isinstance(vals[0], Iterable):
            return await self._write(evt, evt_err, SRC=self._addr, DST=int(dst), TYPE="R", RTYPE="S", VAL=vals[0], timeout=timeout)
        else:
            res = []
            chan = 0
            for v in vals:
                if isinstance(v, Iterable):
                    chan, val = v[0], v[1]
                else:
                    chan += 1
                    val = v
                res.append(await self._write(evt, evt_err, SRC=self._addr, DST=int(dst), TYPE="R", RTYPE="S", CHAN=chan, VAL=val, timeout=timeout))
            return res

    async def calibrate_temps(self, dst: int = 0, timeout=5):
        evt = self._events[HKVAckPacket]
        evt_err = self._events[HKVNAckPacket]
        return await self._write(evt, evt_err, SRC=self._addr, DST=int(dst), TYPE="T", TTYPE="C", timeout=timeout)

    async def get_temps(self, *chan, dst: int = 0, timeout=5):
        evt_err = self._events[HKVNAckPacket]
        if len(chan):
            evt = self._events[HKVTempChannelPacket]
            res = []
            for c in chan:
                res.append(await self._write(evt, evt_err, SRC=self._addr, DST=int(dst), TYPE="T", TTYPE="G", CHAN=int(c), timeout=timeout))
            return res if len(res) > 1 else res[0]
        else:
            evt = self._events[HKVTempDataPacket]
            return await self._write(evt, evt_err, SRC=self._addr, DST=int(dst), TYPE="T", TTYPE="G", timeout=timeout)

    async def set_temps_transmit_period(self, delay=None, period=None, dst: int = 0, timeout=5):
        kargs = {}
        if delay is not None: kargs['DELAY'] = int(delay)
        if period is not None: kargs['PERIOD'] = int(period)
        evt = self._events[HKVAckPacket]
        evt_err = self._events[HKVNAckPacket]
        return await self._write(evt, evt_err, SRC=self._addr, DST=int(dst), TYPE="T", TTYPE="P", timeout=timeout, **kargs)

    async def set_temps_measure_period(self, delay=None, period=None, dst: int = 0, timeout=5):
        kargs = {}
        if delay is not None: kargs['DELAY'] = int(delay)
        if period is not None: kargs['PERIOD'] = int(period)
        evt = self._events[HKVAckPacket]
        evt_err = self._events[HKVNAckPacket]
        return await self._write(evt, evt_err, SRC=self._addr, DST=int(dst), TYPE="T", TTYPE="M", timeout=timeout, **kargs)

    async def _write(self, evt=None, evt_err=None, timeout=5, **kw):
        data = json.dumps(kw) + '\n'
        return await self._write_raw(data, evt=evt, evt_err=evt_err, timeout=timeout)

    async def _write_raw(self, data, evt=None, evt_err=None, timeout=5):
        retry = 3
        while retry > 0:
            try:
                self._writer.write(data.encode())
                await self._writer.drain()
                _LOGGER.info(f"{len(data)} bytes written. (data: {data}")
                if evt:
                    evt.clear()
                    if evt_err is None:
                        evt_err = self._events[HKVNAckPacket]
                    evt_err.clear()
                    try:
                        done, pending = await asyncio.wait(
                            [asyncio.create_task(evt.wait()), asyncio.create_task(evt_err.wait())],
                            timeout=timeout, return_when=asyncio.FIRST_COMPLETED
                        )
                        for p in pending:
                            p.cancel()
                        if evt.is_set():
                            return True, evt.param
                        elif evt_err.is_set():
                            return False, evt_err.param
                    except asyncio.TimeoutError:
                        _LOGGER.warning("Write timeout")
                return False, None
            except Exception as e:
                _LOGGER.error(f"Write error: {e}")
                retry -= 1
                await asyncio.sleep(2 ** (3 - retry))  # Exponential backoff
        return False, None

# Rest des Codes (if __name__ == '__main__': ...) bleibt gleich
      
if __name__=='__main__':
    import argparse

    import IPython
    logging.basicConfig(level='DEBUG')
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev1",default="/dev/ttyUSB0", help="Serial device")
    parser.add_argument("--dev2",default=None, help="Serial device")
    parser.add_argument("--baud1",type=int,default=115200, help="Serial baudrate")
    parser.add_argument("--baud2",type=int,default=115200, help="Serial baudrate")
    parser.add_argument("--addr",type=int,default=99, help="Address of this node")
    args = parser.parse_args()
    
    hkv1 = HKV(name='1',addr=args.addr)
    hkv2 = HKV(name='2',addr=args.addr)
    if args.dev1:
        hkv1.connect(args.dev1,baud=args.baud1)
    if args.dev2:
        hkv2.connect(args.dev2,baud=args.baud2)
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
