import subprocess
import os

def burn_subtitles_into_video(input_video_path, srt_file_path, output_video_path):
    """
    Burns subtitles from an SRT file into a video file using ffmpeg.

    Parameters:
    input_video_path (str): Path to the input video file.
    srt_file_path (str): Path to the SRT subtitle file.
    output_video_path (str): Path to save the output video file with burned-in subtitles.
    """
    try:
        command = [
            'ffmpeg',
            '-i', input_video_path,
            '-vf', f"subtitles={srt_file_path}",
            '-c:a', 'copy',
            output_video_path
        ]
        subprocess.run(command, check=True)
        print(f"Subtitled video saved to {output_video_path}")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred while burning subtitles: {e}")
    except FileNotFoundError:
        print("ffmpeg not found. Please ensure ffmpeg is installed.")


# Example usage:
if __name__ == "__main__":
    # Example 1: Files in current directory
    burn_subtitles_into_video(
        input_video_path='my_video.mp4',
        srt_file_path='subtitles.srt',
        output_video_path='video_with_subtitles.mp4'
    )
    
    # # Example 2: Files in your home directory
    # burn_subtitles_into_video(
    #     input_video_path=os.path.expanduser('~/Videos/input.mp4'),
    #     srt_file_path=os.path.expanduser('~/Videos/subtitles.srt'),
    #     output_video_path=os.path.expanduser('~/Videos/output.mp4')
    # )
    
    # # Example 3: Full paths
    # burn_subtitles_into_video(
    #     input_video_path='/Users/yourname/Desktop/video.mov',
    #     srt_file_path='/Users/yourname/Desktop/subtitles.srt',
    #     output_video_path='/Users/yourname/Desktop/final_video.mp4'
    # )