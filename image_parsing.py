import json
import requests
import mimetypes
import os

HOST_FILE = "https://genai-service.stage.commandcentral.com/app-gateway"

def send_file(api_key, image, sessionID):
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

#prints all previous chats stored with that sessionID, if multiple
def receive_messages(api_key, sessionID):
    ENDPOINT_RESPONSE = f"/api/v2/getSessionMessages/{sessionID}&page=1&limit=10"
    url_image_response = f"{HOST_FILE}{ENDPOINT_RESPONSE}"

    headers = {
        "x-msi-genai-api-key": api_key,
    }
    try:
        response = requests.get(url_image_response,headers=headers)
        response.raise_for_status()
        response_data = response.json()
        print("\nSuccessfully fetched session messages!")
        print(f"Status Code: {response.status_code}") 
        response_dict = response.json()

    except json.JSONDecodeError as e:
        print(e)
    return response_dict['data'][1]['msg']
