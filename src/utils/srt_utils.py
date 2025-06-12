import os
import re
import tiktoken
from typing import List

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
    def get_tokenizer(model: str = "gpt-4"):
        """Get the appropriate tokenizer for the specified model"""
        try:
            return tiktoken.encoding_for_model(model)
        except KeyError:
            # Fallback to cl100k_base encoding if model not found
            return tiktoken.get_encoding("cl100k_base")

    @staticmethod
    def split_to_token_chunks(text: str, max_tokens: int = 5000, model: str = "gpt-4") -> List[str]:
        """
        Split text into chunks based purely on token count.
        
        Args:
            text: Input text to split
            max_tokens: Maximum tokens per chunk (default: 5000)
            model: Model name for tokenizer (default: "gpt-4")
            
        Returns:
            List of text chunks, each containing no more than max_tokens
        """
        tokenizer = SRTUtils.get_tokenizer(model)
        tokens = tokenizer.encode(text)
        chunks = []
        
        for i in range(0, len(tokens), max_tokens):
            chunk_tokens = tokens[i:i + max_tokens]
            chunk_text = tokenizer.decode(chunk_tokens)
            chunks.append(chunk_text)
            
        return chunks

    @staticmethod
    def smart_chunk_by_paragraphs(text: str, max_tokens: int = 5000, model: str = "gpt-4") -> List[str]:
        """
        Split text into chunks by paragraphs while respecting token limits.
        
        Args:
            text: Input text to split
            max_tokens: Maximum tokens per chunk (default: 5000)
            model: Model name for tokenizer (default: "gpt-4")
            
        Returns:
            List of text chunks, each containing no more than max_tokens
        """
        tokenizer = SRTUtils.get_tokenizer(model)
        
        # Split text into paragraphs (handling different line ending styles)
        paragraphs = re.split(r'\n\s*\n', text)
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
                
            paragraph_tokens = len(tokenizer.encode(paragraph))
            
            # If paragraph itself exceeds max_tokens, split it using naive chunking
            if paragraph_tokens > max_tokens:
                # Add any accumulated content as a chunk
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                    current_chunk = []
                    current_tokens = 0
                
                # Split the large paragraph
                sub_chunks = SRTUtils.split_to_token_chunks(paragraph, max_tokens, model)
                chunks.extend(sub_chunks)
                continue
            
            # If adding this paragraph would exceed the limit, start a new chunk
            if current_tokens + paragraph_tokens > max_tokens and current_chunk:
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = []
                current_tokens = 0
            
            current_chunk.append(paragraph)
            current_tokens += paragraph_tokens
        
        # Add any remaining content as the final chunk
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        return chunks

    @staticmethod
    def split_into_chunks(srt_content, max_tokens=1000):
        """
        Split SRT content into chunks of approximately max_tokens based on word boundaries.
        This is a legacy method that uses word-based counting. For token-based splitting,
        use split_to_token_chunks() or smart_chunk_by_paragraphs() instead.
        """
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