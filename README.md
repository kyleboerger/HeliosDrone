# ##############################################
#   Helios - Drone Software
#
#   Using SocketController.py, there is a socket
#   based communication for the radios over
#   TCP/IP.
#
#   Using SerialController.py, there is a serial
#   based communication for the radios over the
#   COM port.
#
#   #DeciveControllers.py uses RS323.py to 
#   help control the usb relay, together with 
#   SerialController.py and SocketController.py.
#   This allows for the radios, one transmitting 
#   and one recieving, allow for the drone to act 
#   as a radio to constantly hear and send out
#   information. 
#
#   Using textToCommand.ipynb &&
#   textToCommand.py the commands spoken
#   (already converted to text) allow them
#   to be useable for the drone to understand
#   
#   Using prompting.py and image_parsing.py
#   together with MSI Generative AI, window.py
#   was created and allows us to access the
#   Claude-Sonet AI to answer questions and
#   parse through images with memory.
#
#   Using text_to_speech.py, getting input
#   from window.py allows for the AI response
#   to be spoken via microphone from text.
#
#   EthRequest.py allows for the computer to be
#   connected to Ethernet while on Wifi with the
#   drone so that the drone can recieve AI
#   responses from the model while not connected.
#
#   Finally main.py brings together all of the
#   scripts and allows for the drone to be 
#   communicated to via a radio and see real
#   time responses to any question or command.
#
# ##############################################