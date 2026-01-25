from moviepy.editor import VideoFileClip
import os
def extract_audio_from_video(video_path, output_audio_path):
    """
    Extracts audio from a video file and saves it as an audio file.

    Parameters:
    video_path (str): Path to the input video file.
    output_audio_path (str): Path to save the extracted audio file.
    """
    # Load the video file
    video_clip = VideoFileClip(video_path)
    
    # Extract the audio
    audio_clip = video_clip.audio
    
    # Write the audio to a file
    audio_clip.write_audiofile(output_audio_path)
    
    # Close the clips to release resources
    audio_clip.close()
    video_clip.close()

if __name__ == "__main__":
    # Example usage
    video_file = "test.mp4"
    audio_file = "extracted_audio.mp3"
    
    extract_audio_from_video(video_file, audio_file)
    print(f"Audio extracted and saved to {audio_file}")