import socket

class TelnetController:
    def __init__(self, radio_ip):
        self.__radio_ip = radio_ip
        self.__connection = None

    def connect(self):
        error = None
        try:
            self.__connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.__connection.settimeout(1)  # Set a timeout for the connection
            self.__connection.connect((self.__radio_ip, 23))
        except Exception as e:
            error = f'Unable to connect to telnet socket: {e}'

        return error
    
    def disconnect(self):
        error = None
        try:
            if self.connected == True:
                self.radio_socket.close()
                self.connected = False
        except Exception as e:
            error = f'Unable to close socket: {e}'

        return error
        

    def receive_all(self, buffer_size=1024, debug=False): # Function to receive all data from the Telnet server
        data = b''
        while True:
            try:
                part = self.__connection.recv(buffer_size)
                if not part:
                    break
                data += part
            except socket.timeout:
                break

        # Get the hexadecimal representation of the data
        hex_data = data.hex()

        # Convert the hexadecimal data to ASCII
        ascii_data = bytes.fromhex(hex_data).decode('ascii', errors='replace')

        if debug:
            print('Received (ASCII):', ascii_data, "\n")
            
        return ascii_data

        
    def send_command(self, command, command_type='ascii'):
        response = None
        try:
            if command_type == 'hex':
                command = bytes.fromhex(command)
            elif command_type == 'ascii':
                command = command.encode('ascii')
            else:
                return None, "Invalid command type. Please use 'hex' or 'ascii'."

            self.__connection.sendall(command)
            try:
                if command_type == 'hex':
                    response = self.__connection.recv(1024)
                elif command_type == 'ascii':
                    response = self.receive_all()

            except socket.timeout:
                return None, "No response received."
            except Exception as e:
                return None, f"Error while receiving response: {e}"

        except Exception as e:
            return None, f"Error while sending command: {e}"

        return response, None