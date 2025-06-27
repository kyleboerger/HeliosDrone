#!/usr/bin/python
# -------------------------------------------------------------------------------
#
#             COPYRIGHT 2024 MOTOROLA SOLUTIONS INC. ALL RIGHTS RESERVED.
#                    MOTOROLA SOLUTIONS CONFIDENTIAL RESTRICTED
#
# -------------------------------------------------------------------------------
import socket
import struct
import binascii

class SocketController:

    def __init__(self, radio_ip, radio_port, mode):
        self.radio_ip = radio_ip
        self.radio_port = radio_port
        self.mode = mode
        self.connected = False

#------------------------------------------------------------------------------------------------------------------
    def connect(self, timeout, radio_ip=None, radio_port=None):
        errorStatus = 'None'

        if self.connected == False:
            dest_radio_ip = radio_ip
            dest_radio_port = radio_port
            if dest_radio_ip == None:
                dest_radio_ip = self.radio_ip
            if dest_radio_port == None:
                dest_radio_port = self.radio_port

            self.radio_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.radio_socket.settimeout(timeout)

            try :
                self.radio_socket.connect((dest_radio_ip, dest_radio_port))
                self.connected = True
            except :
                errorStatus = 'Unable to connect to IP: ' + str(dest_radio_ip) + ' Port: ' + str(dest_radio_port)

        return errorStatus

#------------------------------------------------------------------------------------------------------------------
    def disconnect(self):
        errorStatus = 'None'
        try :
            if self.connected == True:
                self.radio_socket.close()
                self.connected = False
        except :
            errorStatus = 'Unable to close socket'

        return errorStatus

#------------------------------------------------------------------------------------------------------------------
    def write(self, data):

        errorStatus = 'None'

        if self.mode == 'rcmp':
            s = struct.Struct('> H' )
            tempData = binascii.unhexlify(data)
            header = s.pack(len(tempData))
            dataToSend = header + tempData
        else:
            data = data + '\r\n'
            encoded=data.encode('utf-8')
            dataToSend =bytearray(encoded)

        try :
            self.radio_socket.send(dataToSend)
        except:
            errorStatus = 'Unable to write'

        return errorStatus

#------------------------------------------------------------------------------------------------------------------
    def read(self):
        errorStatus = 'None'
        dataToReturn = None
        try :
            dataToReturn = self.radio_socket.recv(4096)
            if self.mode == 'rcmp':
                dataToReturn = dataToReturn[2:] # chop off the length

        except :
            errorStatus = 'Unable to recv'

        return dataToReturn, errorStatus

#------------------------------------------------------------------------------------------------------------------
    def handle_request_and_reply(self, command, expectedResponse = 'None', timeout = 2):
        reply = None
        errorStatus = 'None'
        reply_verification = 'Pass'

        if command != None and self.connected:
            self.radio_socket.settimeout(timeout)
            errorStatus = self.write(command)
            if errorStatus == 'None':
                reply, errorStatus = self.read()
                if expectedResponse != 'None':
                    reply_verification = 'Fail'
                    if reply != None:
                        if expectedResponse in str(binascii.hexlify(reply)):
                            reply_verification = 'Pass'
            else:
                reply_verification = 'Fail'

        return reply, reply_verification, errorStatus