import os
import re
from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import tempfile


def parse_srt(srt_file_path):
    """Parse SRT file and return list of subtitle entries.
    Returns list of tuples: (start_time, end_time, text)
    Times are in seconds (float).
    """
    with open(srt_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # SRT format: number, timestamp, text, blank line
    pattern = r'(\d+)\s*\n(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*\n(.*?)(?=\n\d+\s*\n|\n*$)'
    matches = re.findall(pattern, content, re.DOTALL)
    
    subtitles = []
    for match in matches:
        # Extract times
        h1, m1, s1, ms1 = map(int, match[1:5])
        h2, m2, s2, ms2 = map(int, match[5:9])
        start = h1 * 3600 + m1 * 60 + s1 + ms1 / 1000.0
        end = h2 * 3600 + m2 * 60 + s2 + ms2 / 1000.0
        
        # Extract and clean text
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
    
    # Calculate text size and position (centered, bottom)
    # Split text into lines if needed
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
    box_y = height - box_height - 20  # 20px from bottom
    
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
    # Check if files exist
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
    
    # Create text clips for each subtitle
    text_clips = []
    temp_files = []
    
    for i, (start, end, text) in enumerate(subtitles):
        # Create text image
        text_img = create_text_image(text, video_w, video_h, fontsize, 
                                     fontcolor, bgcolor, bg_opacity)
        
        # Save to temporary file
        temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        temp_files.append(temp_file.name)
        text_img.save(temp_file.name, 'PNG')
        temp_file.close()
        
        # Create ImageClip from the text image
        txt_clip = (ImageClip(temp_file.name)
                   .set_duration(end - start)
                   .set_start(start)
                   .set_position(('center', 'bottom')))
        
        text_clips.append(txt_clip)
    
    print(f"Compositing video with {len(text_clips)} subtitle overlays...")
    
    # Composite video with subtitles
    final_video = CompositeVideoClip([video] + text_clips)
    
    # Write output
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


# Example usage:
if __name__ == "__main__":
    burn_subtitles_into_video(
        input_video_path='videos/test.mp4',
        srt_file_path='transcription.srt',
        output_video_path='videos/test_captioned.mp4',
        fontsize=24,
        fontcolor='white',
        bgcolor='black',
        bg_opacity=180
    )
