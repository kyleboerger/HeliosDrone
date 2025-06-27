from subprocess import Popen, PIPE
from datetime import datetime
from time import sleep
from abc import ABC, abstractmethod

from SocketController import SocketController
from TelnetController import TelnetController
from SerialController import SerialController
from RS232Class import RS232Class

class DeviceController(ABC):
    def log(self, content, prefix="", write_only=False):
        print(prefix + content)

    def execute_with_retry(self, function, params, time_before_retry=15, potential_fix=None, last_resort_fix=None, attempt_number=1, max_attempts=5):
        try:
            response, error = function(*params)
            if error:
                raise Exception(error)
                
            if attempt_number > 1:
                self.log(f"SUCCESS: Reattempt successful, execution of '{function.__name__}' with params '{params}' successful on attempt number {attempt_number}")
            return response
        
        except Exception as e:
            self.log(f"Error executing '{function.__name__}' with params '{params}': {e}")
            if attempt_number < max_attempts:
                self.log(f"Waiting {time_before_retry}s before reattempting execution of '{function.__name__}' with params '{params}', attempt number {attempt_number}")
                sleep(time_before_retry)
                self.log(f"Reattempting execution of '{function.__name__}' with params '{params}', attempt number {attempt_number}")
                
                if last_resort_fix and attempt_number >= max_attempts - 1:
                    last_resort_fix()

                if potential_fix:
                    potential_fix()

                return self.execute_with_retry(function, params, time_before_retry, potential_fix, last_resort_fix, attempt_number+1, max_attempts)
            else:
                self.log(f"Failed to execute '{function.__name__}' with params '{params}' after {attempt_number} attempts, exceeded maxmimum number of attempts")
                raise Exception(f"Failed to execute '{function.__name__}' with params '{params}' after {attempt_number} attempts")
    
    @abstractmethod
    def close_connections(self):
        pass

    def __del__(self):
        self.close_connections()


