import json
from dataclasses import dataclass,InitVar,fields,field

@dataclass
class HKVPacket():
    data:InitVar[dict]
    SRC:int=field(init=False)
    DST:int=field(init=False)
    TYPE:str=field(init=False)
    EXTRA_DATA:dict=field(init=False)
  
    def __post_init__(self,data):
        #print(f"HKVPacket.__post_init__: {data}")
        self.EXTRA_DATA = data.copy()
        for f in fields(self):
            if f.name in data:
                setattr(self,f.name,data[f.name])
                self.EXTRA_DATA.pop(f.name)
        
    @staticmethod
    def from_doc(doc:str):
        data = json.loads(doc)
        return HKVPacket.from_data(data)
    @classmethod
    def from_data(cls,data):
        if data['TYPE']=='L':
            return HKVLogPacket.from_data(data)
        elif data['TYPE']=='A':
            return HKVAckPacket.from_data(data)
        elif data['TYPE']=='N':
            return HKVNAckPacket.from_data(data)
        elif data['TYPE']=='H':
            return HKVHelloPacket.from_data(data)
        elif data['TYPE']=='D':
            return HKVDataPacket.from_data(data)
        elif data['TYPE']=='R':
            return HKVRelaisChannelPacket.from_data(data)
        elif data['TYPE']=='T':
            return HKVTempChannelPacket.from_data(data)
        else:
            return cls(data)
        
    def __repr__(self):
        return f"{self.__class__.__name__}({', '.join([f.name+'='+getattr(self,f.name) for f in fields(self) if not getattr(self,f.name) is None])})"
    
@dataclass
class HKVAckPacket(HKVPacket):
    @classmethod
    def from_data(cls,data):
        return cls(data)
    
@dataclass
class HKVNAckPacket(HKVPacket):
    @classmethod
    def from_data(cls,data):
        return cls(data)
    
@dataclass
class HKVHelloPacket(HKVPacket):
    HTYPE:str=field(init=False)
    @classmethod
    def from_data(cls,data):
        return cls(data)
    
@dataclass
class HKVLogPacket(HKVPacket):
    LTYPE:str=field(init=False)
    MSG:str=field(init=False)
    @classmethod
    def from_data(cls,data):
        return cls(data)
    def __str__(self):
        return f"{self.LTYPE}::{self.SRC}: {self.MSG}"
    
@dataclass
class HKVChannelPacket(HKVPacket):
    ID:str=field(init=False)
    CHAN:int=field(init=False)
    VAL:float=field(init=False)
    @classmethod
    def from_data(cls,data):
        return cls(data)
    
@dataclass
class HKVTempChannelPacket(HKVChannelPacket):
    TTYPE:str=field(init=False)
    CNT:int=field(init=False)
    @classmethod
    def from_data(cls,data):
        return cls(data)
        
#'{"SRC":5955124,"DST":99,"TYPE":"R","RTYPE":"A","ID":"HKV-EG","CHAN":6,"VAL":1}'
@dataclass
class HKVRelaisChannelPacket(HKVChannelPacket):
    RTYPE:str=field(init=False)
    @classmethod
    def from_data(cls,data):
        return cls(data)
    
@dataclass
class HKVDataPacket(HKVPacket):
    DTYPE:str=field(init=False)
    ID:str=field(init=False)
    @classmethod
    def from_data(cls,data):
        if data['DTYPE']=='S':
            return HKVStatusDataPacket.from_data(data)
        elif data['DTYPE']=='T':
            return HKVTempDataPacket.from_data(data)
        elif data['DTYPE']=='R':
            return HKVRelaisDataPacket.from_data(data)
        elif data['DTYPE']=='C':
            return HKVConnectionDataPacket.from_data(data)
        else:
            return cls(data)
        
@dataclass
class HKVTempDataPacket(HKVDataPacket):
    CNT:int=field(init=False,default=None)
    Temp1:float=field(init=False,default=None)
    Temp2:float=field(init=False,default=None)
    Temp3:float=field(init=False,default=None)
    Temp4:float=field(init=False,default=None)
    Temp5:float=field(init=False,default=None)
    Temp6:float=field(init=False,default=None)
    Temp7:float=field(init=False,default=None)
    Temp8:float=field(init=False,default=None)
    Temp9:float=field(init=False,default=None)
    Temp10:float=field(init=False,default=None)
    Temp11:float=field(init=False,default=None)
    Temp12:float=field(init=False,default=None)
    Temp13:float=field(init=False,default=None)
    Temp14:float=field(init=False,default=None)
    @classmethod
    def from_data(cls,data):
        return cls(data)
        
    def __repr__(self):
        return f"{self.__class__.__name__}({', '.join([f.name+'='+str(getattr(self,f.name)) for f in fields(self) if not getattr(self,f.name) is None])})"
@dataclass
class HKVRelaisDataPacket(HKVDataPacket):
    Relais1:bool=field(init=False,default=None)
    Relais2:bool=field(init=False,default=None)
    Relais3:bool=field(init=False,default=None)
    Relais4:bool=field(init=False,default=None)
    Relais5:bool=field(init=False,default=None)
    Relais6:bool=field(init=False,default=None)
    @classmethod
    def from_data(cls,data):
        return cls(data)
      
    def __repr__(self):
        return f"{self.__class__.__name__}({', '.join([f.name+'='+str(getattr(self,f.name)) for f in fields(self) if not getattr(self,f.name) is None])})"
