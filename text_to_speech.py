from gtts import gTTS
from playsound import playsound

def text_to_speech(text):
    language = 'en'  # Example: English

    # Create a gTTS object
    tts = gTTS(text=text, lang=language, slow=False)

    # Save the audio to a file
    audio_file = "tts.wav"
    tts.save(audio_file)
    playsound(audio_file)

if __name__ == '__main__':
    text_to_speech("hello")

# import required module
# import required module
import simpleaudio as sa

# define an object to play
wave_object = sa.WaveObject.from_wave_file('tts.wav')
print('playing sound using simpleaudio')

# define an object to control the play
play_object = wave_object.play()
play_object.wait_done()