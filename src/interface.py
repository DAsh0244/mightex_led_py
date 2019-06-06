import os
from ctypes import *
from enum import Enum
from atexit import register
# load DLLs
# MightexDLL = CDLL('../mightex_lib/x64_lib/Mightex_LEDDriver_SDK.dll')
# change dir to where DLL is:
__x64_BASE_PATH = '../mightex_lib/x64_lib/'
__x86_BASE_PATH = '../mightex_lib/lib/'
__cdecl_dll = 'Mightex_LEDDriver_SDK.dll'
__stddel_dll = 'Mightex_LEDDriver_SDK_Stdcall.dll'


cwd = os.getcwd()
os.chdir(__x64_BASE_PATH)
MightexDLL = cdll.LoadLibrary('Mightex_LEDDriver_SDK.dll')
os.chdir(cwd)
del cwd

# constants for the module itself
SERIAL_NUMBER_SIZE=16
_ENCODING = 'utf-8'

# vars used internally
# flag for initialization
_initialized = False

# will have format (idx:int):(serial_num:str)
__controller_map = {}
def invert_mapping(x):
    return {v: k for k, v in x.items()}

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

class LEDController:
    def __init__(self, index:int, serial_num=None):
        self._handle = MightexDLL.MTUSB_LEDDriverOpenDevice(index)
        self._ch = MightexDLL.MTUSB_LEDDriverDeviceChannels(self._handle)
        self._device_module_type = MightexDLL.MTUSB_LEDDriverDeviceModuleType(self._handle)
        self._ch_info = [[TLedChannelData(),MightexChannelMode.DISABLE_MODE] for i in range(0,self._ch)]
        if serial_num is None: 
            buf = create_string_buffer(SERIAL_NUMBER_SIZE)
            MightexDLL.MTUSB_LEDDriverSerialNumber(self._handle, buf, SERIAL_NUMBER_SIZE)
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

    def get_ch_param(self, channel):
        mode = c_int() 
        MightexDLL.MTUSB_LEDDriverGetCurrentPara(self._handle, channel, self._ch_info[channel-1][0], byref(mode))
        self._ch_info[channel-1][1] = MightexChannelMode(mode.value) 

    def reset_device(self):
        MightexDLL.MTUSB_LEDDriverResetDevice(self._handle)

    def set_mode(self,channel:int, mode:MightexChannelMode):
        MightexDLL.MTUSB_LEDDriverSetMode(self._handle, channel, mode.value)

    def set_current(self,channel:int, current:int):
        MightexDLL.MTUSB_LEDDriverSetNormalCurrent(self._handle, channel, current)

    def close(self):
        MightexDLL.MTUSB_LEDDriverCloseDevice(self._handle)

    def send_cmd(self, command_str):
        # allocate enough space for string
        cmd = f'{command_str}\r\n'.encode(_ENCODING)
        MightexDLL.MTUSB_LEDDriverSendCommand()

# factory function to create a LED controller object
def get_led_controller(ctrlr_idx=None,serial_num=None): 
    # init api
    if not _initialized:
        num_devices = MightexDLL.MTUSB_LEDDriverInitDevices()
        # build controller map
        for i in range(0,num_devices):
            handle = MightexDLL.MTUSB_LEDDriverOpenDevice(i)
            buf = create_string_buffer(SERIAL_NUMBER_SIZE)
            MightexDLL.MTUSB_LEDDriverSerialNumber(handle, buf,SERIAL_NUMBER_SIZE)
            __controller_map[i] = buf.value.decode(_ENCODING)
            MightexDLL.MTUSB_LEDDriverCloseDevice(handle)
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