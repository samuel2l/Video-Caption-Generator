# Caption Generator

A Python tool for automatically generating and burning subtitles into videos. Supports automatic language detection, translation to English, and subtitle burning using Whisper AI and MoviePy.

## Features

- 🎬 **Burn existing subtitles** into videos from SRT files
- 🌍 **Automatic language detection** - Works with any language (Spanish, French, German, etc.)
- 🔄 **Automatic translation** - Translates any language to English subtitles
- ⚡ **Complete pipeline** - Extract audio → Transcribe → Translate → Burn subtitles in one command
- 📝 **Customizable styling** - Adjust font size, colors, and background opacity
- ⏱️ **Progress tracking** - Shows progress for long videos
- 💾 **Memory efficient** - Handles long videos (40+ minutes) efficiently

## Requirements

- Python 3.8+
- FFmpeg (for video processing)
- Sufficient disk space (output videos are similar size to input)

## Installation

1. **Clone or download this repository**

2. **Create a virtual environment** (recommended):
```bash
python3 -m venv myvenv
source myvenv/bin/activate  # On macOS/Linux
# or
myvenv\Scripts\activate  # On Windows
```

3. **Install dependencies**:
```bash
pip install moviepy pillow whisper openai-whisper srt numpy
```

4. **Install FFmpeg**:
   - **macOS**: `brew install ffmpeg`
   - **Linux**: `sudo apt-get install ffmpeg` (or your package manager)
   - **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html)

## Usage

### Step-by-Step Workflow

Follow these steps in order to add subtitles to your video:

#### Step 1: Extract Audio from Video

Edit `audio_extraction.py` and uncomment/modify the main section:

```python
if __name__ == "__main__":
    video_file = "videos/your_video.mp4"
    audio_file = "audios/extracted_audio.mp3"    
    extract_audio_from_video(video_file, audio_file)
    print(f"Audio extracted and saved to {audio_file}")
```

Then run:
```bash
python audio_extraction.py
```

This creates `audios/extracted_audio.mp3` from your video.

#### Step 2: Transcribe Audio to SRT

Edit `audio_to_srt.py` and modify the paths in the main section:

```python
if __name__ == "__main__":
    audio_file = "audios/extracted_audio.mp3"
    print(f"Transcribing audio file to SRT: {audio_file}")
    srt_transcription = transcribe_audio_to_srt(audio_file, model_size="base", segment_duration=30)
    print("SRT Transcription: ", srt_transcription)
    with open("transcription.srt", "w", encoding="utf-8") as srt_file:
        srt_file.write(srt_transcription)                     
    print("SRT transcription saved to transcription.srt")
```

Then run:
```bash
python audio_to_srt.py
```

This creates `transcription.srt` with English subtitles (automatically translates if the video is in another language).

#### Step 3: Burn Subtitles into Video

Edit `subtitle_to_vid.py` and modify the main section:

```python
if __name__ == "__main__":
    burn_subtitles_into_video(
        input_video_path='videos/your_video.mp4',
        srt_file_path='transcription.srt',
        output_video_path='videos/your_video_captioned.mp4',
        fontsize=24,
        fontcolor='white',
        bgcolor='black',
        bg_opacity=180
    )
```

Then run:
```bash
python subtitle_to_vid.py
```

This creates your final video with burned-in subtitles!

### Quick Summary

```bash
# Step 1: Extract audio
python audio_extraction.py
# Output: audios/extracted_audio.mp3

# Step 2: Transcribe to SRT (auto-translates to English)
python audio_to_srt.py
# Output: transcription.srt

# Step 3: Burn subtitles into video
python subtitle_to_vid.py
# Output: videos/your_video_captioned.mp4
```

**Note**: Make sure to edit each file's `if __name__ == "__main__"` section with your file paths before running!

### Alternative: All-in-One Function

If you prefer a single command, you can use the `add_english_subtitles_to_video()` function in `subtitle_to_vid.py` which does all three steps automatically. See the "Advanced Usage" section below.

## Project Structure

```
caption-gen/
├── audio_extraction.py      # Step 1: Extract audio from video → MP3
├── audio_to_srt.py         # Step 2: Transcribe audio → SRT file (auto-translates to English)
├── subtitle_to_vid.py      # Step 3: Burn SRT subtitles into video
├── audio_transcription.py  # Helper: Basic transcription function
└── README.md               # This file
```

**Workflow**: Run files in order: `audio_extraction.py` → `audio_to_srt.py` → `subtitle_to_vid.py`

## How It Works

The workflow consists of three main steps:

1. **`audio_extraction.py`** - Extracts the audio track from your video file and saves it as an MP3
2. **`audio_to_srt.py`** - Uses OpenAI Whisper to:
   - Automatically detect the source language (Spanish, French, etc.)
   - Transcribe the audio
   - Translate to English (if not already English)
   - Generate a properly formatted SRT subtitle file with timing
