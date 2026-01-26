import os
import re
from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import tempfile
import whisper
import srt
from datetime import timedelta


def parse_srt(srt_file_path):
    """Parse SRT file and return list of subtitle entries.
    Returns list of tuples: (start_time, end_time, text)
    Times are in seconds (float).
    """
    with open(srt_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    pattern = r'(\d+)\s*\n(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*\n(.*?)(?=\n\d+\s*\n|\n*$)'
    matches = re.findall(pattern, content, re.DOTALL)
    
    subtitles = []
    for match in matches:
        # Extract times
        h1, m1, s1, ms1 = map(int, match[1:5])
        h2, m2, s2, ms2 = map(int, match[5:9])
        start = h1 * 3600 + m1 * 60 + s1 + ms1 / 1000.0
        end = h2 * 3600 + m2 * 60 + s2 + ms2 / 1000.0
        

        text = match[9].strip()
        
        subtitles.append((start, end, text))
    
    return subtitles


def create_text_image(text, width, height, fontsize=24, fontcolor='white', 
                     bgcolor='black', bg_opacity=128):
    """Create a PIL image with text on a semi-transparent background."""
    # Create image with alpha channel
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Try to use a system font, fallback to default if not available
    try:
        # Try common macOS fonts
        font_paths = [
            '/System/Library/Fonts/Helvetica.ttc',
            '/System/Library/Fonts/Arial.ttf',
            '/Library/Fonts/Arial.ttf',
        ]
        font = None
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    font = ImageFont.truetype(font_path, fontsize)
                    break
                except:
                    continue
        if font is None:
            font = ImageFont.load_default()
    except:
        font = ImageFont.load_default()
    

    lines = text.split('\n')
    line_heights = []
    line_widths = []
    
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_widths.append(bbox[2] - bbox[0])
        line_heights.append(bbox[3] - bbox[1])
    
    total_height = sum(line_heights) + (len(lines) - 1) * fontsize * 0.2
    max_width = max(line_widths) if line_widths else 0
    
    # Add padding
    padding = 10
    box_width = int(max_width + padding * 2)
    box_height = int(total_height + padding * 2)
    
    # Draw background box
    box_x = (width - box_width) // 2
    box_y = height - box_height - 20 
    
    # Convert color names to RGB
    if bgcolor == 'black':
        bg_rgb = (0, 0, 0)
    elif bgcolor == 'white':
        bg_rgb = (255, 255, 255)
    else:
        bg_rgb = (0, 0, 0)  # default to black
    
    draw.rectangle([box_x, box_y, box_x + box_width, box_y + box_height],
                   fill=(bg_rgb[0], bg_rgb[1], bg_rgb[2], bg_opacity))
    
    # Draw text
    if fontcolor == 'white':
        text_rgb = (255, 255, 255)
    elif fontcolor == 'black':
        text_rgb = (0, 0, 0)
    else:
        text_rgb = (255, 255, 255)  # default to white
    
    y_offset = box_y + padding
    for i, line in enumerate(lines):
        text_x = box_x + (box_width - line_widths[i]) // 2
        draw.text((text_x, y_offset), line, fill=text_rgb, font=font)
        y_offset += line_heights[i] + fontsize * 0.2
    
    return img


def burn_subtitles_into_video(input_video_path, srt_file_path, output_video_path,
                               fontsize=24, fontcolor='white', 
                               bgcolor='black', bg_opacity=128):
    """
    Burns subtitles from an SRT file into a video file using moviepy and PIL.

    Parameters:
    input_video_path (str): Path to the input video file.
    srt_file_path (str): Path to the SRT subtitle file.
    output_video_path (str): Path to save the output video file with burned-in subtitles.
    fontsize (int): Font size for subtitles.
    fontcolor (str): Text color ('white' or 'black').
    bgcolor (str): Background box color ('black' or 'white').
    bg_opacity (int): Background opacity (0-255, where 255 is fully opaque).
    """
    if not os.path.exists(input_video_path):
        raise FileNotFoundError(f"Video file not found: {input_video_path}")
    if not os.path.exists(srt_file_path):
        raise FileNotFoundError(f"SRT file not found: {srt_file_path}")
    
    print(f"Loading video: {input_video_path}")
    video = VideoFileClip(input_video_path)
    video_w, video_h = video.size
    
    print(f"Parsing subtitles: {srt_file_path}")
    subtitles = parse_srt(srt_file_path)
    
    if not subtitles:
        raise ValueError("No subtitles found in SRT file")
    
    print(f"Found {len(subtitles)} subtitle segments")
    print(f"Creating text overlays...")
    
    text_clips = []
    temp_files = []
    
    # Show progress for long videos
    total_segments = len(subtitles)
    show_progress = total_segments > 50
    
    for i, (start, end, text) in enumerate(subtitles):
        if show_progress and (i + 1) % 50 == 0:
            print(f"  Progress: {i + 1}/{total_segments} subtitle images created...")
        
        text_img = create_text_image(text, video_w, video_h, fontsize, 
                                     fontcolor, bgcolor, bg_opacity)
        
        temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        temp_files.append(temp_file.name)
        text_img.save(temp_file.name, 'PNG')
        temp_file.close()
        
        txt_clip = (ImageClip(temp_file.name)
                   .set_duration(end - start)
                   .set_start(start)
                   .set_position(('center', 'bottom')))
        
        text_clips.append(txt_clip)
    
    print(f"Compositing video with {len(text_clips)} subtitle overlays...")
    if video.duration > 600:  
        print(f"  Note: This is a long video ({video.duration/60:.1f} minutes).")
        print(f"  Encoding may take 10-30 minutes depending on your system...")
    
    final_video = CompositeVideoClip([video] + text_clips)
    
    print(f"Writing output to: {output_video_path}")
    final_video.write_videofile(output_video_path, 
                                 codec='libx264',
                                 audio_codec='aac',
                                 temp_audiofile='temp-audio.m4a',
                                 remove_temp=True,
                                 verbose=False,
                                 logger=None)
    
    # Clean up temporary files
    for temp_file in temp_files:
        try:
            os.unlink(temp_file)
        except:
            pass
    
    # Clean up
    video.close()
    final_video.close()
    
    print(f"Subtitled video saved to {output_video_path}")


def extract_audio_from_video(video_path, output_audio_path):
    """
    Extracts audio from a video file and saves it as an audio file.

    Parameters:
    video_path (str): Path to the input video file.
    output_audio_path (str): Path to save the extracted audio file.
    """
    try:
        print(f"Extracting audio from video: {video_path}")
        video_clip = VideoFileClip(video_path)
        audio_clip = video_clip.audio
        audio_clip.write_audiofile(output_audio_path, verbose=False, logger=None)
        audio_clip.close()
        video_clip.close()
        print(f"Audio extracted and saved to {output_audio_path}")
    except Exception as e:
        print(f"An error occurred while extracting audio: {e}")
        raise


def transcribe_and_translate_to_english(audio_path, model_size="base", output_srt_path=None):
    """
    Transcribes an audio file using Whisper, automatically detects language,
    and translates to English. Returns the SRT content and detected language.

    Parameters:
    audio_path (str): Path to the input audio file.
    model_size (str): Size of the Whisper model to use (e.g., "tiny", "base", "small", "medium", "large").
    output_srt_path (str, optional): Path to save the SRT file. If None, returns SRT content only.

    Returns:
    tuple: (srt_content, detected_language) where srt_content is the SRT string and detected_language is the language code.
    """
    try:
        print(f"Loading Whisper model: {model_size}")
        print(f"  (This may take a minute for first-time use)")
        model = whisper.load_model(model_size)
        
        try:
            from moviepy.editor import AudioFileClip
            audio_clip = AudioFileClip(audio_path)
            duration = audio_clip.duration
            audio_clip.close()
            if duration > 600:  # More than 10 minutes
                estimated_time = duration / 60 * 0.5  # Rough estimate: 0.5x realtime for base model
                print(f"  Audio duration: {duration/60:.1f} minutes")
                print(f"  Estimated transcription time: {estimated_time:.1f} minutes")
        except:
            pass
        
        print(f"Transcribing and translating audio: {audio_path}")
        print(f"  (This may take a while for long videos...)")
        result = model.transcribe(audio_path, task="translate")
        
        detected_language = result.get("language", "unknown")
        print(f"Detected language: {detected_language}")
        print(f"Translating to English...")
        

        segments = []
        for i, segment in enumerate(result["segments"]):
            start_time = timedelta(seconds=segment["start"])
            end_time = timedelta(seconds=segment["end"])
            content = segment["text"].strip()
            
            segments.append(srt.Subtitle(
                index=i + 1,
                start=start_time,
                end=end_time,
                content=content
            ))
        
        srt_content = srt.compose(segments)
        
        if output_srt_path:
            with open(output_srt_path, "w", encoding="utf-8") as srt_file:
                srt_file.write(srt_content)
            print(f"SRT file saved to: {output_srt_path}")
        
        return srt_content, detected_language
        
    except Exception as e:
        print(f"An error occurred during transcription: {e}")
        raise


def add_english_subtitles_to_video(input_video_path, output_video_path, 
                                   model_size="base", fontsize=24, fontcolor='white',
                                   bgcolor='black', bg_opacity=180, 
                                   keep_temp_files=False):
    """
    Complete pipeline: Extracts audio from video, transcribes and translates to English,
    then burns the subtitles into the video.

    Parameters:
    input_video_path (str): Path to the input video file.
    output_video_path (str): Path to save the output video with burned-in English subtitles.
    model_size (str): Size of the Whisper model to use. For long videos, consider "small" or "medium".
    fontsize (int): Font size for subtitles.
    fontcolor (str): Text color ('white' or 'black').
    bgcolor (str): Background box color ('black' or 'white').
    bg_opacity (int): Background opacity (0-255).
    keep_temp_files (bool): If True, keeps temporary audio and SRT files.
    
    Note: For 40-minute videos, expect:
    - Audio extraction: 1-2 minutes
    - Transcription: 15-30 minutes (depending on model_size)
    - Subtitle burning: 10-20 minutes
    Total: ~30-60 minutes processing time
    """
    temp_audio_path = None
    temp_srt_path = None
    
    try:

        try:
            video_clip = VideoFileClip(input_video_path)
            duration = video_clip.duration
            video_clip.close()
            
            if duration > 1200: 
                print(f"\n⚠️  Long video detected: {duration/60:.1f} minutes")
                print(f"   This will take significant time to process.")
                print(f"   Estimated total time: {duration/60 * 1.5:.0f}-{duration/60 * 2.5:.0f} minutes")
                print(f"   Consider using model_size='small' for faster processing.\n")
        except:
            pass
        
        temp_dir = tempfile.mkdtemp()
        temp_audio_path = os.path.join(temp_dir, "extracted_audio.mp3")
        temp_srt_path = os.path.join(temp_dir, "translation.srt")
        
        print("\n" + "="*60)
        print("STEP 1: Extracting audio from video")
        print("="*60)
        extract_audio_from_video(input_video_path, temp_audio_path)
        
        # Step 2: Transcribe and translate to English
        print("\n" + "="*60)
        print("STEP 2: Transcribing and translating to English")
        print("="*60)
        srt_content, detected_language = transcribe_and_translate_to_english(
            temp_audio_path, 
            model_size=model_size,
            output_srt_path=temp_srt_path
        )
        
        print(f"\nOriginal language: {detected_language}")
        print(f"Translation: English")
        num_segments = len(srt_content.split('\n\n')) - 1
        print(f"Number of subtitle segments: {num_segments}")
        
        print("\n" + "="*60)
        print("STEP 3: Burning subtitles into video")
        print("="*60)
        burn_subtitles_into_video(
            input_video_path=input_video_path,
            srt_file_path=temp_srt_path,
            output_video_path=output_video_path,
            fontsize=fontsize,
            fontcolor=fontcolor,
            bgcolor=bgcolor,
            bg_opacity=bg_opacity
        )
        
        print(f"\n{'='*60}")
        print(f"✓ Successfully created video with English subtitles")
        print(f"  Output: {output_video_path}")
        print(f"{'='*60}")
        
    except Exception as e:
        print(f"\n✗ Error in pipeline: {e}")
        raise
        
    finally:
        # Clean up temporary files
        if not keep_temp_files:
            for temp_file in [temp_audio_path, temp_srt_path]:
                if temp_file and os.path.exists(temp_file):
                    try:
                        os.unlink(temp_file)
                    except:
                        pass
            if temp_dir and os.path.exists(temp_dir):
                try:
                    os.rmdir(temp_dir)
                except:
                    pass


# Example usage:
if __name__ == "__main__":
    # Option 1: Burn existing SRT file into video
    # burn_subtitles_into_video(
    #     input_video_path='videos/test.mp4',
    #     srt_file_path='transcription.srt',
    #     output_video_path='videos/test_captioned.mp4',
    #     fontsize=24,
    #     fontcolor='white',
    #     bgcolor='black',
    #     bg_opacity=180
    # )
    
    # Option 2: Automatically transcribe and translate video to English subtitles
    # For 40-minute videos:
    # - model_size="base": ~30-45 min processing, good balance
    # - model_size="small": ~20-30 min processing, faster but slightly less accurate
    # - model_size="medium": ~45-60 min processing, more accurate but slower
    add_english_subtitles_to_video(
        input_video_path='videos/test.mp4',
        output_video_path='videos/test_english_subtitles.mp4',
        model_size="base",  # For 40-min videos, "base" or "small" recommended
        fontsize=24,
        fontcolor='white',
        bgcolor='black',
        bg_opacity=180
    )
