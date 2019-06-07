import os
# only needed for getdict hack
import numpy as np
#TODO may wan to define an __all__ thanks to this? or refactor imports
from ctypes import *
from enum import Enum
from atexit import register
#onle needed for 
from collections.abc import Sequence

#TODO: DOCUMENTATION!!!

# load DLLs
# MightexDLL = CDLL('../mightex_lib/x64_lib/Mightex_LEDDriver_SDK.dll')
# change dir to where DLL is:
__x64_BASE_PATH = '../mightex_lib/x64_lib/'
__x86_BASE_PATH = '../mightex_lib/lib/'
__cdecl_dll = 'Mightex_LEDDriver_SDK.dll'
__stddel_dll = 'Mightex_LEDDriver_SDK_Stdcall.dll'

__ver_info = (0,1,0)
__version__ = '.'.join(map(str, __ver_info))

# util funcs
def invert_mapping(x):
    return {v: k for k, v in x.items()}

def get_dll(base_path, dll_type):
    cwd = os.getcwd()
    os.chdir(base_path)
    dll = cdll.LoadLibrary(dll_type)
    os.chdir(cwd)
    return dll

# Not used, maybe cut out?
# https://stackoverflow.com/a/51961249
def get_shape(lst, shape=()):
    """
    returns the shape of nested lists similarly to numpy's shape.

    :param lst: the nested list
    :param shape: the shape up to the current recursion depth
    :return: the shape including the current depth
            (finally this will be the full depth)
    """

    if not isinstance(lst, Sequence):
        # base case
        return shape

    # peek ahead and assure all lists in the next depth
    # have the same length
    if isinstance(lst[0], Sequence):
        l = len(lst[0])
        if not all(len(item) == l for item in lst):
            msg = 'not all lists have the same length'
            raise ValueError(msg)

    shape += (len(lst), )

    # recurse
    shape = get_shape(lst[0], shape)

    return shape

# HACK: remove this and replace with instance method to convert to dict
# https://stackoverflow.com/a/3789491
def getdict(struct):
    result = {}
    for field, _ in struct._fields_:
         value = getattr(struct, field)
         # if the type is not a primitive and it evaluates to False ...
         if (type(value) not in [int, float, bool]) and not bool(value):
             # it's a null pointer
             value = None
         elif hasattr(value, "_length_") and hasattr(value, "_type_"):
             # Probably an array
             # value = list(value)
             value = np.ctypeslib.as_array(value).tolist()
         elif hasattr(value, "_fields_"):
             # Probably another struct
             value = getdict(value)
         result[field] = value
    return result


_MightexDLL = get_dll(__x64_BASE_PATH,__cdecl_dll)
# constants for the module itself
SERIAL_NUMBER_SIZE=16
_ENCODING = 'ascii'

# vars used internally
# flag for initialization
_initialized = False

# will have format (idx:int):(serial_num:str)
__controller_map = {}


#defines 
MAX_PROFILE_ITEM = 128

class MightexChannelMode(Enum):
    DISABLE_MODE=0
    NORMAL_MODE=1
    STROBE_MODE=2
    TRIGGER_MODE=3

class MightexModuleType(Enum):
    MODULE_AA=0
    MODULE_AV=1
    MODULE_SA=2
    MODULE_SV=3
    MODULE_MA=4
    MODULE_CA=5
    MODULE_HA=6
    MODULE_HV=7
    MODULE_FA=8
    MODULE_FV=9
    MODULE_XA=10
    MODULE_XV=11
    MODULE_QA=12

