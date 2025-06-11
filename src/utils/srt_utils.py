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
    def merge_srt_files(srt_contents):
        """Merge multiple SRT contents into one, adjusting timestamps"""
        merged_lines = []
        current_index = 1
        
        for i, content in enumerate(srt_contents):
            lines = content.strip().split('\n')
            time_offset = i * 1800  # 30 minutes in seconds
            
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
        
        return '\n'.join(merged_lines) 