class Radio(DeviceController):
    def __init__(self, radio_ip="192.168.128.1", nickname=None, logfolder_path=None):
        self.__radio_ip = radio_ip
        self.__radio_nickname = nickname
        self.__logfolder_path = logfolder_path
        self.__telnet_controller = TelnetController(self.__radio_ip)
        self.__telnet_connected = False
        self.__rcmp_controller = SocketController(self.__radio_ip, 8002, "rcmp")
        self.__rcmp_connected = False

        self.__ref_osc_dac_prefix = None

    def get_ip(self):
        return self.__radio_ip

    def log(self, content, prefix="", write_only=False, log_metadata=True):
        if content:
            identifier = self.__radio_nickname if self.__radio_nickname else self.__radio_ip

            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            if log_metadata:
                message = f"{prefix}{current_time} | Radio '{identifier}' | {content}"
            else:
                message = f"{prefix}{content}"
            
            if not write_only:
                print(message)

            if self.__logfolder_path:
                filepath = f"{self.__logfolder_path}/{identifier}.txt"
                with open(filepath, "a") as f:
                    f.write(message)
                    f.write("\n")

    # Telnet
    def connect_telnet(self):
        error = self.__telnet_controller.connect()
        if error:
            return f"Error connecting via telnet: {error}"
        self.__telnet_connected = True
        sleep(0.1)
        return None
    
    def reconnect_telnet(self):
        if self.__telnet_controller:
            self.__telnet_controller.disconnect()
        self.connect_telnet()

    def send_telnet_command(self, command):
        if not self.__telnet_connected:
            error = self.connect_telnet()
            if error:
                return None, error

        response, error = self.__telnet_controller.send_command(command + '\r\n')
        if error:
            return None, f"Error sending telnet command '{command}': {error}" 
        
        return response, error
    
    def send_telnet_command_with_retry(self, command):
        return super().execute_with_retry(self.send_telnet_command, (command,), potential_fix=self.reconnect_telnet, last_resort_fix=self.reconfigure_radio)
    
    # RCMP
    def connect_rcmp(self):
        error = self.__rcmp_controller.connect(10)
        if error != 'None':
            return f"Error connecting via rcmp: {error}"
        self.__rcmp_connected = True
        sleep(0.1)
        return None
    
    def reconnect_rcmp(self):
        if self.__rcmp_controller:
            self.__rcmp_controller.disconnect()
        self.connect_rcmp()

    def send_rcmp_command(self, command, timeout=2):
        if not self.__rcmp_connected:
            error = self.connect_rcmp()
            if error:
                return None, error
            
        response, reply_verification, error = self.__rcmp_controller.handle_request_and_reply(command, timeout=timeout)
        # SocketController returns 'None' as a string instead of None
        if error != 'None':
            return None, f"Error sending rcmp command '{command}': {error}" 
        if not response:
            return None, f"No response when sending rcmp command '{command}'"
        
        return response, None
    
    def send_rcmp_command_with_retry(self, command, timeout=2):
        return super().execute_with_retry(self.send_rcmp_command, (command,timeout), potential_fix=self.reconnect_rcmp, last_resort_fix=self.reconfigure_radio)

    @staticmethod
    def to_hex_str(value, length):
        return format(value, f"0{length}x")

    def enter_test_mode(self):
        self.send_rcmp_command_with_retry("000c", timeout=20)

    # sets TX power level to either high or low or to a custom value in milli dBm
    def set_tx_power_level(self, level):
        if level == "high":
            self.send_rcmp_command_with_retry("000600")
        elif level == "low":
            self.send_rcmp_command_with_retry("000603")
        elif isinstance(level, int):
            level_hex_str = Radio.to_hex_str(level, 4)
            self.send_rcmp_command_with_retry(f"0006ff{level_hex_str}")
        else:
            self.log(f"Invalid power level: {level}")

    def set_tx_freq_hz(self, freq, bandwidth=100, deviation=0):
        # frequency value is the number of 5hz steps from 0 to reach desired frequency
        freq_hex_str = Radio.to_hex_str(freq // 5, 8)
        bandwidth_hex_str = Radio.to_hex_str(bandwidth, 2)
        deviation_hex_str = Radio.to_hex_str(deviation, 2)
        self.send_rcmp_command_with_retry(f"000b{freq_hex_str}{bandwidth_hex_str}{deviation_hex_str}")

    def set_rx_freq_hz(self, freq, bandwidth=100):
        # frequency value is the number of 5hz steps from 0 to reach desired frequency
        freq_hex_str = Radio.to_hex_str(freq // 5, 8)
        bandwidth_hex_str = Radio.to_hex_str(bandwidth, 2)
        self.send_rcmp_command_with_retry(f"000a{freq_hex_str}{bandwidth_hex_str}00")

    def transmit_muted(self):
        self.send_rcmp_command_with_retry("000403")
    
    def transmit(self):
        self.send_rcmp_command_with_retry("000402")

    def receive(self):
        self.send_rcmp_command_with_retry("000502")

    def get_ref_osc_dac_value(self, attempt_number=1, max_attempts=5):
        self.send_telnet_command_with_retry("radiodebugger")
        sblast_resp = self.send_telnet_command_with_retry("SBLAST:SPI:RODINIA_CS:8C000000")
        sblast_resp = sblast_resp.split("Data received:")[1].strip('\r\x00\n') # get just the value from data received
        sblast_resp = sblast_resp[-4:] # get the last two bytes

        if sblast_resp == "FFFF":
            if attempt_number <= max_attempts:
                self.log("Retrying get reference oscillator DAC value")
                sleep(10)
                return self.get_ref_osc_dac_value(attempt_number=attempt_number+1)
            else:
                self.log("Failed getting reference oscillator DAC value")

        sblast_resp = int(sblast_resp, 16) # convert from hex string to value
        ref_osc_dac_val = sblast_resp & 0x7ff # get bits 0-10

        # store bits 11-15 to write back later
        self.__ref_osc_dac_prefix = sblast_resp & 0xf800 # keep bits 11-15 and clear 0-10


        return ref_osc_dac_val
    
    def write_ref_osc_dac_value(self, val):
        # if we have not gotten and stored the prefix, get it
        if self.__ref_osc_dac_prefix is None:
            self.get_ref_osc_dac_value()

        if val > 0x7ff:
            self.log("Error when writing to reference osicillator DAC value: value too large")
            return False

        ref_osc_write = self.__ref_osc_dac_prefix | val # fill bits 0-10 with new value
        ref_osc_write = Radio.to_hex_str(ref_osc_write, 4)
        self.send_telnet_command_with_retry(f"SBLAST:SPI:RODINIA_CS:0C00{ref_osc_write}") # write new value to DAC
        return True


    def reconfigure_radio(self):
        error = b''
        try:
            self.log(f"Trying to reconfigure radio as PnP device in order to fix a common issue setting up the radio with Windows, only works when run from an administrator environment")

            terminal_command = "powershell.exe Get-PnpDevice -PresentOnly -FriendlyName \"*Motorola*\" | Disable-PnpDevice -Confirm:$false".split(" ")
            p = Popen(terminal_command, stdout=PIPE, stderr=PIPE)
            terminal_output, terminal_error = p.communicate()
            error += terminal_error

            sleep(10)

            terminal_command = "powershell.exe Get-PnpDevice -PresentOnly -FriendlyName \"*Motorola*\" | Enable-PnpDevice -Confirm:$false".split(" ")
            p = Popen(terminal_command, stdout=PIPE, stderr=PIPE)
            terminal_output, terminal_error = p.communicate()
            error += terminal_error
            
            if len(error > 0):
                return error
            else:
                return None
            
        except Exception as e:
            self.log(f"Tried to reconfigure radio as PnP device, but the process failed. Make sure this is running in an administrator environment: {e}")
            return e
        
    
            
    def close_connections(self):
        if self.__telnet_connected:
            self.__telnet_controller.disconnect()
        self.__telnet_connected = False

        if self.__rcmp_connected:
            self.__rcmp_controller.disconnect()
        self.__rcmp_connected = False
        
    def reboot(self):
        self.send_rcmp_command_with_retry("000D")
        self.close_connections()

    def get_battery_level(self, attempt_number=1, max_attempts=5):
        response = self.send_rcmp_command_with_retry("041080")
        batt_level = response[5]
        if batt_level == 255:
            if attempt_number <= max_attempts:
                self.log("Reattempting get battery level")
                sleep(10)
                return self.get_battery_level(attempt_number=attempt_number+1, max_attempts=max_attempts)
            else:
                self.log(f"Could not get battery level after {max_attempts} attempts")
                return 255
        return batt_level
    
    def get_battery_level_and_auth_status(self, attempt_number=1, max_attempts=5):
        response = self.send_rcmp_command_with_retry("041080")
        batt_level = response[5]
        batt_auth_status = (response[-1] >> 4) & 0b1 # Get value of authentication bit
        if batt_level == 255:
            if attempt_number <= max_attempts:
                self.log("Reattempting get battery level and authentication status")
                sleep(10)
                return self.get_battery_level_and_auth_status(attempt_number=attempt_number+1, max_attempts=max_attempts)
            else:
                self.log(f"Could not get battery level and authentication status after {max_attempts} attempts")
                return 255, 0
        return batt_level, batt_auth_status
    
    
class SerialDevice(DeviceController):
    def __init__(self, controller, connected_radios=[], name="Serial Device"):
        self.__connected_radios = connected_radios
        self._controller = controller
        self._connected = False
        self.__name = name

    def log(self, content, prefix="", write_only=False):
        if self.__connected_radios:
            for radio in self.__connected_radios:
                radio.log(content, prefix=prefix, write_only=write_only)
        else:
            print(content)

    def connect(self):
        error = self._controller.open()
        if error:
            return f"Error connecting to {self.__name}: {error}"
        self._connected = True
        sleep(0.1)
        return None
    
    def reconnect(self):
        if self._controller:
            self._controller.close()
        self.connect()

    def send_command(self, command):
        if not self._connected:
            error = self.connect()
            if error:
                return None, error
    
        error = self._controller.send_command(command)
        if error:
            return None, f"Error sending command to {self.__name}: {error}" 
        
        return None, None
    
    def send_command_with_retry(self, command):
        super().execute_with_retry(self.send_command, (command,), potential_fix=self.reconnect)

    def close_connections(self):
        if self._connected:
            self._controller.close()
        self._connected = False

class iBootPDU(SerialDevice):
    def __init__(self, com_port, password, num_outlets, baudrate=115200, connected_radios=[]):
        controller = SerialController(com_port, baudrate=baudrate)
        super().__init__(controller, connected_radios=connected_radios, name="iBootPDU")
        self.__password = password
        self.__outlets = [x for x in range(1, num_outlets+1)]

    def send_command(self, command):
        if not self._connected:
            error = self.connect()
            if error:
                return None, error
        # log in to bootbox
        self._controller.send_command("abc\n") # it frequently loses the first few bytes, so send dummy username at first
        self._controller.send_command("admin\n")
        self._controller.send_command(f"{self.__password}\n")
        response, error = self._controller.send_command(command + "\n")
        if error:
            return None, f"Error sending command to boot box: {error}" 
        if "Ok" not in response:
            return response, f"Error sending command to boot box: {response}" 
        
        return response, error
            
    def turn_outlets_on(self):
        for outlet in self.__outlets:
            self.send_command_with_retry(f"set outlet {outlet} on")

    def turn_outlets_off(self):
        for outlet in self.__outlets:
            self.send_command_with_retry(f"set outlet {outlet} off")


class USBRelay(SerialDevice):
    def __init__(self, com_port, baudrate=9600, connected_radios=[], num_switches=4, name="USBRelay"):
        controller = RS232Class(com_port, baudrate=baudrate)
        super().__init__(controller, connected_radios=connected_radios, name="USBRelay")
        self.__num_switches = num_switches
            
    def turn_all_switches_on(self):
        for i in range(0, self.__num_switches + 1):
            self.send_command_with_retry(f"relay on {i}")

    def turn_all_switches_off(self):
        for i in range(0, self.__num_switches + 1):
            self.send_command_with_retry(f"relay off {i}")