# structs
class TLedChannelData(Structure):
    _pack_ = 1
    _fields_ = [
        ('Normal_CurrentMax',c_int),
        ('Normal_CurrentSet',c_int),
        ('Strobe_CurrentMax',c_int),
        ('Strobe_RepeatCnt',c_int),
        ('Strobe_Profile',(c_int*MAX_PROFILE_ITEM)*2),
        ('Trigger_CurrentMax',c_int),
        ('Trigger_Polarity',c_int),
        ('Trigger_Profile',(c_int*MAX_PROFILE_ITEM)*2)
        ]

    # these don't change so doesnt matter typing keys out instead of pulling
    _int_keys = {
        'Normal_CurrentMax', 'Normal_CurrentSet',
        'Strobe_CurrentMax', 'Strobe_CurrentMax', 'Strobe_RepeatCnt',
        'Trigger_CurrentMax', 'Trigger_Polarity'
    }
    
    _arr_keys = {
        'Strobe_Profile','Trigger_Profile'
    }
    
    # _keys = {param[0] for param in _fields_}
    _keys = _int_keys|_arr_keys

    #TODO: handle strobe and trigger profile size limits
    #TODO: type checking, all vals are ints
    #TODO: lookinto accpeting a sequence of 2 element sequences and transposing it
    @classmethod
    def from_mapping(cls, mapping):
        """
        converts a dict to the struct

        checks to ensure values fit in the struct

        important note: assumes profiles are a sqeuene of of 2 sequences corresponsing to a_n values and b_n values
        eg: [(a_1,a_2,...,a_n),(b_1,b_2,...,b_n)]
        """
        # ensure all keys in mapping are acceptable:
        assert all([(k in cls._keys) for k in mapping.keys() ])
        # ensure type checking
        assert all([isinstance(v,int) for v in [v for k,v in mapping.items() if (k in cls._int_keys)]])
        assert all([isinstance(m, Sequence) for m in [v for k,v in mapping.items() if (k in cls._arr_keys)]])
        
        # not implemented
        # determine if need to transpose the profile arrays
        # shape = get_shape()


        # transpose and chop after MAX_PROFILE_LEN
        for k,v in mapping.items():
            if (k in cls._arr_keys):
                # mapping[k] = ((c_int*MAX_PROFILE_ITEM)*2)(*list(zip(*v))[:MAX_PROFILE_ITEM-1])
                mapping[k] = ((c_int*MAX_PROFILE_ITEM)*2)(*tuple([tuple(e[:MAX_PROFILE_ITEM]) for e in v]))

        return cls(**mapping)
    

    def __str__(self):
        return "{}: {{{}}}".format(self.__class__.__name__,
                                ", ".join(["{}: {}".format(field[0],
                                                            getattr(self,
                                                                    field[0]))
                                            for field in self._fields_]))

# print(TLedChannelData._keys)

# TODO: MAYBE annotate the functions? 
# declare prototypes
# int MTUSB_LEDDriverInitDevices( void );
# int MTUSB_LEDDriverOpenDevice( int DeviceIndex );
# int MTUSB_LEDDriverCloseDevice( int DevHandle );
# int MTUSB_LEDDriverSerialNumber( int DevHandle, char *SerNumber, int Size );
# int MTUSB_LEDDriverDeviceChannels( int DevHandle );
# int MTUSB_LEDDriverDeviceModuleType( int DevHandle);
# int MTUSB_LEDDriverSetMode( int DevHandle, int Channel, int Mode );
# int MTUSB_LEDDriverSetNormalPara( int DevHandle, int Channel, TLedChannelData *LedChannelDataPtr );
# int MTUSB_LEDDriverSetNormalCurrent( int DevHandle, int Channel, int Current );
# int MTUSB_LEDDriverSetStrobePara( int DevHandle, int Channel, TLedChannelData *LedChannelDataPtr );
# int MTUSB_LEDDriverSetTriggerPara( int DevHandle, int Channel, TLedChannelData *LedChannelDataPtr );
# int MTUSB_LEDDriverResetDevice( int DevHandle );
# int MTUSB_LEDDriverStorePara( int DevHandle );
# int MTUSB_LEDDriverRestoreDefault( int DevHandle );
# int MTUSB_LEDDriverGetLoadVoltage( int DevHandle, int Channel );
# int MTUSB_LEDDriverGetCurrentPara( int DevHandle, int Channel,TLedChannelData *LedChannelDataPtr,int *Mode );
# int MTUSB_LEDDriverSendCommand( int DevHandle, char *CommandString );

