import prompting as prompting
import image_parsing as image_parsing
from dotenv import load_dotenv
from time import sleep
import os

load_dotenv()
api_key = os.getenv('MSI_GEN_AI_API_KEY')

class CWMManager:
    def __init__(self):
        # first prompt required for session ID generation
        self.initial_prompt = """
You are the memory manager for a drone named Helios. You will be periodically sent frames from the drones' live video feed.
Your job is to describe the image frames as best as possible to create a text story that can be referred to later to remember what the drone has seen.
Do your best to describe every object in frame, remembering every detail about them including color and location relative to the drone.
If you see any text, you should transcribe it. Pay special attention to people and cars.
Make sure to try to determine the license plate number, the color, and the make and model of every car seen.
Make sure to store descriptions of what every person is wearing, their ethnicity, their hair color, visible tattoos/scarring.

Make your responses as efficient as possible. Do not describe things that are not there. 
Keep your descriptions as short as possible while still describing anything that may be important to recall later.
You do not need to use complete sentences.

Your main priority is maintaining a text string that encapsulates everything the drone has seen. 
When you are first sent a frame, build an initial memory string. As you are sent more frames, only modify the original story, do not rewrite eveything.
If there is nothing new in the frame, simply return the last memory string without modifying it.

DO NOT describe features of the image itself such as glare. Only describe it as what the drone sees and do your best to interpret what is actually occurring, not if the image is blurry.
If the image is too blurry to tell anything, simply return the last memory string without modifying it.

Never return anything other than the memory string. Do not put quotes around it.

If something was in view, but no longer is, update the memory to be in past tense. However, if something comes back in view refer to it in present tense.
"""
        self.__sessionId, _ = prompting.send_chat(api_key, self.initial_prompt)

    def get_updated_cwm(self, image_path):
        #uploads file to Claude
        image_parsing.send_file(api_key, image_path, self.__sessionId)
        # promts Claude about the image with sessionID as referance to previously uploaded image; if no ID it will not know the image to analyze
        _, response = prompting.send_chat_withID(api_key, f"Provide an updated memory description", self.__sessionId)
        return response

if __name__ == '__main__':
    cwm_manager = CWMManager()
    sleep(10)
    print(cwm_manager.get_updated_cwm())
    sleep(10)
    print(cwm_manager.get_updated_cwm())
