import serial

class RS232Class:
    def __init__(self, port, baudrate = 19200, parity = serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS, timeout=10):
        self.__port = port
        self.__baudrate = baudrate
        self.__parity = parity
        self.__stopbits = stopbits
        self.__bytesize = bytesize
        self.__timeout = timeout
        self.__connection = None

    def open(self):
        error = None
        try:
            self.__connection = serial.Serial(
                port=self.__port,
                baudrate=self.__baudrate,
                parity=self.__parity,
                stopbits=self.__stopbits,
                bytesize=self.__bytesize,
                timeout=self.__timeout
            )
        except serial.SerialException:
            error = "Failed to connect to RS232"
        return error

    def close(self):
        error = None
        if self.__connection:
            try:
                self.__connection.close()
                self.__connection = None
            except:
                error = f'Error closing RS232 Connection'
        else:
            error = 'RS232 port could not disconnect'
        return error

    def send_command(self, command):
        error = None
        if self.__connection:
           try:
                self.__connection.write((command+'\n\r').encode('utf-8'))
           except:
                error = f"Error sending command"
        else:
            error = "Not connected to the RS232 Relay Port"
        return error

    def read_response(self):
        error = None
        if self.__connection:
            try:
                response = self.__connection.read(self.__connection.in_waiting)
                response = response.decode().strip()
            except:
                error = f"Error reading response"
                response = None
        else:
            error = "Not connected to the RS232"
            response = None
        return response, error

    def __del__(self):
        self.close()