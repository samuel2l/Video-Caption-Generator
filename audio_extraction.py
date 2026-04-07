try:
    from moviepy.editor import VideoFileClip  # moviepy v1
except ModuleNotFoundError:
    from moviepy import VideoFileClip  # moviepy v2
def extract_audio_from_video(video_path, output_audio_path):
    """
    Extracts audio from a video file and saves it as an audio file.

    Parameters:
    video_path (str): Path to the input video file.
    output_audio_path (str): Path to save the extracted audio file.
    """
    try:

        video_clip = VideoFileClip(video_path)        
        audio_clip = video_clip.audio        
        try:
            audio_clip.write_audiofile(output_audio_path, verbose=False, logger=None)
        except TypeError:
            try:
                audio_clip.write_audiofile(output_audio_path, logger=None)
            except TypeError:
                audio_clip.write_audiofile(output_audio_path)
        audio_clip.close()
        video_clip.close()

    except Exception as e:

        print(f"An error occurred: {e}")

# if __name__ == "__main__":

#     video_file = "videos/test.mp4"
#     audio_file = "audios/extracted_audio.mp3"    
#     extract_audio_from_video(video_file, audio_file)
#     print(f"Audio extracted and saved to {audio_file}")

