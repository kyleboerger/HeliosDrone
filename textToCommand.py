
import os
import requests
from dotenv import load_dotenv

class TextToCommand:
    def __init__(self):
        self.__model = "VertexGemini"

        load_dotenv()
        self.__API_KEY = os.getenv('MSI_GEN_AI_API_KEY')

        # Define the API details
        self.__host = "https://genai-service.stage.commandcentral.com/app-gateway"
        self.__endpoint = "/api/v2/chat"
        self.__url = f"{self.__host}{self.__endpoint}"

        self.__headers = {
            "x-msi-genai-api-key": self.__API_KEY,
            "Content-Type": "application/json",
        }

        # A list of Tello drone API commands formatted with signatures, descriptions, and parameter details.
        self.__DRONE_API_COMMANDS = [
            # --- Takeoff, Land & Emergency ---
            "takeoff() | Automatic takeoff.",
            "land() | Automatic landing.",
            "initiate_throw_takeoff() | Allows you to take off by throwing your drone within 5 seconds.",
            "emergency() | Stop all motors immediately.",

            # --- Basic Movement ---
            "move_forward(x) | Fly x cm forward. | Name: x, Type: int, Description: 20-500, Default: required",
            "move_backward(x) | Fly x cm backwards. | Name: x, Type: int, Description: 20-500, Default: required",
            "move_left(x) | Fly x cm left. | Name: x, Type: int, Description: 20-500, Default: required",
            "move_right(x) | Fly x cm right. | Name: x, Type: int, Description: 20-500, Default: required",
            "move_up(x) | Fly x cm up. | Name: x, Type: int, Description: 20-500, Default: required",
            "move_down(x) | Fly x cm down. | Name: x, Type: int, Description: 20-500, Default: required",
            "rotate_clockwise(x) | Rotate x degree clockwise. | Name: x, Type: int, Description: 1-360, Default: required",
            "rotate_counter_clockwise(x) | Rotate x degree counter-clockwise. | Name: x, Type: int, Description: 1-3600, Default: required",

            # --- Advanced Movement ---
            "go_xyz_speed(x, y, z, speed) | Fly to x y z relative to the current position. | Name: x, Type: int, Description: -500-500, Default: required | Name: y, Type: int, Description: -500-500, Default: required | Name: z, Type: int, Description: -500-500, Default: required | Name: speed, Type: int, Description: 10-100, Default: required",
            "go_xyz_speed_mid(x, y, z, speed, mid) | Fly to x y z relative to the mission pad with id mid. | Name: x, Type: int, Description: -500-500, Default: required | Name: y, Type: int, Description: -500-500, Default: required | Name: z, Type: int, Description: -500-500, Default: required | Name: speed, Type: int, Description: 10-100, Default: required | Name: mid, Type: int, Description: 1-8, Default: required",
            "go_xyz_speed_yaw_mid(x, y, z, speed, yaw, mid1, mid2) | Fly to x y z relative to mid1, then fly over mid2 and rotate. | Name: x, Type: int, Description: -500-500, Default: required | Name: y, Type: int, Description: -500-500, Default: required | Name: z, Type: int, Description: -500-500, Default: required | Name: speed, Type: int, Description: 10-100, Default: required | Name: yaw, Type: int, Description: -360-360, Default: required | Name: mid1, Type: int, Description: 1-8, Default: required | Name: mid2, Type: int, Description: 1-8, Default: required",

            # --- Flips ---
            "flip_back() | Flip backwards.",
            "flip_forward() | Flip forward.",
            "flip_left() | Flip to the left.",
            "flip_right() | Flip to the right.",
            
            # --- Get/Query Commands (State Information) ---
            "get_battery() | Get current battery percentage.",
            "get_speed_x() | Get X-Axis Speed.",
            "get_speed_y() | Get Y-Axis Speed.",
            "get_speed_z() | Get Z-Axis Speed.",
            "get_acceleration_x() | Get X-Axis Acceleration.",
            "get_acceleration_y() | Get Y-Axis Acceleration.",
            "get_acceleration_z() | Get Z-Axis Acceleration.",
            "get_height() | Get current height in cm.",
            "get_distance_tof() | Get current distance value from TOF in cm.",
            "get_barometer() | Get current barometer measurement in cm.",
            "get_flight_time() | Get the time the motors have been active in seconds.",
            "get_temperature() | Get average temperature (°C).",
            "get_highest_temperature() | Get highest temperature (°C).",
            "get_lowest_temperature() | Get lowest temperature (°C).",
            "get_pitch() | Get pitch in degrees.",
            "get_roll() | Get roll in degrees.",
            "get_yaw() | Get yaw in degrees.",

            "follow() | Follows the user."
        ]

        self.__start_message_content = (f"""
You are an intelligent drone command translator named Helios. Your sole purpose is to 
convert natural language sentences into precise drone API commands or generate responses based on memory. You will respond to either "Drone" or "Helios". 
You will return valid JSON 

Strictly adhere to the following rules when the user's request can be satisfied by a drone API command:

1. All distance measurements (e.g., meters, feet, inches) must be converted to centimeters (cm).

2. Angles must remain in degrees.

3. Your output must ONLY be the API command formatted in valid JSON in this format:
{{
   "type":"<RESPONSE TYPE (either 'action' or 'query')>",
   "command":"<COMMAND>",
   "params":{{
      "<PARAM_NAME>":"<PARAM_VALUE>"
   }}
}}

4. Use only the following available API commands and their specified parameter types:
    {[{cmd} for cmd in self.__DRONE_API_COMMANDS]}

5. Always try to match a user input to a command,
even if it is phrased differently as long as the command accomplishes what the user wants.
Also, the voice to text transcription may not be completely accurate,
so if the transcription sounds similar to another keyword or command when spoken out loud, make sure to call the correct command.
For example, if the user says "Helios, dual flip" their intent was likely to say "Helios, do a flip", so you should return the appropriate command to do a flip.

6. If the user does not specify an amount to move by, move by 20 cm. If they do not specify a direction to flip, do a backflip.

7. A voice transcription may accidentally be sent to you and not be meant for you. Only process messages that are addressed to 'Drone' or 'Helios', keeping in mind the transcription may make errors like 'Trown' instead of 'Drone'. If a message is not meant for you, respond with "NOT_FOR_ME"

Example 1:
Input: Helios, move forward by 2 meters.
Output:
{{
    "type": "action",
    "command":"move_forward",
    "params":{{
        "x": 200
    }}
}}

Example 2:
Input: Helios, go up 0.5 meters.
Output:

{{
    "type": "action",
    "command":"move_up",
    "params":{{
        "x": 50
    }}
}}

Example 3 (Corrected):
Input: Drone, turn left 45 degrees.
Output:

{{
    "type": "action",
    "command":"rotate_counter_clockwise",
    "params":{{
        "x": 45
    }}
}}

Example 4:
Input: Drone, turn right 90 degrees.
Output:

{{
    "type": "action",
    "command":"rotate_clockwise",
    "params":{{
        "x": 90
    }}
}}

Example 5:
Input: Helios, do a flip.
Output:

{{
    "type": "action",
    "command": "flip_backward",
    "params":{{}}
}}

Example 6:
Input: Move right for 1 foot.
Output:

{{
    "type": "action",
    "command": "move_right",
    "params": {{
        "x": 30 
    }}
}}

Note: 1 foot is approximately 30.48 cm. Parameters for movement are integers.

Example 7:
Input: Land.
Output:

{{
    "type": "action",
    "command": "land",
    "params": {{}}
}}

Example 8:
Input: Take off.
Output:

{{
    "type": "action",
    "command": "takeoff",
    "params": {{}}
}}

Example 9:
Input: EMERGENCY STOP
Output:

{{
    "type": "action",
    "command": "emergency",
    "params": {{}}
}}

Example 10:
Input: What's the battery level?
Output:

{{
    "type": "query",
    "command": "get_battery",
    "params": {{}}
}}

Example 12:
Input: How high are you?
Output:

{{
    "type": "query",
    "command": "get_height",
    "params": {{}}
}}


If a command cannot be clearly mapped to one of the provided API commands, output 'UNKNOWN_COMMAND'.
                

Strictly adhere to the following rules when the user's request can be satisfied only with what you know from memory:

1. Only respond in the format:
{{
    "type": "memory_question",
    "response": <INSERT YOUR RESPONSE HERE>
}}

2. Do your best to answer their question based on provided memory or general knowledge.

3. If you do not know how to answer their question, simply respond 
that you do not know or you cannot answer their question depending on what is more appropriate.

4. Never respond talking about the memory as a separate object. You are the drone, and the memory contain what you remember.

5. When discussing your memory or past events, say "I remember" not my memory saw. The memory passed in is your memory and you should refer to it as such.

Examples:

Input: What was the license plate number of the blue Toyota?
Output:
{{
    "type": "memory_question",
    "response": The blue Toyota's license plate number was EH5G5F.
}}

Input: What is 2+2?
Output:
{{
    "type": "memory_question",
    "response": Two plus two is four.
}}

Input: What color shirt was the blonde man wearing?
Output:
{{
    "type": "memory_question",
    "response": The blonde man was wearing a blue polo shirt.
}}
"""       
        )

        self.__payload = {
            # "userId": coreID + "@motorolasolutions.com",
            "model": self.__model,
            "prompt": self.__start_message_content,
        }

        # Make the POST request
        response = requests.post(self.__url, headers=self.__headers, json=self.__payload)
        data = response.json()
        # Check the response
        if response.status_code != 200:
            print("Error:", response.status_code, response.text)
        self.__session_id = data.get("sessionId")

    # Convert user input to API command using GPT 
    def get_drone_api_command(self, user_sentence: str, memory: str) -> str:

        payload = {
            # "userId": coreID + "@motorolasolutions.com",
            "model": self.__model,
            "prompt": f"""
------------------------BEGIN MEMORY--------------------
{memory}
------------------------END MEMORY--------------------

------------------------BEGIN USER REQUEST--------------------
{user_sentence}
------------------------END USER REQUEST--------------------
""",
            "session_id": self.__session_id,
            "system": self.__start_message_content
        }

        # Make the POST request
        response = requests.post(self.__url, headers=self.__headers, json=payload)

        # Check the response
        if response.status_code != 200:
            print("Error:", response.status_code, response.text)

        return response.json()['msg']

    def send_file(self, image):
        ENDPOINT_FILE = f"/api/v2/upload/{sessionID}"
        url_for_image = f"{HOST_FILE}{ENDPOINT_FILE}"
        file_field_name = "file"
        mime_type,_ = mimetypes.guess_type(image)
        headers = {
            "x-msi-genai-api-key": api_key,
        }
        try:
            with open(image, "rb") as f:
                files = {file_field_name: (os.path.basename(image),f,mime_type)}
                
                # print(f"Attempting to upload file to: {url_for_image}")
                # print(f"File to upload: {image} (as field '{file_field_name}')\n")

                response = requests.post(url_for_image,headers=headers,files=files)
                response_image_dict = response.json()
                # print(response_image_dict)
            response.raise_for_status()
            # print("\nFile upload successful!")
            # print(f"Status Code: {response.status_code}\n")
        except FileNotFoundError:
            print(f"Error: The file '{image}' was not found.")
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}")
            print(f"Response content: {response.text}")
        except requests.exceptions.ConnectionError as conn_err:
            print(f"Connection error occurred: {conn_err}")
        except requests.exceptions.Timeout as timeout_err:
            print(f"Timeout error occurred: {timeout_err}")
        except requests.exceptions.RequestException as req_err:
            print(f"An unexpected error occurred: {req_err}")
        except json.JSONDecodeError as json_err:
            print(f"Failed to decode JSON response: {json_err}")
            if 'response' in locals() and response.text:
                print(f"Raw response text: {response.text}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")


# Input user command
if __name__ == "__main__":
    # user_task = input("Enter the drone task sentence: ")
    ttc = TextToCommand()
    user_task = "move forward 10 feet"

    # Get the API command
    generated_command = ttc.get_drone_api_command(user_task)

    # Output the result
    print(generated_command)