'''
Created on Dec 31, 2022

@author: holger
'''
import threading
from .hkv.hkv import HKV
import logging
from .hkv.packets import HKVHelloPacket,\
    HKVDataPacket, HKVTempDataPacket
from queue import Empty
from collections import OrderedDict, defaultdict
from dataclasses import asdict

_LOGGER = logging.getLogger(__name__)


class HKVHub:
    """Placeholder class to make tests pass.

    TODO Remove this placeholder class and replace with things from your PyPI package.
    """

    def __init__(self, dev: str, baud: int) -> None:
        """Initialize."""
        self.dev = dev
        self.baud = baud
        self._lock = threading.Lock()
        self.hkv = HKV()
        
    def connect(self):
        self.hkv.connect(port=self.dev)
        _LOGGER.info(f"hello: {self.hkv.hello(dst=-1, timeout=20)}")
        #TODO: register temps handler
        
        #_LOGGER.info(f"set temps measure interval: {self.hkv.set_temps_measure_period(delay=1000, period=30000, dst=-1, timeout=20)}")
        #_LOGGER.info(f"set temps transmit interval: {self.hkv.set_temps_transmit_period(delay=1000, period=30000, dst=-1, timeout=20)}")
        _LOGGER.info(f"set temps measure interval: {self.hkv.set_temps_measure_period(delay=0, period=0, dst=-1, timeout=10)}")
        _LOGGER.info(f"set temps transmit interval: {self.hkv.set_temps_transmit_period(delay=0, period=0, dst=-1, timeout=10)}")
        #_LOGGER.info(f"conn: {self.hkv.get_connections(dst=-1)}")
        
    async def scan_connected_devices(self):
        _LOGGER.error(f"scan_connected_devices: ...")
        devices={}
        # for addr in self.hkv._known_addr:
        #     ack,pack = await hass.async_add_executor_job(self.hkv.hello,addr) #(dst=addr)
        #     if ack:
        #         devices[addr] = {
        #             'ID': pack.ID,
        #             #'temps':self.hkv.get_temps(dst=addr)[1],
        #             #'relais':self.hkv.get_relais(dst=addr)[1],
        #             #'connections':self.hkv.get_connections(dst=addr)[1],
        #             }
        #         #ack,tpack = self.hkv.get_temps(dst=addr)
        #         #if ack:
        #         #    devices[addr].update(asdict(tpack))
        #         #ack,rpack = self.hkv.get_relais(dst=addr)
        #         #if ack:
        #         #    devices[addr].update(asdict(rpack))
        #     _LOGGER.info(f"{addr=}: {devices[addr]=}")
        return {"devices": devices}
        
    async def fetch_data(self, hass):
                        
        self.hkv._block_handlers = True
        
        devices = OrderedDict()
        
        def defaultdevdata():
            return OrderedDict(
                ID='UNKNOWN',
                # DISPLAY=dict(USED=False, READY=False),
                # USB=dict(USED=False, READY=False),
                # LORA=dict(USED=False, READY=False),
                # RELAIS=dict(USED=False, READY=False),
                # SENSOR=dict(USED=False, READY=False, SNUM=14,**{f"ADDR{i}":0 for i in range(14)}),
                SNUM=0,
                MCNT=0,
                RNUM=0,
                CCNT=0,
                **{f"Temp{i+1}":0.0 for i in range(14)},
                **{f"Relais{i+1}":False for i in range(6)},
                temp_transmit_interval=30000,
                temp_measure_interval=30000,
                )
        try:
            dev = defaultdevdata()
            #dev = {'temp_transmit_interval':30000,'temp_measure_interval':30000,'CNT':None}
            success = False
            while not success:
                success,state_pck = self.hkv.get_status(dst=0,timeout=10)
            _LOGGER.warning(state_pck)
            if state_pck is not None:
                devices[state_pck.SRC] = dev
                dev['ID'] = state_pck.ID
                dev['MSEC'] = state_pck.MSEC
                dev['SNUM'] = state_pck.SNUM
                dev['MCNT'] = state_pck.MCNT
                dev['RNUM'] = state_pck.RNUM
                dev['CCNT'] = state_pck.CCNT
                # dev['DISPLAY'] = state_pck.DISPLAY
                # dev['USB'] = state_pck.USB
                # dev['LORA'] = state_pck.LORA
                # dev['RELAIS'] = state_pck.RELAIS
                # dev['SENSOR'] = state_pck.SENSOR
            
            success = False
            while not success:
                success,temps_pck = self.hkv.get_temps(dst=0,timeout=10)
            _LOGGER.warning(temps_pck)
            if temps_pck is not None:
                dev['SNUM'] = temps_pck.SNUM
                dev['MCNT'] = temps_pck.MCNT
                dev['TDATA'] = temps_pck.TDATA
                for ii in range(dev['SNUM']):
                    tempi = f"Temp{ii+1}"
                    temp = dev['TDATA'][ii]
                    if temp:
                        dev[tempi] = temp
                    else:
                        print(f"{tempi} not present")
                        dev[tempi] = None
            success = False
            while not success:
                success,relais_pck = self.hkv.get_relais(dst=0,timeout=10)
            _LOGGER.warning(relais_pck)
            if relais_pck is not None:
                dev['RNUM'] = relais_pck.RNUM
                dev['RDATA'] = relais_pck.RDATA
                for ii in range(dev['RNUM']):
                    reli = f"Relais{ii+1}"
                    rel = dev['RDATA'][ii]
                    if not rel is None:
                        dev[reli] = rel
                    else:
                        print(f"{reli} not present")
                        continue
            success = False
            while not success:
                success,conn_pck = self.hkv.get_connections(dst=0,timeout=10) # HKV-Base
        except Exception as e:
            _LOGGER.critical(e,exc_info=True)
        if conn_pck:
            try:
                
                for i in range(conn_pck.CCNT):
                    addr = conn_pck.CDATA[i]['ADDR']
                    if addr and addr not in [0,99]:
                        dev = defaultdevdata()
                        #dev = {'temp_transmit_interval':30000,'temp_measure_interval':30000,'CNT':None}
                        devices[addr] = dev
                        success = False
                        while not success:
                            success,state_pck = self.hkv.get_status(dst=addr,timeout=10)
                        _LOGGER.warning(f"{state_pck=}")
                        if state_pck is not None:
                            dev['ID'] = state_pck.ID
                            dev['MSEC'] = state_pck.MSEC
                            dev['SNUM'] = state_pck.SNUM
                            dev['MCNT'] = state_pck.MCNT
                            dev['RNUM'] = state_pck.RNUM
                            dev['CCNT'] = state_pck.CCNT
                            # dev['DISPLAY'] = state_pck.DISPLAY
                            # dev['USB'] = state_pck.USB
                            # dev['LORA'] = state_pck.LORA
                            # dev['RELAIS'] = state_pck.RELAIS
                            # dev['SENSOR'] = state_pck.SENSOR
                        success = False
                        while not success:
                            success,temps_pck = self.hkv.get_temps(dst=addr,timeout=10)
                        _LOGGER.warning(f"{temps_pck=}")
                        if temps_pck is not None:
                            dev['SNUM'] = temps_pck.SNUM
                            dev['MCNT'] = temps_pck.MCNT
                            dev['TDATA'] = temps_pck.TDATA
                            for ii in range(dev['SNUM']):
                                tempi = f"Temp{ii+1}"
                                temp = dev['TDATA'][ii]
                                if temp:
                                    dev[tempi] = temp
                                else:
                                    print(f"{tempi} not present")
                                    dev[tempi] = None
                        success = False
                        while not success:
                            success,relais_pck = self.hkv.get_relais(dst=addr,timeout=10)
                        _LOGGER.warning(f"{relais_pck=}")
                        if relais_pck is not None:
                            dev['RNUM'] = relais_pck.RNUM
                            dev['RDATA'] = relais_pck.RDATA
                            for ii in range(dev['RNUM']):
                                reli = f"Relais{ii+1}"
                                rel = dev['RDATA'][ii]
                                if not rel is None:
                                    dev[reli] = rel
                                else:
                                    print(f"{reli} not present")
                                    continue
            except Exception as e:
                _LOGGER.error(e)
                
        self.hkv._block_handlers = False
            
        _LOGGER.warning(f"set temps measure interval: {self.hkv.set_temps_measure_period(delay=1000, period=30000, dst=-1, timeout=10)}")
        _LOGGER.warning(f"set temps transmit interval: {self.hkv.set_temps_transmit_period(delay=2000, period=30000, dst=-1, timeout=10)}")
        
        return {"devices": devices}
        
    
