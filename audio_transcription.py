import whisper

def transcribe_audio(audio_path, model_size="base"):
    """
    Transcribes an audio file using the Whisper model.

    Parameters:
    audio_path (str): Path to the input audio file.
    model_size (str): Size of the Whisper model to use (e.g., "tiny", "base", "small", "medium", "large").

    Returns:
    str: The transcribed text.
    """
    try:
        model = whisper.load_model(model_size)
        result = model.transcribe(audio_path)
        return result["text"]
    except Exception as e:
        print(f"An error occurred during transcription: {e}")
        return ""

# if __name__ == "__main__":
#     audio_file = "audios/extracted_audio.mp3"
#     print(f"Transcribing audio file: {audio_file}")
#     transcription = transcribe_audio(audio_file, model_size="base")
#     print("Transcription:")
#     print(transcription)    