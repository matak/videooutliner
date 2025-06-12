import json
import requests
from pathlib import Path
import os
import datetime
from src.utils.srt_utils import SRTUtils

class OutlineGenerator:
    def __init__(self, api_key):
        self.openrouter_api_key = api_key
        # Create logs directory if it doesn't exist
        self.logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs", "api")
        os.makedirs(self.logs_dir, exist_ok=True)

    def _log_api_interaction(self, interaction_type, data):
        """Log API interaction to a timestamped file"""
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        log_file = os.path.join(self.logs_dir, f'{interaction_type}_{timestamp}.json')
        
        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Failed to log {interaction_type}: {str(e)}")

    def _get_chunk_json_path(self, outline_path, chunk_index):
        """Get the cache path for a specific chunk"""
        return f"{outline_path}.chunk_{chunk_index}.json"

    def _process_chunk(self, chunk, chunk_index, outline_path):
        """Process a single chunk of SRT content"""
        json_path = self._get_chunk_json_path(outline_path, chunk_index)

        # Check for cached response first
        try:
            cached_response = self._load_json(json_path)
            print(f"Using cached response for chunk ... {json_path}")
            return cached_response
        except Exception as e:
            pass

        prompt = self._load_content(os.path.join(os.path.dirname(__file__), "prompts", "srt_chunk_prompt.txt"))
        prompt = prompt.format(chunk_index=chunk_index, chunk=chunk)

        headers = {
            "Authorization": f"Bearer {self.openrouter_api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": "openai/o3",
            "messages": [{"role": "user", "content": prompt}]
        }

        # Log the request
        self._log_api_interaction('request', {
            'timestamp': datetime.datetime.now().isoformat(),
            'headers': headers,
            'data': data,
            'prompt': prompt,
            'chunk_index': chunk_index,
            'outline_path': outline_path
        })

        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=data
            )

            # Log the response
            self._log_api_interaction('response', {
                'timestamp': datetime.datetime.now().isoformat(),
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'text': response.text,
                'encoding': response.encoding,
                'chunk_index': chunk_index,
                'outline_path': outline_path
            })

            if response.status_code != 200:
                raise Exception(f"OpenRouter API error: {response.text}")

            response_json = response.json()
            if not response_json.get("choices") or not response_json["choices"][0].get("message"):
                raise Exception("Invalid response format from API")
            
            content = response_json["choices"][0]["message"]["content"].strip()
            content_json = json.loads(content)

            # Save the response
            self._save_json(content_json, json_path)

            return content_json
        except Exception as e:
            raise Exception(f"Error processing chunk {chunk_index}: {str(e)}")

    def _combine_outlines(self, outlines):
        """Combine multiple outlines into a single coherent outline"""
        prompt = """Combine these partial outlines into a single coherent outline in JSON format.
Rules:
• Each level (main topics and any nested subsections) may contain **no more than 10 items**.
• If more than 10 items belong at one level, create additional nested levels so every level stays ≤ 10 items.
• For every node include:
  - "title": brief heading  
  - "start_time": "HH:MM:SS" of first mention
  - "subsections": [] (array holding any children; empty if none)
• Merge similar topics and maintain chronological order.

Return ONLY valid JSON with this exact overall shape:

[
    {
        "title": "Main Topic",
        "start_time": "HH:MM:SS",
        "subsections": [
            {
                "title": "Subtopic",
                "start_time": "HH:MM:SS",
                "subsections": []
            }
        ]
    }
]

Partial Outlines:
{outlines}
"""
        prompt = prompt.format(outlines=json.dumps(outlines, indent=2))

        headers = {
            "Authorization": f"Bearer {self.openrouter_api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": "openai/o3",
            "messages": [{"role": "user", "content": prompt}]
        }

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data
        )

        if response.status_code != 200:
            raise Exception(f"OpenRouter API error: {response.text}")

        try:
            response_json = response.json()
            if not response_json.get("choices") or not response_json["choices"][0].get("message"):
                raise Exception("Invalid response format from API")
            
            content = response_json["choices"][0]["message"]["content"].strip()
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse JSON response: {e}\nContent: {content}")
        except Exception as e:
            raise Exception(f"Error processing response: {str(e)}")

    def generate_outline(self, srt_content, outline_path):
        """Generate outline using OpenRouter API"""
        # Check for cached response first
        try:
            cached_response = self._load_json(outline_path)
            print(f"Using cached response from {outline_path}")
            return json.loads(cached_response["text"].strip())
        except Exception as e:
            pass

        # Split content into chunks
        chunks = SRTUtils.split_into_chunks(srt_content)
        print(f"Split content into {len(chunks)} chunks ... ")

        # Process each chunk
        chunk_outlines = []
        for i, chunk in enumerate(chunks, 1):
            print(f"Processing chunk {i}/{len(chunks)}")
            chunk_outline = self._process_chunk(chunk, i, outline_path)
            chunk_outlines.append(chunk_outline)

        # Combine all outlines
        print("Combining outlines...")
        exit()

        final_outline = self._combine_outlines(chunk_outlines)
        
        # Save and return the final outline
        self._save_json(final_outline, outline_path)
        return final_outline


    def _load_content(self, path):
        """Load the content of a file"""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            raise Exception(f"File not found at {path}")
        except Exception as e:
            raise Exception(f"Error loading path {path}: {str(e)}")
        
    def _load_json(self, path):
        """Load json from a file"""
        content = self._load_content(path)
        try:
            response_data = json.load(content)
            return response_data
        except (json.JSONDecodeError, IOError) as e:
            raise Exception(f"Error loading json from {path}: {e}")

    def _save_json(self, json, path):
        """Save json to a file"""
        try:
            content = json.dumps(json, ensure_ascii=False, indent=2)
            self._save_content(content, path)
        except Exception as e:
            raise Exception(f"Error dumping json to {path}: {e}")
        
    def _save_content(self, content, path):
        """Save content to a file"""
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
        except IOError as e:
            raise Exception(f"Error saving content to {path}: {e}")        