# TODO: look into handling return codes from the functions for confirming or alerting success/failure for api call
# TODO: convert mostly to properties for things liek channel info for better usage 
class LEDController:
    def __init__(self, index:int, serial_num=None):
        self._handle = _MightexDLL.MTUSB_LEDDriverOpenDevice(index)
        register(self.close)
        # force into PC mode
        self.send_cmd('ECHOOFF')
        self._ch = _MightexDLL.MTUSB_LEDDriverDeviceChannels(self._handle)
        self._device_module_type = _MightexDLL.MTUSB_LEDDriverDeviceModuleType(self._handle)
        self._ch_info = [[TLedChannelData(),MightexChannelMode.DISABLE_MODE] for i in range(0,self._ch)]
        # required to enable PC mode on the device, only needs a single call but why not get all at this point
        for i in range(1,self._ch+1):
            self.get_ch_param(i)
        if serial_num is None: 
            buf = create_string_buffer(SERIAL_NUMBER_SIZE)
            _MightexDLL.MTUSB_LEDDriverSerialNumber(self._handle, buf, SERIAL_NUMBER_SIZE)
            self._serial_num = buf.value.decode(_ENCODING)
        else:
            self._serial_num = serial_num

    @property
    def serial_num(self):
        return self._serial_num

    @property
    def num_channels(self):
        return self._ch

    @property
    def module_type(self):
        return MightexModuleType(self._device_module_type)

    #TODO: convert to property?
    def get_ch_param(self, channel):
        mode = c_int() 
        _MightexDLL.MTUSB_LEDDriverGetCurrentPara(self._handle, channel, self._ch_info[channel-1][0], byref(mode))
        self._ch_info[channel-1][1] = MightexChannelMode(mode.value) 

    def reset_device(self):
        _MightexDLL.MTUSB_LEDDriverResetDevice(self._handle)

    def set_mode(self, channel:int, mode:MightexChannelMode):
        _MightexDLL.MTUSB_LEDDriverSetMode(self._handle, channel, mode.value)

    def set_current(self, channel:int, current:int):
        _MightexDLL.MTUSB_LEDDriverSetNormalCurrent(self._handle, channel, current)

    def close(self):
        # print('cleaup')
        _MightexDLL.MTUSB_LEDDriverCloseDevice(self._handle)
    
    # note: trigger doesnt exist for some units
    # note: settingsparameters will change struct, and screen but normal set current will not update 
    def set_parameters(self, channel:int, parameters:dict):
        cfg = getdict(self._ch_info[channel-1][0])
        cfg.update(parameters)
        params = TLedChannelData.from_mapping(cfg)
        _MightexDLL.MTUSB_LEDDriverSetNormalPara(self._handle,channel,params)
        _MightexDLL.MTUSB_LEDDriverSetStrobePara(self._handle,channel,params)
        _MightexDLL.MTUSB_LEDDriverSetTriggerPara(self._handle,channel,params)

    def restore_default(self):
        _MightexDLL.MTUSB_LEDDriverRestoreDefault(self._handle)

    def store_parameters(self):
        _MightexDLL.MTUSB_LEDDriverStorePara(self._handle)

    # note doesnt work for SLC_MAxx-xx models
    def get_load_voltage(self, channel:int):
        return _MightexDLL.MTUSB_LEDDriverGetLoadVoltage(self._handle,channel)

    def send_cmd(self, command_str):
        cmd = f'{command_str}\n\r'.encode(_ENCODING)
        return _MightexDLL.MTUSB_LEDDriverSendCommand(self._handle, c_char_p(cmd))

# factory function to create a LED controller object
def get_led_controller(ctrlr_idx=None,serial_num=None): 
    # init api
    if not _initialized:
        num_devices = _MightexDLL.MTUSB_LEDDriverInitDevices()
        # build controller map
        for i in range(0,num_devices):
            handle = _MightexDLL.MTUSB_LEDDriverOpenDevice(i)
            # send command if needed:
            # _MightexDLL.MTUSB_LEDDriverSendCommand(handle, c_char_p('ECHOOFF\n\r'.encode(_ENCODING)))
            buf = create_string_buffer(SERIAL_NUMBER_SIZE)
            _MightexDLL.MTUSB_LEDDriverSerialNumber(handle, buf,SERIAL_NUMBER_SIZE)
            __controller_map[i] = buf.value.decode(_ENCODING)
            _MightexDLL.MTUSB_LEDDriverCloseDevice(handle)
    # match serial num
    if ctrlr_idx is None and serial_num is not None:
        idx = invert_mapping(__controller_map)[serial_num]
        return LEDController(index=idx, serial_num=serial_num)
    elif (ctrlr_idx is not None) and (serial_num is None):
        return LEDController(index=ctrlr_idx,serial_num=__controller_map[ctrlr_idx])
    # both are None 
    else:
        raise ValueError('Must specify either controller index or serial number')

if __name__ == "__main__":
    pass