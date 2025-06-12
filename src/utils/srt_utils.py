import os
import re

class SRTUtils:
    @staticmethod
    def srt_timestamp_to_seconds(timestamp):
        """Convert SRT timestamp (HH:MM:SS,mmm) to seconds"""
        hours, minutes, seconds = timestamp.replace(',', '.').split(':')
        return float(hours) * 3600 + float(minutes) * 60 + float(seconds)

    @staticmethod
    def seconds_to_srt_timestamp(seconds):
        """Convert seconds to SRT timestamp format (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = seconds % 60
        milliseconds = int((seconds - int(seconds)) * 1000)
        return f"{hours:02d}:{minutes:02d}:{int(seconds):02d},{milliseconds:03d}"
    
    @staticmethod
    def split_into_chunks(srt_content, max_tokens=100000):
        """Split SRT content into chunks of approximately max_tokens based on word boundaries"""
        # First split into subtitle entries to preserve timing information
        entries = re.split(r'\n\n+', srt_content.strip())
        
        chunks = []
        current_chunk = []
        current_token_count = 0
        
        for entry in entries:
            # Split entry into lines to separate timing from text
            lines = entry.strip().split('\n')
            if len(lines) < 3:  # Skip malformed entries
                continue
                
            # Get the text content (everything after the timing line)
            text_content = ' '.join(lines[2:])
            
            # Count tokens (rough estimate: 1 token ≈ 1 word)
            # Split by whitespace and count words
            words = text_content.split()
            entry_tokens = len(words)
            
            # If a single entry is larger than max_tokens, we need to split it
            if entry_tokens > max_tokens:
                # If we have accumulated entries, add them as a chunk
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                    current_chunk = []
                    current_token_count = 0
                
                # Split the large entry into smaller pieces
                words_chunks = []
                current_words = []
                current_chunk_tokens = 0
                
                for word in words:
                    if current_chunk_tokens + 1 > max_tokens:
                        words_chunks.append(' '.join(current_words))
                        current_words = []
                        current_chunk_tokens = 0
                    current_words.append(word)
                    current_chunk_tokens += 1
                
                if current_words:
                    words_chunks.append(' '.join(current_words))
                
                # Create new entries for each word chunk while preserving timing
                for i, word_chunk in enumerate(words_chunks):
                    new_entry = f"{lines[0]}\n{lines[1]}\n{word_chunk}"
                    chunks.append(new_entry)
            else:
                # If adding this entry would exceed max_tokens, start a new chunk
                if current_token_count + entry_tokens > max_tokens and current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                    current_chunk = []
                    current_token_count = 0
                
                current_chunk.append(entry)
                current_token_count += entry_tokens
        
        # Add any remaining entries as the final chunk
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        return chunks

    @staticmethod
    def merge_srt_files(srt_contents, chunk_duration_minutes=30, destination_path=None):
        """Merge multiple SRT contents into one, adjusting timestamps"""
        merged_lines = []
        current_index = 1
        
        for i, content in enumerate(srt_contents):
            lines = content.strip().split('\n')
            time_offset = i * (chunk_duration_minutes * 60)  # Convert minutes to seconds
            
            for line in lines:
                if line.strip().isdigit():  # Subtitle index
                    merged_lines.append(str(current_index))
                    current_index += 1
                elif '-->' in line:  # Timestamp line
                    start, end = line.split(' --> ')
                    start_seconds = SRTUtils.srt_timestamp_to_seconds(start) + time_offset
                    end_seconds = SRTUtils.srt_timestamp_to_seconds(end) + time_offset
                    
                    start_adjusted = SRTUtils.seconds_to_srt_timestamp(start_seconds)
                    end_adjusted = SRTUtils.seconds_to_srt_timestamp(end_seconds)
                    
                    merged_lines.append(f"{start_adjusted} --> {end_adjusted}")
                else:  # Text content
                    merged_lines.append(line)
            
            # Add blank line between chunks
            if i < len(srt_contents) - 1:
                merged_lines.append('')
        
        merged_content = '\n'.join(merged_lines)
        
        # Save to file if destination_path is provided
        if destination_path:
            os.makedirs(os.path.dirname(destination_path), exist_ok=True)
            with open(destination_path, 'w', encoding='utf-8') as f:
                f.write(merged_content)
        
        return merged_content 