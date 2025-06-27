import serial
import time

class SerialController:
    def __init__(self, com_port, baudrate=9600):
        self.__com_port = com_port
        self.__baudrate = baudrate
        self.__socket = None

    def open(self):
        try:
            self.__socket = serial.Serial(self.__com_port, baudrate=self.__baudrate, timeout=1)
            return None
        except Exception as error:
            return error
    
    def close(self):
        if self.__socket:
            self.__socket.close()

        
    def send_command(self, command):
        response = None  # Initialize response
        error = None
        try:
            self.__socket.write(command.encode())
            time.sleep(0.1)

            # Read the response
            received_data = bytearray()
            if self.__socket.in_waiting > 0:
                data_chunk = self.__socket.read(self.__socket.in_waiting)
                received_data.extend(data_chunk)

            if received_data:
                response = received_data.decode()

        except Exception as e:
            error = f"Error while sending command to serial {self.__com_port}: {e}"

        return response, error