3. **`subtitle_to_vid.py`** - Burns the subtitles into the video using PIL and MoviePy:
   - Creates text images for each subtitle segment
   - Composites them onto the video at the correct times
   - Exports the final video with burned-in subtitles

## Performance & Processing Time

### For a 40-minute video:

- **Audio extraction**: 1-2 minutes
- **Transcription** (depends on model):
  - `tiny`: ~10-15 minutes (fastest, least accurate)
  - `base`: ~30-45 minutes (recommended balance)
  - `small`: ~20-30 minutes (good balance)
  - `medium`: ~45-60 minutes (more accurate)
  - `large`: ~60-90 minutes (most accurate, slowest)
- **Subtitle burning**: ~10-20 minutes

**Total: ~30-60 minutes** depending on your system and model choice.

### Model Size Recommendations

- **Short videos (< 10 min)**: Use `base` or `small`
- **Medium videos (10-30 min)**: Use `base` or `small`
- **Long videos (30+ min)**: Use `base` or `small` for faster processing
- **Maximum accuracy needed**: Use `medium` or `large` (much slower)

## Parameters

### `burn_subtitles_into_video()`

- `input_video_path` (str): Path to input video
- `srt_file_path` (str): Path to SRT subtitle file
- `output_video_path` (str): Path for output video
- `fontsize` (int): Font size (default: 24)
- `fontcolor` (str): Text color - `'white'` or `'black'` (default: `'white'`)
- `bgcolor` (str): Background color - `'black'` or `'white'` (default: `'black'`)
- `bg_opacity` (int): Background opacity 0-255 (default: 180)

### `add_english_subtitles_to_video()`

- `input_video_path` (str): Path to input video
- `output_video_path` (str): Path for output video
- `model_size` (str): Whisper model size - `"tiny"`, `"base"`, `"small"`, `"medium"`, `"large"` (default: `"base"`)
- `fontsize` (int): Font size (default: 24)
- `fontcolor` (str): Text color (default: `'white'`)
- `bgcolor` (str): Background color (default: `'black'`)
- `bg_opacity` (int): Background opacity (default: 180)
- `keep_temp_files` (bool): Keep temporary audio/SRT files (default: `False`)

## Supported Languages

Whisper supports 99+ languages including:
- Spanish, French, German, Italian, Portuguese
- Chinese, Japanese, Korean, Arabic, Hindi
- And many more!

The tool automatically detects the language and translates to English.

## Troubleshooting

### "No such filter: 'drawtext'" or "No such filter: 'subtitles'"
Your FFmpeg installation doesn't have the required filters. This is normal - the script uses MoviePy and PIL instead, which don't require these filters.

### "MoviePy Error: ImageMagick not found"
The script uses PIL instead of ImageMagick, so this shouldn't occur. If it does, make sure Pillow is installed: `pip install pillow`

### Out of memory errors
For very long videos, try:
- Using a smaller Whisper model (`tiny` or `base`)
- Processing in smaller chunks
- Closing other applications

### Slow processing
- Use a smaller Whisper model for faster transcription
- Ensure you have sufficient CPU/RAM
- Processing time scales with video length

## Examples

### Example: Spanish Video → English Subtitles

**Step 1** - Edit and run `audio_extraction.py`:
```python
video_file = "videos/spanish_tutorial.mp4"
audio_file = "audios/extracted_audio.mp3"
```

**Step 2** - Edit and run `audio_to_srt.py`:
```python
audio_file = "audios/extracted_audio.mp3"
# Creates transcription.srt automatically
```

**Step 3** - Edit and run `subtitle_to_vid.py`:
```python
burn_subtitles_into_video(
    input_video_path='videos/spanish_tutorial.mp4',
    srt_file_path='transcription.srt',
    output_video_path='videos/spanish_tutorial_english.mp4'
)
```

### Custom Styled Subtitles

In `subtitle_to_vid.py`, customize the styling:
```python
burn_subtitles_into_video(
    input_video_path='videos/video.mp4',
    srt_file_path='transcription.srt',
    output_video_path='videos/video_styled.mp4',
    fontsize=32,           # Larger font
    fontcolor='white',    # White text
    bgcolor='black',      # Black background
    bg_opacity=200        # More opaque
)
```

### Advanced: All-in-One Function

If you want to do everything in one command, use the `add_english_subtitles_to_video()` function in `subtitle_to_vid.py`:

```python
from subtitle_to_vid import add_english_subtitles_to_video

add_english_subtitles_to_video(
    input_video_path='videos/spanish_video.mp4',
    output_video_path='videos/spanish_video_english.mp4',
    model_size="base"
)
```

## License

This project is open source and available for personal and commercial use.

## Credits

- **OpenAI Whisper** - For speech recognition and translation
- **MoviePy** - For video processing
- **PIL/Pillow** - For text rendering

## Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.
