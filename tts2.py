import requests
import sounddevice as sd
import soundfile as sf
import io
import os
from dotenv import load_dotenv


load_dotenv()
api_key = os.environ.get("CARTESIA_API_KEY", "YOUR_API_KEY")
def play_text_to_speech(transcript: str, radio, model_id: str = "sonic-2", voice_id: str = "f9836c6e-a0bd-460e-9d3c-f7299fa60f94", language: str = "en"):
    """
    Converts text to speech using the Cartesia API and plays the audio.

    Args:
        api_key (str): Your Cartesia API key.
        transcript (str): The text to be converted to speech.
        model_id (str, optional): The model to use for TTS. Defaults to "sonic-2".
        voice_id (str, optional): The voice ID to use. Defaults to a sample voice.
        language (str, optional): The language of the transcript. Defaults to "en".
    """
    url = "https://api.cartesia.ai/tts/bytes"

    headers = {
        "Cartesia-Version": "2024-06-10",
        "X-API-Key": api_key,
        "Content-Type": "application/json"
    }

    data = {
        "model_id": model_id,
        "transcript": transcript,
        "voice": {
            "mode": "id",
            "id": voice_id
        },
        "output_format": {
            "container": "wav",
            "encoding": "pcm_f32le",
            "sample_rate": 44100
        },
        "language": language
    }

    try:
        # Make the POST request to the API
        response = requests.post(url, headers=headers, json=data, stream=True)
        response.raise_for_status()  # Raise an exception for bad status codes

        # Check if the response contains audio data
        if 'audio/wav' in response.headers.get('Content-Type', ''):
            # Read the audio data from the response
            audio_data, samplerate = sf.read(io.BytesIO(response.content))

            # Play the audio
            print("Playing audio...")
            radio.transmit()
            sd.play(audio_data, samplerate)
            sd.wait()  # Wait for the audio to finish playing
            radio.receive()
            print("Audio finished.")
        else:
            print("Error: The response did not contain audio data.")
            print("Response content:", response.text)


    except requests.exceptions.RequestException as e:
        print(f"An error occurred with the API request: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == '__main__':
    # --- IMPORTANT ---
    # To run this, you need to install the required libraries:
    # pip install requests sounddevice soundfile

    # Replace "YOUR_API_KEY" with your actual Cartesia API key.
    # You can get a key from the Cartesia website.
    text_to_speak = "Hello, this is a test of the text to speech API."
    play_text_to_speech(text_to_speak)
