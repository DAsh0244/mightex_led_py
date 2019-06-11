 # -*- coding: utf-8 -*-
"""
wraps calling the Mightex LED driver api dlls into a set of object oriented interfaces.

author: Danyal Ahsanullah
"""
# __author__ = 'Danyal Ahsanullah'
__ver_info = (0,2,1)
__version__ = '.'.join(map(str, __ver_info))


import typing as _typ
import ctypes as _ctypes
from enum import Enum as _Enum
from os import ( getcwd as _getcwd, chdir as _chdir )
from atexit import ( register as _register, unregister as _unregister )

# typing definitions
T = _typ.TypeVar('T')
LC = _typ.TypeVar('LC', bound='LEDController')
TL = _typ.TypeVar('TL', bound='TLedChannelData')
TLED_MAPPING = _typ.Dict[str,_typ.Union[int,_typ.Tuple[_typ.Sequence[int],_typ.Sequence[int]]]]

# DLL info
# CONSIDER: making this an env var?
__x64_BASE_PATH = '../mightex_lib/x64_lib/'
__x86_BASE_PATH = '../mightex_lib/lib/'
__cdecl_dll = 'Mightex_LEDDriver_SDK.dll'
__stddel_dll = 'Mightex_LEDDriver_SDK_Stdcall.dll'
# MightexDLL = CDLL('../mightex_lib/x64_lib/Mightex_LEDDriver_SDK.dll')

# util funcs
def _get_dll(base_path:str, dll_type:str) -> _typ.Union[_ctypes.CDLL,_ctypes.WinDLL]:
    """
    Loads the desired dll and returns the loaded DLL object.
    
    Arguments:
        base_path {str} -- Path to the directory that contains the DLL
        dll_type {str} -- DLL filename
    
    Returns:
        CDLL or WinDLL -- Loaded Mightex CDLL object
    """
    cwd = _getcwd()
    _chdir(base_path)
    if 'stdcall' in dll_type.lower():
        dll_class = _ctypes.windll
    else:
        dll_class = _ctypes.cdll
    dll = dll_class.LoadLibrary(dll_type)
    _chdir(cwd)
    return dll


def _invert_mapping(x):
    return {v: k for k, v in x.items()}

#defines 
MAX_PROFILE_ITEM = 128

# constants for the module itself
SERIAL_NUMBER_SIZE=16
_ENCODING = 'ascii'
_PROFILE_DIM = ((_ctypes.c_int*MAX_PROFILE_ITEM)*2)
_MightexDLL = _get_dll(__x64_BASE_PATH,__cdecl_dll)
# CONSIDER: MAYBE annotate the functions? 
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

# vars used internally
# flag for initialization
_initialized = False
# will have format (idx:int):(serial_num:str)
_controller_map = {}

class MightexChannelMode(_Enum):
    DISABLE_MODE=0
    NORMAL_MODE=1
    STROBE_MODE=2
    TRIGGER_MODE=3

