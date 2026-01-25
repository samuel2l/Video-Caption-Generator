import whisper
import srt
from datetime import timedelta

def transcribe_audio_to_srt(audio_path, model_size="base", segment_duration=30):
    """
    Transcribes an audio file using the Whisper model and converts the transcription to SRT format.

    Parameters:
    audio_path (str): Path to the input audio file.
    model_size (str): Size of the Whisper model to use (e.g., "tiny", "base", "small", "medium", "large").
    segment_duration (int): Duration of each segment in seconds for SRT subtitles.

    Returns:
    str: The transcription in SRT format.
    """
    try:
        model = whisper.load_model(model_size)
        result = model.transcribe(audio_path)

        segments = []
        start_time = 0.0

        for i, segment in enumerate(result["segments"]):
            end_time = segment["end"]
            content = segment["text"].strip()

            while start_time < end_time:
                seg_end_time = min(start_time + segment_duration, end_time)
                seg_content = content

                segments.append(srt.Subtitle(index=i+1,
                                             start=timedelta(seconds=start_time),
                                             end=timedelta(seconds=seg_end_time),
                                             content=seg_content))
                start_time = seg_end_time

        srt_output = srt.compose(segments)
        return srt_output

    except Exception as e:
        print(f"An error occurred during transcription to SRT: {e}")
        return ""