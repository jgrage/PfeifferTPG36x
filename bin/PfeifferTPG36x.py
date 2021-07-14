#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" Tango device classes for the Pfeiffer TPG36X vacuum gauge
controller series. This module uses the ethernet interface of
the new controller family. Per default the controller listens on
port 8000 for incoming tcp connections. Support for the serial
interface is not implemented yet.
"""

__author__ = "Jonas Grage"
__copyright__ = "Copyright 2020"
__license__ = "GPLv3"
__version__ = "1.0"
__maintainer__ = "Jonas Grage"
__email__ = "grage@physik.tu-berlin.de"
__status__ = "Production"


import sys

from time import time, sleep
from functools import partial
from configparser import ConfigParser

from tango import Attr, AttrQuality, AttrWriteType, DispLevel, DevState, DevFloat, DevString
from tango.server import Device, attribute, command, device_property, DeviceMeta, run

from PfeifferCommunication import PfeifferEthernetInterface


MEASUREMENT_STATUS = {
    0: 'Measurement data okay',
    1: 'Underrange',
    2: 'Overrange',
    3: 'Sensor error',
    4: 'Sensor off',
    5: 'No sensor',
    6: 'Identification error'
}

GAUGE_IDS = {
    'TPR/PCR': 'Pirani Gauge or Pirani Capacitive gauge',
    'IKR': 'Cold Cathode Gauge 10E-9 or 10E-11',
    ### TPG256 specific
    'TPR': 'Pirani Gauge or Pirani Capacitive gauge',
    'IKR9': 'Cold Cathode Gauge 10E-9 ',
    'IKR11': 'Cold Cathode Gauge 10E-11 ',
    'CMR': 'Linear gauge',
    ###
    'PKR': 'FullRange CC Gauge',
    'PBR': 'FullRange BA Gauge',
    'IMR': 'Pirani / High Pressure Gauge',
    'CMR/APR': 'Linear gauge',
    'noSEn': 'no sensor',
    'noSENSOR': 'no sensor',
    'noid': 'no identifier'
}

PRESSURE_UNITS = {
    0: 'mbar',
    1: 'Torr',
    2: 'Pa',
    3: 'Micron',
    4: 'hPa',
    5: 'Volt'}

class PfeifferTPG36x(Device):
    host = device_property(dtype=str)
    port = device_property(dtype=int, default_value=8000)


    def _read_pressure(self, channel, attr):
        """Function template for reading the pressure of a channel.
        This function is used to generate a bound method for each 
        pressure attribute r_meth inside the _factory() function.
        """
        self.debug_stream("read PressureCH{0:d}".format(channel + 1))
        mnemonic = "PR{:d}".format(channel + 1)
        
        response = self.connection.send(mnemonic)
        status = int(response[0])
        
        if status == 0:
            # Update pressure if gauge status is ok (0)
            pressure = float(response[1])
            quality = AttrQuality.ATTR_VALID
        else:
            """Set pressure to -1.0 and set quality to invalid if the
            gauge status is not ok.
            """
            pressure = -1.0
            quality = AttrQuality.ATTR_INVALID
        
        # Update the attribute
        attr.set_value_date_quality(pressure, time(), quality)
    
    def _read_status(self, channel, attr):
        """Function template for reading the status of a channel.
        This function is used to generate a bound method for each
        status attribute r_meth inside the _factory() function.
        """
        self.debug_stream("read StatusCH{0:d}".format(channel + 1))
        mnemonic = "PR{:d}".format(channel + 1)
        
        response = self.connection.send(mnemonic)
        status = MEASUREMENT_STATUS[int(response[0])]
        
        # Update the attribute
        attr.set_value_date_quality(status, time(), AttrQuality.ATTR_VALID)
    
    
    def _factory(self):
        """Generate callback methods for all attributes.
        
        This method is called once while initializing the device object
        and will create pressure and status attributes for each channel.
        The callback functions are generated by using the partial
        evaluation of the _read_pressure/_read_status methods with the
        coresponding channel number.
        Each attribute needs a bound r_meth callback method, but the 
        functools.partial function returns a partial object. Therefore
        we create a bound method using setattr() and pass it to the
        r_meth argument.
        """
        for number, name in self.channels.items():
            # Generate bound method as callback for reading pressure
            callback = partial(self._read_pressure, number)
            callback.__name__ = "_read_pressure_{0}".format(name)
            setattr(self, callback.__name__, callback)
            
            # Create pressure attr and connect the read callback method
            pressure_attr = Attr("Pressure{0}".format(name), DevFloat, AttrWriteType.READ)
            self.add_attribute(pressure_attr, r_meth=getattr(self, callback.__name__))
            
            # Generate bound method as callback for reading status
            callback = partial(self._read_status, number)
            callback.__name__ = "_read_status_{0}".format(name)
            setattr(self, callback.__name__, callback)
            
            # Create status attr and connect the read callback method
            status_attr = Attr("Status{0}".format(name), DevString, AttrWriteType.READ)
            self.add_attribute(status_attr, r_meth=getattr(self, callback.__name__))
            
    
    @command(dtype_out=[str], doc_out="Print the device ethernet configuration.")
    def EthernetParameters(self):
        self.debug_stream("print configuration of the ethernet interface")
        mnemonic = "ETH"
        response = self.connection.send(mnemonic)
        
        if response[0] == "0":
            method = "Static"
        else:
            method = "DHCP"
        address = "address:\t{0}".format(response[1])
        netmask = "netmask:\t{0}".format(response[2])
        gateway = "gateway:\t{0}".format(response[3])

        return [method, address, netmask, gateway]        
    

    @command(dtype_out=[str], doc_out="Print model parameters.")
    def AreYouThere(self):
        self.debug_stream("send AYT request")
        mnemonic = "AYT"
        response = self.connection.send(mnemonic)
        
        model = "model:\t{0}".format(response[0])
        modelnum = "model no.:\t{0}".format(response[1])
        serialnum = "serial no.:\t{0}".format(response[2])
        fw_version = "firmware vers.:\t{0}".format(response[3])
        hw_version = "hardware vers.:\t{0}".format(response[4])
        return [model, modelnum, serialnum, fw_version, hw_version]


    @command(dtype_out=[str], doc_out="Get a list of the types of all connected gauges. The list index corresponds to the channel number.")
    def IdentifyGauges(self):
        self.debug_stream("get types of connected gauges")
        mnemonic = "TID"
        ids = self.connection.send(mnemonic)
        return [GAUGE_IDS[i] for i in ids]

    """
    @command(dtype_in=str, dtype_out=str)
    def DisableChannel(self, channel):
        self.info_stream("disable channel {0}".format(channel))
        mnemonic = "SEN"
        arg_list = []

        for number, name in self.channels.items():
            if channel == name or channel == str(number):
                arg_list.append("1")
            else:
                arg_list.append("0")
        
        response = self.connection.send(mnemonic, *arg_list)
        for ch, status in enumerate(response):
            if status == "0":
                msg = "channel {0} can't be turned off".format(ch+1)
                self.error_stream(msg)
            else:
                pass
                
                
    @command(dtype_in=str, dtype_out=str)
    def EnableChannel(self, channel):
        self.info_stream("enable channel {0}".format(channel))
        mnemonic = "SEN"
        arg_list = []

        for number, name in self.channels.items():
            if channel == name or channel == str(number):
                arg_list.append("2")
            else:
                arg_list.append("0")
        print(arg_list)
        
        response = self.connection.send(mnemonic, *arg_list)
        for ch, status in enumerate(response):
            if status == "0":
                msg = "channel {0} can't be turned on".format(ch+1)
                self.error_stream(msg)
            else:
                pass
    """


    @attribute(label="operating hours", display_level=DispLevel.OPERATOR, dtype=int, unit="h", doc="Get the total number of operating hours")
    def OperatingHours(self):
        self.debug_stream("read operating hours")
        mnemonic = "RHR"
        hours = self.connection.send(mnemonic)[0]
        return int(hours)
    

    @attribute(label="firmware version", display_level=DispLevel.OPERATOR, dtype=str, doc="Get the firmware version")            
    def FirmwareVersion(self):
        self.debug_stream("read firmware version")
        mnemonic = "PNR"
        version = self.connection.send(mnemonic)[0]
        return version
    
    
    @attribute(label="hardware version", display_level=DispLevel.OPERATOR, dtype=str, doc="Get the hardware version")            
    def HardwareVersion(self):
        self.debug_stream("read hardware version")
        mnemonic = "HDW"
        version = self.connection.send(mnemonic)[0]
        return version


    @attribute(label="mac address", display_level=DispLevel.OPERATOR, dtype=str, doc="Get the device MAC address")            
    def MACAddress(self):
        self.debug_stream("read hardware MAC address")
        mnemonic = "MAC"
        mac = self.connection.send(mnemonic)[0]
        return mac


    @attribute(label="inner temperature", display_level=DispLevel.OPERATOR, dtype=float, unit="°C", doc="Get the temperature inside the unit")  
    def InnerTemperature(self):
        self.debug_stream("read inner temperature")
        mnemonic = "TMP"
        temperature = float(self.connection.send(mnemonic)[0])
        return temperature
    

    @attribute(label="pressure unit", display_level=DispLevel.OPERATOR, dtype=str, doc="Get the configured pressure unit")            
    def PressureUnit(self):
        self.debug_stream("read PressureUnit")
        mnemonic = "UNI"
        unit_id = int(self.connection.send(mnemonic)[0])
        return PRESSURE_UNITS[unit_id], time(), AttrQuality.ATTR_VALID
    
    
    @PressureUnit.write
    def PressureUnit(self, unit):
        """Change the pressure unit used to display the pressure values.
        The unit has to be valid value of the PRESSURE_UNITS dict.
        """
        self.debug_stream("set PressureUnit to {0}".format(unit))
        mnemonic = "UNI"
        for key, value in PRESSURE_UNITS.items():
            if value == unit:
                # Send command if the argument is a valid unit
                self.connection.send(mnemonic, key)
                return
                
        # Log error if the user passed an invalid unit setting
        self.error_stream("error setting PressureUnit to {0}: Invalid unit".format(unit))
                
                
    def init_device(self):
        """Initialize the device by creating the pressure and status
        attributes for each channel.
        
        First the names of all $(self.number_of_channels channels) are
        generated. Then the _factory() method is called to create all
        attributes and callback functions with the _read_pressure and
        _read_status templates.
        Afterwards a tcp connection to the controller hardware will be
        established.
        """
        self.info_stream("call init_device() ({0})".format(self.__class__.__name__))
        Device.init_device(self)
        self.set_state(DevState.INIT)
        
        # Create channels and attributes
        self.channels = {n: "CH{0:d}".format(n+1) for n in range(self.number_of_channels)}
        self._factory()
        
        # Establish connection to controller
        try:
            self.connection = PfeifferEthernetInterface(self.host, self.port)
            sleep(1)
            self.info_stream("connected to {0} device at {1}:{2:d}".format(self.__class__.__name__, self.host, self.port))
            self.set_state(DevState.ON)
        
        # Exit if connection can't be established
        except Exception as exc:
            self.error_stream("error in init_device(): {0}".format(exc))
            self.set_state(DevState.OFF)
            sys.exit()
        
        
class PfeifferTPG361(PfeifferTPG36x):
    number_of_channels = 1

        
class PfeifferTPG362(PfeifferTPG36x):
    number_of_channels = 2
        
        
class PfeifferTPG366(PfeifferTPG36x):
    number_of_channels = 6
        
        
if __name__ == "__main__":
    PfeifferTPG361.run_server()