class MightexModuleType(_Enum):
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
class TLedChannelData(_ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ('Normal_CurrentMax', _ctypes.c_int),
        ('Normal_CurrentSet', _ctypes.c_int),
        ('Strobe_CurrentMax', _ctypes.c_int),
        ('Strobe_RepeatCnt', _ctypes.c_int),
        ('Strobe_Profile', _PROFILE_DIM),
        ('Trigger_CurrentMax', _ctypes.c_int),
        ('Trigger_Polarity', _ctypes.c_int),
        ('Trigger_Profile', _PROFILE_DIM)
        ]

    # All key names that are 
    _int_keys = {
        'Normal_CurrentMax', 'Normal_CurrentSet',
        'Strobe_CurrentMax', 'Strobe_CurrentMax', 'Strobe_RepeatCnt',
        'Trigger_CurrentMax', 'Trigger_Polarity'
    }
    
    _arr_keys = {
        'Strobe_Profile','Trigger_Profile'
    }
    
    _keys = _int_keys|_arr_keys
    # this is bad as it doesnt keep order so members are shuffled about and not right
    # _fields_ = [(key,c_int) for key in _int_keys] + [(key, (c_int*MAX_PROFILE_ITEM)*2) for key in _arr_keys]

    #TODO: lookinto accpeting a sequence of 2 element sequences and transposing it
    @classmethod
    def from_mapping(cls:_typ.Type[TL], mapping:_typ.Mapping)->TL:
        """
        converts a dict to the struct.
        checks to ensure values fit in the struct.
        important note: assumes profiles are a sqeuene of of 2 sequences corresponsing to a_n values and b_n values
        eg: [(a_1,a_2,...,a_n),(b_1,b_2,...,b_n)]
        
        Arguments:
            cls {Type[TL]} -- class instance. Passed implicitly in most cases
            mapping {Mapping} -- mappign object that describes the structure
        
        Returns:
            TLedChannelData -- [description]
        """
        
        # ensure all keys in mapping are acceptable:
        assert all([(k in cls._keys) for k in mapping.keys() ])
        # ensure type checking
        assert all([isinstance(v,int) for v in [v for k,v in mapping.items() if (k in cls._int_keys)]])
        assert all([isinstance(m, _typ.Sequence) for m in [v for k,v in mapping.items() if (k in cls._arr_keys)]])
        
        # not implemented
        # determine if need to transpose the profile arrays
        # shape = get_shape()
        # transpose to a sqeuene of of 2 sequences corresponsing to a_n values and b_n values


        # chop after MAX_PROFILE_LEN
        for k,v in mapping.items():
            if (k in cls._arr_keys):
                # mapping[k] = (_PROFILE_DIM)(*list(zip(*v))[:MAX_PROFILE_ITEM-1])
                mapping[k] = (_PROFILE_DIM)(*tuple([tuple(e[:MAX_PROFILE_ITEM]) for e in v]))

        return cls(**mapping)
    
    def to_mapping(self)->TLED_MAPPING:
        """converts from structure to dict"""
        res:TLED_MAPPING = {}
        for field in self._int_keys:
            res[field] = getattr(self, field)
        for field in self._arr_keys:
            # convert arr to list
            profile = [None,None]
            for i,entry in enumerate(getattr(self,field)):
                profile[i] = entry[:]
            res[field] = tuple(profile)
        return res

    def __repr__(self)->str:
        """Return test represenation of instance"""
        res = []
        for field in self._int_keys:
            res.append('%s=%s' % (field, repr(getattr(self, field))))
        for field in self._arr_keys:
            # convert arr to list
            profile = [None,None]
            for i,entry in enumerate(getattr(self,field)):
                profile[i] = entry[:]
            res.append('%s=%s' % (field, tuple(profile)))
        return self.__class__.__name__ + '(' + ','.join(res) + ')'