@dataclass
class HKVConnectionDataPacket(HKVDataPacket):
    ADDR0:int=field(init=False,default=None)
    STYPE0:int=field(init=False,default=None)
    ADDR1:int=field(init=False,default=None)
    STYPE1:int=field(init=False,default=None)
    ADDR2:int=field(init=False,default=None)
    STYPE2:int=field(init=False,default=None)
    ADDR3:int=field(init=False,default=None)
    STYPE3:int=field(init=False,default=None)
    ADDR4:int=field(init=False,default=None)
    STYPE4:int=field(init=False,default=None)
    ADDR5:int=field(init=False,default=None)
    STYPE5:int=field(init=False,default=None)
    ADDR6:int=field(init=False,default=None)
    STYPE6:int=field(init=False,default=None)
    ADDR7:int=field(init=False,default=None)
    STYPE7:int=field(init=False,default=None)
    ADDR8:int=field(init=False,default=None)
    STYPE8:int=field(init=False,default=None)
    ADDR9:int=field(init=False,default=None)
    STYPE9:int=field(init=False,default=None)
    @classmethod
    def from_data(cls,data):
        return cls(data)
        
    def __repr__(self):
        return f"{self.__class__.__name__}({', '.join([f.name+'='+str(getattr(self,f.name)) for f in fields(self) if not getattr(self,f.name) is None])})"

@dataclass
class HKVStatusDataPacket(HKVDataPacket):
    DISPLAY:str=field(init=False,default=None)
    USB:str=field(init=False,default=None)
    LORA:str=field(init=False,default=None)
    RS485:str=field(init=False,default=None)
    RELAIS:str=field(init=False,default=None)
    SENSOR:str=field(init=False,default=None)
    @classmethod
    def from_data(cls,data):
        return cls(data)
        
    def __repr__(self):
        return f"{self.__class__.__name__}({', '.join([f.name+'='+str(getattr(self,f.name)) for f in fields(self) if not getattr(self,f.name) is None])})"

if __name__=='__main__':
    import time
    
    print(HKVRelaisChannelPacket.from_doc('{"SRC":5955124,"DST":99,"TYPE":"R","RTYPE":"A","ID":"HKV-EG","CHAN":6,"VAL":1}'))
    
    # print(HKVPacket.from_doc('{"SRC":1,"DST":2,"TYPE":"D","DTYPE":"T","ID":"HKV-BASE","Temp0":20.0,"Temp1":20.1,"Temp2":20.2,"Temp11":20.11}'))
    # print(HKVPacket.from_doc('{"SRC":1,"DST":2,"TYPE":"D","DTYPE":"R","ID":"HKV-BASE","Relais1":1,"Relais2":0,"Relais3":1,"Relais4":0}'))
    # print(HKVPacket.from_doc('{"SRC":1,"DST":2,"TYPE":"L","LTYPE":"D","MSG":"Debug LOG Message."}'))
    # print(HKVPacket.from_doc('{"SRC":5955124,"DST":99,"TYPE":"D","DTYPE":"C","ID":"HKV-BASE","ADDR0":99,"STYPE0":1}'))
    # print(HKVTempDataPacket.mro())
    # for f in fields(HKVTempDataPacket):
    #     print(f"HKVTempDataPacket.{f.name}")
    # #time.sleep(2)
    # print(HKVTempDataPacket(dict(SRC=1, DST=2, TYPE='D', DTYPE='T', ID='HKV-BASE', Temp0=20.0, Temp1=20.1, Temp2=20.2, Temp3=None, Temp4=None, Temp5=None, Temp6=None, Temp7=None, Temp8=None, Temp9=None, Temp10=None, Temp11=20.11)))
    # print(HKVRelaisDataPacket(dict(SRC=1, DST=2, TYPE='D', DTYPE='R', ID='HKV-BASE', Relais1=1, Relais2=0, Relais3=1, Relais4=0, Relais5=None, Relais6=None)))
    # print(HKVLogPacket(dict(SRC=1, DST=2, TYPE='L', LTYPE='D', MSG='Debug LOG Message.')))
    # print(HKVStatusDataPacket(dict(SRC=1, DST=2, TYPE='D', DTYPE='S', ID='HKV-BASE', DISPLAY='OK', USB='OK', LORA='OK', RS485='OK', RELAIS='OK', SENSOR='OK')))
    # print(HKVStatusDataPacket({"SRC":5954092,"DST":99,"TYPE":"D","DTYPE":"S","ID":"HKV-BASE","DISPLAY":"Display Init .. DONE!","USB":"","LORA":"LoRa Init ..   DONE!","RS485":"RS485 Init ..  IGNORE!","RELAIS":"Relais Init .. DONE!","SENSOR":"Sensor Init .. DONE! -> 1"}))
    # print(HKVPacket.from_doc('{"SRC":5954092,"DST":99,"TYPE":"D","DTYPE":"S","ID":"HKV-BASE","DISPLAY":"Display Init .. DONE!","USB":"","LORA":"LoRa Init ..   DONE!","RS485":"RS485 Init ..  IGNORE!","RELAIS":"Relais Init .. DONE!","SENSOR":"Sensor Init .. DONE! -> 1"}'))
    
    
