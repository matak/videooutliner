#!/usr/bin/env python3

import os
import argparse
from pathlib import Path
from dotenv import load_dotenv
from src.video_outline_generator import VideoOutlineGenerator

# Load environment variables
load_dotenv()

# Configure paths
ROOT_DIR = Path(__file__).parent
IMPORT_DIR = ROOT_DIR / "import"
WEB_DIR = ROOT_DIR / "web"

def main():
    parser = argparse.ArgumentParser(description="Generate lecture outline from video")
    parser.add_argument("--file", help="Path to a specific video file to process")
    args = parser.parse_args()

    try:
        generator = VideoOutlineGenerator(
            import_dir=str(IMPORT_DIR),
            web_dir=str(WEB_DIR)
        )
        
        if args.file:
            # Process a specific file
            video_path = Path(args.file)
            if not video_path.is_absolute():
                video_path = IMPORT_DIR / video_path
            generator.process_video(str(video_path))
        else:
            # Process all files in the import directory
            generator.process_all_videos()
            
    except Exception as e:
        print(f"Error: {e}")
        exit(1)

if __name__ == "__main__":
    main() 