# TODO: Implement debug... make debug a logging.level type var?
class LEDController:
    """
    Class representing the Mightex SLC-MAxx-Mx series LED controllers
    Reccomended method of getting an instance of this is through the 
    `LEDController.get_controller` factory method. 
    
    This class will automatically cleanup its HID control connection 
    upon termination of the program. To cleanup before then manually call the 
    `close` method.After calling this method, the object should not be used again.
    If it is needed to reaccess the LED Controller, instantiate a new instance of LEDController. 

    Attributes:
        Standard: 
            debug:bool - flag set for enabling debug mode
            

        Read only:
            closed:bool - flag for indicating if device has been closed
            serial_num:str - serial number of the device
            num_channels:int - number of channels of the device
            module_type:MightexModuleType - enum of the module type
            channel_status:dict - dictionary holding channel info for each channel

    Methods:
        see method docstrings
    """
    
    @staticmethod
    def _check_return_code(result:T, ret_map:_typ.Mapping[T,_typ.Type[Exception]]):
        """
        checks result againgst a provided mapping of return codes and associated errors to raise.
        
        Arguments:
            result {T} -- return code
            ret_map {Mapping[T,Type[Exception]]} -- map of return codes : exceptions to raise
        
        Raises:
            err: exception specified by return code if triggered, else None
        """
        for key,err in ret_map.items():
            if result == key:
                raise err
        
    def __init__(self, index:int, serial_num=None, debug=False):
        """
        Instantiantie the object. 
        This method: 
            1. Opens the device
            2. puts it into PC control mode
            3. Queries the device's information
            4. Queries each of the device's channel's configurations
        
        Arguments:
            index {int} -- index of the LEDController to open. 
            This number should be in the range [0, `MTUSB_LEDDriverInitDevices()`) 
        
        Keyword Arguments:
            serial_num {[type]} -- optional arguement for passing the serial number
             of the device if it was selected by serial number (default: {None})
            debug {bool} -- whether or not to enable debug mode (default: {False})
        """
        self.debug = debug
        self._handle = _MightexDLL.MTUSB_LEDDriverOpenDevice(index)
        _register(self._close)
        self._closed = False
        # force into PC mode
        self.send_cmd('ECHOOFF')
        self._ch = _MightexDLL.MTUSB_LEDDriverDeviceChannels(self._handle)
        self._device_module_type = _MightexDLL.MTUSB_LEDDriverDeviceModuleType(self._handle)
        self._ch_info = [[TLedChannelData(),MightexChannelMode.DISABLE_MODE] for i in range(0,self._ch)]
        self.update_channel_info()
        if serial_num is None: 
            buf = _ctypes.create_string_buffer(SERIAL_NUMBER_SIZE)
            _MightexDLL.MTUSB_LEDDriverSerialNumber(self._handle, buf, SERIAL_NUMBER_SIZE)
            self._serial_num = buf.value.decode(_ENCODING)
        else:
            self._serial_num = serial_num

    @property
    def closed(self):
        return self._closed

    @property
    def serial_num(self)->str:
        return self._serial_num

    @property
    def num_channels(self)->int:
        return self._ch

    @property
    def module_type(self)->MightexModuleType:
        return MightexModuleType(self._device_module_type)

    @property
    def channel_info(self)->_typ.Dict[int,TLED_MAPPING]:
        info = {}
        for idx,ch in enumerate(self._ch_info):
            info[idx] = ch[0].to_mapping()
            info[idx].update({'status':ch[1]})
        return info

    def update_channel_info(self):
        """
        convience function that updates all channel information
        """
        for i in range(1,self._ch+1):
            self.get_ch_param(i)

    #CONSIDER: making more private?
    def get_ch_param(self, channel):
        """
        Queries and gets channel information for the specified channel.
        This information is then accessable through the `channel_info` property.
        
        Arguments:
            channel {[type]} -- 1 indexed channel number to query the confgiured parameters for. 
        """
        mode = _ctypes.c_int() # dummy var needed for dll call
        _MightexDLL.MTUSB_LEDDriverGetCurrentPara(self._handle, channel, self._ch_info[channel-1][0], _ctypes.byref(mode))
        self._ch_info[channel-1][1] = MightexChannelMode(mode.value) 

    def reset_device(self):
        """
        Commands the device to reset itself
        After this command it is necessary to re-enable PC control mode
        """
        _MightexDLL.MTUSB_LEDDriverResetDevice(self._handle)

    def set_ch_mode(self, channel:int, mode:_typ.Union[MightexChannelMode,int,str]):
        """
        Sets the desired channel mode
        
        Arguments:
            channel {int} -- channel to set mode of.
            mode {MightexChannelMode|int|str} -- Mode enumeration object or value/name of enumeration
        
        Raises:
            ValueError if an invalid enum designation is not provided
        """
        # asssume enum type
        mode_val = mode.value
        if isinstance(mode,str):
            try: 
                mode_val = MightexChannelMode[mode]
            except IndexError:
                raise ValueError('invalid Enumeration name provided {}'.format(mode))
        elif isinstance(mode,int):
            # this raises proper exception already
            mode_val = MightexChannelMode(mode).value
        else:
            if not isinstance(mode, MightexChannelMode):
                raise ValueError('Invalid object passed {!r}'.format(mode))
        _MightexDLL.MTUSB_LEDDriverSetMode(self._handle, channel, mode_val)

    def set_current(self, channel:int, current:int):
        """
        Sets normal mode current of channel. 
        Note this does not set the current parameter of the device. Instead use set parameters. 
        
        Arguments:
            channel {int} -- 1 indexed channel number
            current {int} -- set current in mA
        """
        _MightexDLL.MTUSB_LEDDriverSetNormalCurrent(self._handle, channel, current)

    def close(self):
        """
        Manual method to close the LEDController properly

        After calling this method, the object should not be used again.
        If it is needed to reaccess the LED Controller, 
        Instantiate a new instance of LEDController. 
        """
        # print('cleaup')
        _unregister(self._close)
        self._closed = True
        self._close()

    def _close(self):
        """
        Calls the close api call.
        This method should never be called directly, 
        and instead should be let to run automatically at program termination
        OR through the instance's `close` method. 
        """
        res = _MightexDLL.MTUSB_LEDDriverCloseDevice(self._handle)
        self._check_return_code(res,{-1:RuntimeError('Error in calling API')})
    
    # note: trigger doesnt exist for some units
    # note: settingsparameters will change struct, and screen but normal set current will not update 
    def set_parameters(self, channel:int, parameters:dict):
        """
        Set parameters from parameter dict for specified channel
        
        Arguments:
            channel {int} -- [description]
            parameters {dict} -- [description]

        Raises:
            ValueError: Upon being called with invalid Handle
            RuntimeError: Upon API error occuring
        """
        ret_map = {-1:ValueError('Invalid Handle provided'), 1:RuntimeError('Error in calling API')}
        cfg = self._ch_info[channel-1][0].to_mapping()
        cfg.update(parameters)
        params = TLedChannelData.from_mapping(cfg)
        res = _MightexDLL.MTUSB_LEDDriverSetNormalPara(self._handle,channel,params)
        self._check_return_code(res,ret_map)
        res = _MightexDLL.MTUSB_LEDDriverSetStrobePara(self._handle,channel,params)
        self._check_return_code(res,ret_map)
        res = _MightexDLL.MTUSB_LEDDriverSetTriggerPara(self._handle,channel,params)
        self._check_return_code(res,ret_map)

    def restore_default(self):
        """
        Restore factory defaults to the given device.
                
        Raises:
            ValueError: Upon being called with invalid Handle
            RuntimeError: Upon API error occuring
        """
        res = _MightexDLL.MTUSB_LEDDriverRestoreDefault(self._handle)
        self._check_return_code(res,{-1:ValueError('Invalid Handle provided'), 1:RuntimeError('Error in calling API')})

    def store_parameters(self):
        """
        Stores current parameters into Controller's non-volatile memory

        Raises:
            ValueError: Upon being called with invalid Handle
            RuntimeError: Upon API error occuring
        """
        res = _MightexDLL.MTUSB_LEDDriverStorePara(self._handle)
        self._check_return_code(res,{-1:ValueError('Invalid Handle provided'), 1:RuntimeError('Error in calling API')})

    # note doesnt work for SLC_MAxx-xx models
    def get_load_voltage(self, channel:int)-> int:
        """
        Returns load voltage of the channel
        note doesnt work for SLC_MAxx-xx models
        
        Arguments:
            channel {int} -- 1 indexed channel number to query load voltage.
        
        Returns:
            int -- Load voltage in mV, -1 on failure
        """
        return _MightexDLL.MTUSB_LEDDriverGetLoadVoltage(self._handle,channel)

    def send_cmd(self, command_str):
        cmd = f'{command_str}\n\r'.encode(_ENCODING)
        res = _MightexDLL.MTUSB_LEDDriverSendCommand(self._handle, _ctypes.c_char_p(cmd))
        self._check_return_code(res,{-1:ValueError('Invalid Handle provided')})

    # factory function to create a LED controller object
    @classmethod
    def get_controller(cls:_typ.Type[LC], ctrlr_idx:_typ.Optional[int]=None,serial_num:_typ.Optional[str]=None)->LC:
        """
        Factory function to create a LED controller object.
        Either ctrlr_idx or serial_num must not be None, else a ValueError is raised.

        Keyword Arguments:
            ctrlr_idx {Optional[int]} -- index of the LEDController to open. 
            This number should be in the range [0, `MTUSB_LEDDriverInitDevices()`)
            (default: {None})
            serial_num {Optional[str]} -- serial number of the device (default: {None})
        
        Raises:
            ValueError: If ctrlr_idx and serial_num are both None.
        
        Returns:
            LEDController -- LEDCotntroller instance
        """
        # init api
        if not _initialized:
            num_devices = _MightexDLL.MTUSB_LEDDriverInitDevices()
            # build controller map
            for i in range(0,num_devices):
                handle = _MightexDLL.MTUSB_LEDDriverOpenDevice(i)
                # send command if needed:
                # _MightexDLL.MTUSB_LEDDriverSendCommand(handle, c_char_p('ECHOOFF\n\r'.encode(_ENCODING)))
                buf = _ctypes.create_string_buffer(SERIAL_NUMBER_SIZE)
                _MightexDLL.MTUSB_LEDDriverSerialNumber(handle, buf,SERIAL_NUMBER_SIZE)
                _controller_map[i] = buf.value.decode(_ENCODING)
                _MightexDLL.MTUSB_LEDDriverCloseDevice(handle)
        # match serial num
        if ctrlr_idx is None and serial_num is not None:
            idx = _invert_mapping(_controller_map)[serial_num]
            return cls(index=idx, serial_num=serial_num)
        elif (ctrlr_idx is not None) and (serial_num is None):
            return cls(index=ctrlr_idx,serial_num=_controller_map[ctrlr_idx])
        # both are None 
        else:
            raise ValueError('Must specify either controller index or serial number')

if __name__ == "__main__":
    controller = LEDController.get_controller(0)
    def test_TLedChannelData_mappings(controller:LEDController):
        # print(getdict(controller._ch_info[0][0]))
        print(repr(controller._ch_info[0][0]))
        print(controller._ch_info[0][0].to_mapping())
        print(repr(TLedChannelData.from_mapping(controller._ch_info[0][0].to_mapping())))
        print(repr(TLedChannelData.from_mapping(controller._ch_info[0][0].to_mapping())) == repr(controller._ch_info[0][0]))

    def test_controller_settings(controller:LEDController):
        print(controller.channel_info)
        controller.send_cmd('CURRENT 1 100')
        controller.send_cmd('TRIGGER 1 1000 0')
        print(controller.channel_info)
        # controller.set_parameters(1,{})

    # test_TLedChannelData_mappings(controller)
    # test_controller_settings(controller)