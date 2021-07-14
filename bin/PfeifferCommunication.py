#!/usr/bin/env python
# -*- coding:utf-8 -*-

import sys
import socket
from time import sleep

ETX = '\x03'
CR = '\x0D'
LF = '\x0A'
ENQ = '\x05'
ACK = '\x06'
NAK = '\x15'
RESP_END = '\x0D\x0A'

class CommandError(Exception):
    def __init__(self, commandstring, message):
        self.message = message
        self.commandstring = commandstring
        super().__init__(self.message)

    def __str__(self):
        return f"{self.commandstring} -> {self.message}"


class CommandSyntaxError(CommandError):
    def __init__(self, commandstring, message="Syntax error in command!"):
        super().__init__(commandstring, message)


class InadmissibleParameterError(CommandError):
    def __init__(self, commandstring, message="Inadmissible parameter was left out!"):
        super().__init__(commandstring, message)


class Error(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return self.message


class NoHardwareError(Error):
    def __init__(self, message="No Hardware!"):
        super().__init__(message)


class ControllerError(Error):
    def __init__(self, message="Controller error occured! Check display."):
        super().__init__(message)


class UnknownErrorWord(Error):
    def __init__(self, message="Error word unknown or incomplete transmission"):
        super().__init__(message)


class PfeifferEthernetInterface:
    def __init__(self, HOST, PORT):
        self.interface = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.interface.settimeout(5)
        IP = socket.gethostbyname(HOST)
        self.interface.connect((IP, PORT))
        
    def receive(self):
        sleep(0.01)
        data = self.interface.recv(1024)
        if CR.encode() in data:
            response, *rest = data.split(CR.encode())
            return response.decode().split(',')
        else:
            raise SocketError
            
    def _enq(self):
        self.interface.send(ENQ.encode())
    
    def _get_data(self):
        self._enq()
        return self.receive()
        
    def _get_error(self):
        self.interface.send("ERR")
        response = self.receive()[0]
        
        if response == ACK:
            self._enq()
            error_word = self.receive()[0]
            if error_word == "0001":
                raise CommandSyntaxError(commandstring.encode())
            elif error_word == "0010":
                raise InadmissibleParameterError(commandstring.encode())
            elif error_word == "0100":
                raise NoHardwareError
            elif error_word == "1000":
                raise ControllerError
            else:
                raise UnknownErrorWord
        else:
            raise Exception
    
    
    def send(self, mnemonic: str, *argv):
        tmp = [mnemonic]
        
        # Build the commandstring
        for arg in argv:
            tmp.append(',')
            tmp.append(str(arg))
        tmp.append(CR)
        commandstring = ''.join(tmp)
        
        # Send command to device
        self.interface.send(commandstring.encode())
        
        # Wait for ACK and handle response
        response = self.receive()[0]
        if response == ACK:
            return self._get_data()
        elif response == NAK:
            self._get_error()
        else:
            raise Exception
            
    def __del__(self): 
        self.interface.close()
        
        
class PfeifferSerialInterface:
    def __init__(self):
        raise NotImplementedError
        
    def __del__(self):
        raise NotImplementedError
