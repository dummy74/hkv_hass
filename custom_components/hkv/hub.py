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
        for addr in self.hkv._known_addr:
            ack,pack = await hass.async_add_executor_job(self.hkv.hello,addr) #(dst=addr)
            if ack:
                devices[addr] = {
                    'ID': pack.ID,
                    #'temps':self.hkv.get_temps(dst=addr)[1],
                    #'relais':self.hkv.get_relais(dst=addr)[1],
                    #'connections':self.hkv.get_connections(dst=addr)[1],
                    }
                #ack,tpack = self.hkv.get_temps(dst=addr)
                #if ack:
                #    devices[addr].update(asdict(tpack))
                #ack,rpack = self.hkv.get_relais(dst=addr)
                #if ack:
                #    devices[addr].update(asdict(rpack))
        _LOGGER.info(f"{addr=}: {devices[addr]=}")
        return {"devices": devices}
        
    async def fetch_data(self, hass):
                        
        devices = OrderedDict()
        def defaultdevdata():
            return OrderedDict(
                ID='UNKNOWN',
                #DISPLAY=dict(USED=False, READY=False),
                #USB=dict(USED=False, READY=False),
                #LORA=dict(USED=False, READY=False),
                #RELAIS=dict(USED=False, READY=False),
                #SENSOR=dict(USED=False, READY=False, NUM=0,),#**{f"ADDR{i}":0 for i in range(14)}),
                CNT=None,
                #**{f"Temp{i+1}":0.0 for i in range(14)},
                #**{f"Relais{i+1}":False for i in range(6)},
                temp_transmit_interval=30000,
                temp_measure_interval=30000,
                )
        
        dev = defaultdevdata()
        #dev = {'temp_transmit_interval':30000,'temp_measure_interval':30000,'CNT':None}
        
        state_pck = None; retry = 5
        while state_pck is None and retry:
            retry -= 1
            _,state_pck = await hass.async_add_executor_job(self.hkv.get_status,0,60)#dst=0,timeout=60)
            _LOGGER.warning(f"0:{retry=}:{state_pck=}")
        if state_pck is not None:
            dev.update(asdict(state_pck))
        
        temps_pck = None; retry = 5
        while temps_pck is None and retry:
            retry -= 1
            _,temps_pck = await hass.async_add_executor_job(self.hkv.get_temps,0,60)#dst=0,timeout=60)
            _LOGGER.warning(f"0:{retry=}:{temps_pck=}")
        if temps_pck is not None:
            dev.update(asdict(temps_pck))
        relais_pck = None; retry = 5
        while relais_pck is None and retry:
            retry -= 1
            _,relais_pck = await hass.async_add_executor_job(self.hkv.get_relais,0,60)#dst=0,timeout=60)
            _LOGGER.warning(f"0:{retry=}:{relais_pck=}")
        if relais_pck is not None:
            dev.update(asdict(relais_pck))
        conn_pck = None; retry = 5
        while conn_pck is None and retry:
            retry -= 1
            _,conn_pck = await hass.async_add_executor_job(self.hkv.get_connections,0,60)#dst=0,timeout=60) # HKV-Base
            _LOGGER.warning(f"0:{retry=}:{conn_pck=}")
        if conn_pck:
            try:
                for i in range(10):
                    addri = f"ADDR{i}"
                    addr = getattr(conn_pck,addri,None)
                    if addr and addr!=99:
                        dev = defaultdevdata()
                        #dev = {'temp_transmit_interval':30000,'temp_measure_interval':30000,'CNT':None}
                        devices[addr] = dev
                        state_pck = None; retry = 5
                        while state_pck is None and retry:
                            retry -= 1
                            _,state_pck = await hass.async_add_executor_job(self.hkv.get_status,addr,10)#dst=addr,timeout=10)
                            _LOGGER.warning(f"{addr}:{retry=}:{state_pck=}")
                        if state_pck is not None:
                            dev.update(asdict(state_pck))
                        
                        temps_pck = None; retry = 5
                        while temps_pck is None and retry:
                            retry -= 1
                            _,temps_pck = await hass.async_add_executor_job(self.hkv.get_temps,addr,10)#dst=addr,timeout=10)
                            _LOGGER.warning(f"{addr}:{retry=}:{temps_pck}")
                        if temps_pck is not None:
                            dev.update(asdict(temps_pck))
                        
                        relais_pck = None; retry = 5
                        while relais_pck is None and retry:
                            retry -= 1
                            _,relais_pck = await hass.async_add_executor_job(self.hkv.get_relais,addr,10)#dst=addr,timeout=10)
                            _LOGGER.warning(f"{addr}:{retry=}:{relais_pck}")
                        if relais_pck is not None:
                            dev.update(asdict(relais_pck))
            except: pass
            
        _LOGGER.warning(f"set temps measure interval: {await hass.async_add_executor_job(self.hkv.set_temps_measure_period,1000,30000,-1,20)}") #(delay=1000, period=30000, dst=-1, timeout=20)}")
        _LOGGER.warning(f"set temps transmit interval: {await hass.async_add_executor_job(self.hkv.set_temps_transmit_period,1000,30000,-1,20)}") #(delay=1000, period=30000, dst=-1, timeout=20)}")
        
        return {"devices": devices}
        
    
