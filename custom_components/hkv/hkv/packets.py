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
        try:
            if data['TYPE']=='L':
                return HKVLogPacket.from_data(data)
            elif data['TYPE']=='A':
                return HKVAckPacket.from_data(data)
            elif data['TYPE']=='N':
                return HKVNAckPacket.from_data(data)
            elif data['TYPE']=='H':
                return HKVHelloPacket.from_data(data)
            elif data['TYPE']=='D' and data['DTYPE'] in ['T','R','S','C']:
                return HKVDataPacket.from_data(data)
            elif data['TYPE']=='R' and data['RTYPE']=='A':
                return HKVRelaisChannelPacket.from_data(data)
            elif data['TYPE']=='T' and data['TTYPE']=='A':
                return HKVTempChannelPacket.from_data(data)
            else:
                return cls(data)
        except:
                return cls(data)
            
        
    def __repr__(self):
        return f"{self.__class__.__name__}({', '.join([f.name+'='+str(getattr(self,f.name)) for f in fields(self) if not getattr(self,f.name) is None])})"
    
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
    # ID:str=field(init=False)
    CHAN:int=field(init=False)
    VAL:float=field(init=False)
    @classmethod
    def from_data(cls,data):
        return cls(data)
    
@dataclass
class HKVTempChannelPacket(HKVChannelPacket):
    TTYPE:str=field(init=False)
    MCNT:int=field(init=False)
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
    # ID:str=field(init=False)
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
    MCNT:int=field(init=False,default=0)
    SNUM:int=field(init=False,default=0)
    TDATA:list[float]=field(init=False,default_factory=list)
    @classmethod
    def from_data(cls,data):
        return cls(data)
        
    def __repr__(self):
        return f"{self.__class__.__name__}({', '.join([f.name+'='+str(getattr(self,f.name)) for f in fields(self) if not getattr(self,f.name) is None])})"
@dataclass
class HKVRelaisDataPacket(HKVDataPacket):
    RNUM:int=field(init=False,default=0)
    RDATA:list[bool]=field(init=False,default_factory=list)
    @classmethod
    def from_data(cls,data):
        return cls(data)
      
    def __repr__(self):
        return f"{self.__class__.__name__}({', '.join([f.name+'='+str(getattr(self,f.name)) for f in fields(self) if not getattr(self,f.name) is None])})"
@dataclass
class HKVConnectionDataPacket(HKVDataPacket):
    CCNT:int=field(init=False,default=0)
    CDATA:list[dict]=field(init=False,default_factory=list)
    @classmethod
    def from_data(cls,data):
        return cls(data)
        
    def __repr__(self):
        return f"{self.__class__.__name__}({', '.join([f.name+'='+str(getattr(self,f.name)) for f in fields(self) if not getattr(self,f.name) is None])})"

@dataclass
class HKVStatusDataPacket(HKVDataPacket):
    ID:str=field(init=False,default=None)
    MSEC:int=field(init=False,default=None)
    SNUM:int=field(init=False,default=None)
    MCNT:int=field(init=False,default=None)
    RNUM:int=field(init=False,default=None)
    CCNT:int=field(init=False,default=None)
    # DISPLAY:str=field(init=False,default=None)
    # USB:str=field(init=False,default=None)
    # LORA:str=field(init=False,default=None)
    # RS485:str=field(init=False,default=None)
    # RELAIS:str=field(init=False,default=None)
    # SENSOR:str=field(init=False,default=None)
    @classmethod
    def from_data(cls,data):
        return cls(data)
        
    def __repr__(self):
        return f"{self.__class__.__name__}({', '.join([f.name+'='+str(getattr(self,f.name)) for f in fields(self) if not getattr(self,f.name) is None])})"

if __name__=='__main__':
    import time
    
    print(HKVRelaisChannelPacket.from_doc('{"SRC":5955124,"DST":99,"TYPE":"R","RTYPE":"A","ID":"HKV-EG","CHAN":6,"VAL":1}'))
    print(HKVRelaisChannelPacket.from_doc('{"SRC":5955124,"DST":99,"TYPE":"D","DTYPE":"T","DATA":[1,2,3,4]}'))
    
    # print(HKVPacket.from_doc('{"SRC":1,"DST":2,"TYPE":"D","DTYPE":"T","ID":"HKV-BASE","Temp0":20.0,"Temp1":20.1,"Temp2":20.2,"Temp11":20.11}'))
    # print(HKVPacket.from_doc('{"SRC":1,"DST":2,"TYPE":"D","DTYPE":"R","ID":"HKV-BASE","Relais1":1,"Relais2":0,"Relais3":1,"Relais4":0}'))
    # print(HKVPacket.from_doc('{"SRC":1,"DST":2,"TYPE":"L","LTYPE":"D","MSG":"Debug LOG Message."}'))
    # print(HKVPacket.from_doc('{"SRC":5955124,"DST":99,"TYPE":"D","DTYPE":"C","ID":"HKV-BASE","ADDR0":99,"STYPE0":1}'))
    # print(HKVTempDataPacket.mro())
    # for f in fields(HKVTempDataPacket):
    #     print(f"HKVTempDataPacket.{f.name}")
    # #time.sleep(2)
    # print(HKVTempDataPacket(dict(SRC=1, DST=2, TYPE='D', DTYPE='T', ID='HKV-BASE', Temp0=20.0, Temp1=20.1, Temp2=20.2, Temp3=None, Temp4=None, Temp5=None, Temp6=None, Temp7=None, Temp8=None, Temp9=None, Temp10=None, Temp11=20.11)))
    print(HKVRelaisDataPacket(dict(SRC=1, DST=2, TYPE='D', DTYPE='R', ID='HKV-BASE', RNUM=2, RDATA=[1,1])))
    # print(HKVLogPacket(dict(SRC=1, DST=2, TYPE='L', LTYPE='D', MSG='Debug LOG Message.')))
    # print(HKVStatusDataPacket(dict(SRC=1, DST=2, TYPE='D', DTYPE='S', ID='HKV-BASE', DISPLAY='OK', USB='OK', LORA='OK', RS485='OK', RELAIS='OK', SENSOR='OK')))
    # print(HKVStatusDataPacket({"SRC":5954092,"DST":99,"TYPE":"D","DTYPE":"S","ID":"HKV-BASE","DISPLAY":"Display Init .. DONE!","USB":"","LORA":"LoRa Init ..   DONE!","RS485":"RS485 Init ..  IGNORE!","RELAIS":"Relais Init .. DONE!","SENSOR":"Sensor Init .. DONE! -> 1"}))
    # print(HKVPacket.from_doc('{"SRC":5954092,"DST":99,"TYPE":"D","DTYPE":"S","ID":"HKV-BASE","DISPLAY":"Display Init .. DONE!","USB":"","LORA":"LoRa Init ..   DONE!","RS485":"RS485 Init ..  IGNORE!","RELAIS":"Relais Init .. DONE!","SENSOR":"Sensor Init .. DONE! -> 1"}'))
    
    
