import pyttsx3

class SpeechOutput:
    def __init__(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 150)  # Speed of speech (words per minute)
        self.engine.setProperty('volume', 1.0)  # Max volume

    def announce(self, text):
        """
        Announces the given text using Text-to-Speech (TTS).
        """
        self.engine.say(text)
        self.engine.runAndWait()
