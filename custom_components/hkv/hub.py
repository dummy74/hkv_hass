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
        
        _LOGGER.info(f"set temps measure interval: {self.hkv.set_temps_measure_period(delay=1000, period=30000, dst=-1, timeout=20)}")
        _LOGGER.info(f"set temps transmit interval: {self.hkv.set_temps_transmit_period(delay=1000, period=30000, dst=-1, timeout=20)}")
        #_LOGGER.info(f"set temps measure interval: {self.hkv.set_temps_measure_period(delay=0, period=0, dst=-1, timeout=10)}")
        #_LOGGER.info(f"set temps transmit interval: {self.hkv.set_temps_transmit_period(delay=0, period=0, dst=-1, timeout=10)}")
        #_LOGGER.info(f"conn: {self.hkv.get_connections(dst=-1)}")
        
    async def scan_connected_devices(self):
        devices={}
        # for addr in self.hkv._known_addr:
        #     ack,pack = self.hkv.hello(dst=addr)
        #     if ack:
        #         devices[addr] = {
        #             'id': pack.ID,
        #             # 'temps':self.hkv.get_temps(dst=addr)[1],
        #             # 'relais':self.hkv.get_relais(dst=addr)[1],
        #             # 'connections':self.hkv.get_connections(dst=addr)[1],
        #             }
        # _LOGGER.info(f"data: {devices=}")
        return {"devices": devices}
        
    async def fetch_data(self):
                        
        devices = OrderedDict()
        def defaultdevdata():
            return dict(
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
        
        _,state_pck = self.hkv.get_status(dst=0,timeout=20)
        _LOGGER.warning(state_pck)
        if state_pck is not None:
            dev['ID'] = state_pck.ID
            dev['DISPLAY'] = state_pck.DISPLAY
            dev['USB'] = state_pck.USB
            dev['LORA'] = state_pck.LORA
            dev['RELAIS'] = state_pck.RELAIS
            dev['SENSOR'] = state_pck.SENSOR
        
        _,temps_pck = self.hkv.get_temps(dst=0,timeout=20)
        _LOGGER.warning(temps_pck)
        if temps_pck is not None:
            dev['CNT'] = temps_pck.CNT
            devices[temps_pck.SRC] = dev
            num = state_pck.SENSOR['NUM']
            for ii in range(num):
                tempi = f"Temp{ii+1}"
                temp = getattr(temps_pck,tempi,None)
                if temp:
                    dev[tempi] = temp
                else:
                    print(f"{tempi} not present")
                    dev[tempi] = None
        _,relais_pck = self.hkv.get_relais(dst=0,timeout=20)
        _LOGGER.warning(relais_pck)
        if relais_pck is not None:
        #dev['ID'] = relais_pck.ID
            for ii in range(6):
                reli = f"Relais{ii+1}"
                rel = getattr(relais_pck,reli,None)
                if not rel is None:
                    dev[reli] = rel
                else:
                    print(f"{reli} not present")
                    continue
        _,conn_pck = self.hkv.get_connections(dst=0,timeout=20) # HKV-Base
        if conn_pck:
            _LOGGER.warning(conn_pck)
            try:
                for i in range(10):
                    addri = f"ADDR{i}"
                    addr = getattr(conn_pck,addri,None)
                    if addr and addr!=99:
                        dev = defaultdevdata()
                        #dev = {'temp_transmit_interval':30000,'temp_measure_interval':30000,'CNT':None}
                        devices[addr] = dev
                        _,state_pck = self.hkv.get_status(dst=addr,timeout=20)
                        _LOGGER.warning(state_pck)
                        if state_pck is not None:
                            dev['ID'] = state_pck.ID
                            dev['DISPLAY'] = state_pck.DISPLAY
                            dev['USB'] = state_pck.USB
                            dev['LORA'] = state_pck.LORA
                            dev['RELAIS'] = state_pck.RELAIS
                            dev['SENSOR'] = state_pck.SENSOR
                        _,temps_pck = self.hkv.get_temps(dst=addr,timeout=20)
                        _LOGGER.warning(temps_pck)
                        if temps_pck is not None:
                            dev['ID'] = temps_pck.ID
                            dev['CNT'] = temps_pck.CNT
                            num = state_pck.SENSOR['NUM']
                            for ii in range(num):
                                tempi = f"Temp{ii+1}"
                                temp = getattr(temps_pck,tempi,None)
                                if temp:
                                    dev[tempi] = temp
                                else:
                                    print(f"{tempi} not present")
                                    dev[tempi] = None
                        _,relais_pck = self.hkv.get_relais(dst=addr,timeout=20)
                        _LOGGER.warning(relais_pck)
                        if relais_pck is not None:
                            #dev['ID'] = relais_pck.ID
                            for ii in range(6):
                                reli = f"Relais{ii+1}"
                                rel = getattr(relais_pck,reli,None)
                                if not rel is None:
                                    dev[reli] = rel
                                else:
                                    print(f"{reli} not present")
                                    continue
            except: pass
            
        #_LOGGER.warning(f"set temps measure interval: {self.hkv.set_temps_measure_period(delay=1000, period=30000, dst=-1, timeout=20)}")
        #_LOGGER.warning(f"set temps transmit interval: {self.hkv.set_temps_transmit_period(delay=1000, period=30000, dst=-1, timeout=20)}")
        
        return {"devices": devices}
        
    
