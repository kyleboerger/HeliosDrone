import json
import requests
url_for_prompt = "https://genai-service.stage.commandcentral.com/app-gateway/api/v2/chat"

def send_chat(api_key, message):

    headers = {
        "x-msi-genai-api-key": api_key,
        "Content-Type": "application/json",
        "x-msi-genai-client": "drone-chat"
    }


    # Sets request parameters for AI model, prompt and model are required
    payload = {
        "model": "Claude-Sonnet-3_7",  
        "prompt": f"{message}",
    }

    # makes the post request and waits for response
    try:
        # print(f"Attempting to connect to: {url_for_prompt}")
        # print(f"prompt is: {payload['prompt']}")

        response = requests.post(url_for_prompt, headers=headers, json=payload)
        response.raise_for_status()

        # If the request was successful (status code 200)
        # print("\nSuccessfully connected to the API!")
        # print(f"Status Code: {response.status_code}\n")
        
        response_data_dict = response.json()
        # print(f"Output message: {response_data_dict['msg']}")
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
    return response_data_dict['sessionId'], response_data_dict['msg']

def send_chat_withID(api_key, message, sessionId):

    headers = {
        "x-msi-genai-api-key": api_key,
        "Content-Type": "application/json",
        "x-msi-genai-client": "drone-chat"
    }


    # Sets request parameters for AI model, prompt and model are required
    payload = {
        "model": "Claude-Sonnet-3_7",  
        "prompt": f"{message}",
        "sessionId": f"{sessionId}"
    }

    # makes post request and handles errors
    try:
        # print(f"Attempting to connect to: {url_for_prompt}")
        # print(f"prompt is: {payload['prompt']}")

        response = requests.post(url_for_prompt, headers=headers, json=payload)
        response.raise_for_status()

        # If the request was successful (status code 200)
        # print("\nSuccessfully connected to the API!")
        # print(f"Status Code: {response.status_code}")
        # print("Response Body:")
        # print(json.dumps(response.json(),indent=4))

        response_data_dict = response.json()
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
    return response_data_dict['sessionId'], response_data_dict['msg']