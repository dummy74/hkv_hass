'''
Created on Dec 31, 2022

@author: holger
'''
import threading
import asyncio
from .hkv.hkv import HKV
import logging
from .hkv.packets import HKVHelloPacket, HKVDataPacket, HKVTempDataPacket
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

    async def connect(self):
        await self.hkv.connect(port=self.dev)
        _LOGGER.info(f"hello: {await self.hkv.hello(dst=-1, timeout=20)}")
        # TODO: register temps handler

        # Set intervals only on startup
        await self.hkv.set_temps_measure_period(delay=0, period=0, dst=-1, timeout=10)
        await self.hkv.set_temps_transmit_period(delay=0, period=0, dst=-1, timeout=10)

    async def scan_connected_devices(self):
        _LOGGER.error(f"scan_connected_devices: ...")
        devices = {}
        return {"devices": devices}

    async def fetch_data(self, hass):
        self.hkv._block_handlers = True
        devices = OrderedDict()

        def defaultdevdata():
            return OrderedDict(
                ID='UNKNOWN',
                SNUM=0,
                MCNT=0,
                RNUM=0,
                CCNT=0,
                **{f"Temp{i+1}": 0.0 for i in range(14)},
                **{f"Relais{i+1}": False for i in range(6)},
                temp_transmit_interval=30000,
                temp_measure_interval=30000,
            )

        try:
            dev = defaultdevdata()
            # # Parallel queries for base device (dst=0)
            # tasks = [
            #     self.hkv.get_status(dst=0, timeout=5),
            #     self.hkv.get_temps(dst=0, timeout=5),
            #     self.hkv.get_relais(dst=0, timeout=5),
            #     self.hkv.get_connections(dst=0, timeout=5)
            # ]
            # results = await asyncio.gather(*tasks, return_exceptions=True)

            # state_pck = results[0][1] if isinstance(results[0], tuple) and results[0][0] else None
            # temps_pck = results[1][1] if isinstance(results[1], tuple) and results[1][0] else None
            # relais_pck = results[2][1] if isinstance(results[2], tuple) and results[2][0] else None
            # conn_pck = results[3][1] if isinstance(results[3], tuple) and results[3][0] else None

            success = False
            while not success:
                success, state_pck = await self.hkv.get_status(dst=0, timeout=10)

            if state_pck:
                devices[state_pck.SRC] = dev
                dev['ID'] = state_pck.ID
                dev['MSEC'] = state_pck.MSEC
                dev['SNUM'] = state_pck.SNUM
                dev['MCNT'] = state_pck.MCNT
                dev['RNUM'] = state_pck.RNUM
                dev['CCNT'] = state_pck.CCNT

            success = False
            while not success:
                success, temps_pck = await self.hkv.get_temps(dst=0, timeout=10)

            if temps_pck:
                dev['SNUM'] = temps_pck.SNUM
                dev['MCNT'] = temps_pck.MCNT
                dev['TDATA'] = temps_pck.TDATA
                for ii in range(dev['SNUM']):
                    tempi = f"Temp{ii+1}"
                    temp = dev['TDATA'][ii]
                    dev[tempi] = temp if temp else None
                    
            success = False
            while not success:
                success, relais_pck = await self.hkv.get_relais(dst=0, timeout=10)

            if relais_pck:
                dev['RNUM'] = relais_pck.RNUM
                dev['RDATA'] = relais_pck.RDATA
                for ii in range(dev['RNUM']):
                    reli = f"Relais{ii+1}"
                    rel = dev['RDATA'][ii]
                    dev[reli] = rel if rel is not None else None

            success = False
            while not success:
                success, conn_pck = await self.hkv.get_connections(dst=0, timeout=10)

            # Handle connections
            if conn_pck:
                query_tasks = []
                for i in range(conn_pck.CCNT):
                    addr = conn_pck.CDATA[i]['ADDR']
                    if addr and addr not in [0, 99]:
                        dev = defaultdevdata()
                        devices[addr] = dev
                        query_tasks.append(self._query_device(addr, dev))
                if query_tasks:
                    await asyncio.gather(*query_tasks, return_exceptions=True)

        except Exception as e:
            _LOGGER.critical(e, exc_info=True)

        self.hkv._block_handlers = False

        # Set intervals less frequently
        await self.hkv.set_temps_measure_period(delay=1000, period=30000, dst=-1, timeout=10)
        await self.hkv.set_temps_transmit_period(delay=2000, period=30000, dst=-1, timeout=10)

        return {"devices": devices}

    async def _query_device(self, addr, dev):
        # tasks = [
        #     self.hkv.get_status(dst=addr, timeout=5),
        #     self.hkv.get_temps(dst=addr, timeout=5),
        #     self.hkv.get_relais(dst=addr, timeout=5)
        # ]
        # results = await asyncio.gather(*tasks, return_exceptions=True)

        # state_pck = results[0][1] if isinstance(results[0], tuple) and results[0][0] else None
        # temps_pck = results[1][1] if isinstance(results[1], tuple) and results[1][0] else None
        # relais_pck = results[2][1] if isinstance(results[2], tuple) and results[2][0] else None
        
        success = False
        while not success:
            success, state_pck = await self.hkv.get_status(dst=addr, timeout=10)

        if state_pck:
            dev['ID'] = state_pck.ID
            dev['MSEC'] = state_pck.MSEC
            dev['SNUM'] = state_pck.SNUM
            dev['MCNT'] = state_pck.MCNT
            dev['RNUM'] = state_pck.RNUM
            dev['CCNT'] = state_pck.CCNT

        success = False
        while not success:
            success, temps_pck = await self.hkv.get_temps(dst=addr, timeout=10)

        if temps_pck:
            dev['SNUM'] = temps_pck.SNUM
            dev['MCNT'] = temps_pck.MCNT
            dev['TDATA'] = temps_pck.TDATA
            for ii in range(dev['SNUM']):
                tempi = f"Temp{ii+1}"
                temp = dev['TDATA'][ii]
                dev[tempi] = temp if temp else None

        success = False
        while not success:
            success, relais_pck = await self.hkv.get_relais(dst=addr, timeout=10)

        if relais_pck:
            dev['RNUM'] = relais_pck.RNUM
            dev['RDATA'] = relais_pck.RDATA
            for ii in range(dev['RNUM']):
                reli = f"Relais{ii+1}"
                rel = dev['RDATA'][ii]
                dev[reli] = rel if rel is not None else None