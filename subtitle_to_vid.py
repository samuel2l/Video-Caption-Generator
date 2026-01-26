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


def get_text_size(draw, text, font):
    """Get text size, compatible with different PIL versions."""
    try:
        # Try newer getbbox method
        bbox = font.getbbox(text)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]
    except AttributeError:
        # Fallback to older textsize method
        try:
            return draw.textsize(text, font=font)
        except:
            # Last resort: estimate
            return len(text) * 10, 20


def wrap_text(draw, text, font, max_width):
    """Wrap text to fit within max_width pixels."""
    words = text.split(' ')
    lines = []
    current_line = []
    
    for word in words:
        # Test if adding this word would exceed max_width
        test_line = ' '.join(current_line + [word])
        test_width, _ = get_text_size(draw, test_line, font)
        
        if test_width <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]
    
    if current_line:
        lines.append(' '.join(current_line))
    
    return lines if lines else [text]


def create_text_image(text, video_width, video_height, fontsize=12, fontcolor='white', 
                     bgcolor='black', bg_opacity=0):
    """Create a PIL image with just the subtitle box (not full video size).
    Returns (image, position_x, position_y) for positioning on video.
    """
    # Create a temporary image to calculate text dimensions
    temp_img = Image.new('RGBA', (100, 100), (0, 0, 0, 0))
    draw = ImageDraw.Draw(temp_img)
    
    # Try to use a system font, fallback to default if not available
    try:
        font_paths = [
            '/System/Library/Fonts/Supplemental/Arial.ttf',
            '/Library/Fonts/Arial.ttf',
            '/System/Library/Fonts/Helvetica.ttc',
        ]
        font = None
        font_loaded = None
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    font = ImageFont.truetype(font_path, fontsize)
                    font_loaded = font_path
                    break
                except Exception as e:
                    continue
        if font is None:
            font = ImageFont.load_default()
            font_loaded = "default"
    except:
        font = ImageFont.load_default()
        font_loaded = "default"
    
    # Limit subtitle box to 75% of video width
    max_box_width = int(video_width * 0.75)
    padding = 10
    
    # Wrap text to fit within max width
    paragraphs = text.split('\n')
    wrapped_lines = []
    
    for para in paragraphs:
        if para.strip():
            wrapped = wrap_text(draw, para.strip(), font, max_box_width - padding * 2)
            wrapped_lines.extend(wrapped)
        else:
            wrapped_lines.append('')
    
    # Calculate dimensions for all wrapped lines
    line_heights = []
    line_widths = []
    line_spacing = int(fontsize * 0.2)
    
    for line in wrapped_lines:
        if line:
            line_w, line_h = get_text_size(draw, line, font)
            line_widths.append(line_w)
            line_heights.append(line_h)
        else:
            line_widths.append(0)
            line_heights.append(int(fontsize * 0.3))
    
    # Calculate box dimensions
    max_line_width = max(line_widths) if line_widths else 0
    total_text_height = sum(line_heights) + (len(wrapped_lines) - 1) * line_spacing
    
    box_width = min(int(max_line_width + padding * 2), max_box_width)
    box_height = int(total_text_height + padding * 2)
    
    # Now create the actual subtitle image (just the box size, not full video)
    img = Image.new('RGBA', (box_width, box_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Convert color names to RGB
    if bgcolor == 'black':
        bg_rgb = (0, 0, 0)
    elif bgcolor == 'white':
        bg_rgb = (255, 255, 255)
    else:
        bg_rgb = (0, 0, 0)
    
    # Draw background box only if opacity > 0
    if bg_opacity > 0:
        draw.rectangle([0, 0, box_width, box_height],
                       fill=(bg_rgb[0], bg_rgb[1], bg_rgb[2], bg_opacity))
    # Debug: print if background should be transparent
    # (commented out to avoid spam, uncomment if needed)
    # if bg_opacity == 0:
    #     print(f"  DEBUG: Background opacity is 0, should be transparent")
    
    # Draw text
    if fontcolor == 'white':
        text_rgb = (255, 255, 255)
    elif fontcolor == 'black':
        text_rgb = (0, 0, 0)
    else:
        text_rgb = (255, 255, 255)
    
    y_offset = padding
    for i, line in enumerate(wrapped_lines):
        if line:
            text_x = (box_width - line_widths[i]) // 2
            
            # Draw subtle black outline for better visibility when no background
            # Only draw outline if bg_opacity is 0 (transparent background)
            if bg_opacity == 0 and fontcolor == 'white':
                outline_width = 1  # Very thin outline
                # Draw outline in 4 directions only (top, bottom, left, right) for subtlety
                outline_positions = [(-outline_width, 0), (outline_width, 0), 
                                    (0, -outline_width), (0, outline_width)]
                for adj, adj2 in outline_positions:
                    draw.text((text_x + adj, y_offset + adj2), line, 
                             fill=(0, 0, 0, 180), font=font)  # Semi-transparent black outline
            
            # Draw main text
            draw.text((text_x, y_offset), line, fill=text_rgb, font=font)
        y_offset += line_heights[i] + line_spacing
    
    # Calculate position: centered horizontally, at bottom with margin
    pos_x = (video_width - box_width) // 2
    bottom_margin = int(video_height * 0.05)  # 5% margin from bottom
    pos_y = video_height - box_height - bottom_margin
    
    return img, pos_x, pos_y


def burn_subtitles_into_video(input_video_path, srt_file_path, output_video_path,
                               fontsize=12, fontcolor='white', 
                               bgcolor='black', bg_opacity=0):
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
    
    # Use the font size as specified - no auto-scaling
    print(f"Using font size: {fontsize}")
    print(f"Video resolution: {video_w}x{video_h}")
    print(f"Background opacity: {bg_opacity} (0 = transparent, 255 = opaque)")
    # Suggest appropriate font size based on video height
    suggested_fontsize = max(12, int(video_h * 0.02))  # About 2% of video height
    if fontsize > suggested_fontsize + 5:
        print(f"  Note: Font size {fontsize} may be large for this video. Suggested: {suggested_fontsize}")
    
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
        
        text_img, pos_x, pos_y = create_text_image(text, video_w, video_h, fontsize, 
                                                    fontcolor, bgcolor, bg_opacity)
        
        temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        temp_files.append(temp_file.name)
        # Save PNG with alpha channel explicitly preserved
        text_img.save(temp_file.name, 'PNG', optimize=False)
        temp_file.close()
        
        # Debug first subtitle
        if i == 0:
            print(f"  First subtitle - bg_opacity: {bg_opacity}, image mode: {text_img.mode}")
        
        # Create ImageClip and position at the calculated bottom position
        txt_clip = ImageClip(temp_file.name)
        
        # Debug: print size of first clip
        if i == 0:
            print(f"  Video dimensions: {video_w}x{video_h}")
            print(f"  Subtitle box size: {txt_clip.size}")
            print(f"  Subtitle position: ({pos_x}, {pos_y})")
        
        txt_clip = txt_clip.set_duration(end - start).set_start(start)
        
        # Position the subtitle box at the bottom of the screen
        txt_clip = txt_clip.set_position((pos_x, pos_y))
        
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
                                   model_size="base", fontsize=12, fontcolor='white',
                                   bgcolor='black', bg_opacity=0, 
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
    #     fontsize=16,
    #     fontcolor='white',
    #     bgcolor='black',
    #     bg_opacity=0  # Transparent background
    # )
    
    # Option 2: Automatically transcribe and translate video to English subtitles
    # For 40-minute videos:
    # - model_size="base": ~30-45 min processing, good balance
    # - model_size="small": ~20-30 min processing, faster but slightly less accurate
    # - model_size="medium": ~45-60 min processing, more accurate but slower
    add_english_subtitles_to_video(
        input_video_path='videos/test.mp4',
        output_video_path='videos/test_3.mp4',
        model_size="base",  # For 40-min videos, "base" or "small" recommended
        fontsize=12,  # Smaller font size - try 10-14 for smaller text
        fontcolor='white',
        bgcolor='black',
        bg_opacity=0  # Transparent background
    )
