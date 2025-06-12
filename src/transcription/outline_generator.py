import json
import requests
from pathlib import Path
import os
import datetime
import traceback
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

    def _process_chunk(self, chunk, chunk_index, chunk_total, outline_path):
        """Process a single chunk of SRT content"""
        json_path = self._get_chunk_json_path(outline_path, chunk_index)
        print(f"Processing chunk {chunk_index} ... {json_path}")
    
        # Check for cached response first
        try:
            cached_response = self._load_json(json_path)
            print(f"Using cached response for chunk ... {json_path}")
            return cached_response
        except Exception as e:
            print(f"Error loading cached response for chunk {chunk_index} ... {json_path}: {str(e)}")
            pass

        #raise Exception(f"Processing not cached chunk {chunk_index} ... {json_path}")

        prompt_system_message = self._load_content(os.path.join(os.path.dirname(__file__), "prompts", "srt_chunk_prompt_system_message.txt"))
        #print(f"prompt content: {prompt_system_message}")

        # Replace the placeholders directly since the template uses simple {chunk_index} and {chunk}
        prompt_system_message = prompt_system_message.replace("{chunk_index}", str(chunk_index)).replace("{chunk_total}", str(chunk_total)).replace("{chunk}", chunk)

        prompt_user_message = self._load_content(os.path.join(os.path.dirname(__file__), "prompts", "srt_chunk_prompt.txt"))
        #print(f"prompt content: {prompt_user_message}")

        # Replace the placeholders directly since the template uses simple {chunk_index} and {chunk}
        prompt_user_message = prompt_user_message.replace("{chunk_index}", str(chunk_index)).replace("{chunk_total}", str(chunk_total)).replace("{chunk}", chunk)
        #print(f"prompt_user_message: {prompt_user_message}")


        self._save_content(prompt_system_message, os.path.join(self.logs_dir, f"prompt_system_message_{chunk_index}.txt"))
        self._save_content(prompt_user_message, os.path.join(self.logs_dir, f"prompt_user_message_{chunk_index}.txt"))

        #raise Exception(f"Processing chunk {chunk_index} ... {json_path}")
    
        headers = {
            "Authorization": f"Bearer {self.openrouter_api_key}",
            "Content-Type": "application/json"
        }

        data = {
            #"model": "openai/o3", - openai cant be used through openrouter, only with its own api key
            #"model": "anthropic/claude-3-sonnet", - very bad performance for tokens above 5000
            "model": "openai/o4-mini-high",
            "messages": [
                {"role": "system", "content": prompt_system_message}, 
                {"role": "user", "content": prompt_user_message}
                ]
        }

        # Log the request
        self._log_api_interaction('request', {
            'timestamp': datetime.datetime.now().isoformat(),
            'headers': headers,
            'data': data,
            'prompt_system_message': prompt_system_message,
            'prompt_user_message': prompt_user_message,
            'chunk_index': chunk_index,
            'outline_path': outline_path
        })

        try:
            # Check if cached response exists in logs
            """
            log_path = f"/mnt/x/srv/git.romanmatena.cz/24gatel.eu/videooutliner/logs/api/response_last.json"
            if os.path.exists(log_path):
                try:
                    with open(log_path, 'r', encoding='utf-8') as f:
                        log_data = json.load(f)
                        if 'text' in log_data:
                            response_text = log_data['text'].strip()
                            response_json = json.loads(response_text)
                            print(f"response_json: {response_json}")
                            if response_json.get("choices") and response_json["choices"][0].get("message"):
                                content = response_json["choices"][0]["message"]["content"].strip()
                                print(f"logged content: {content}")
                                content_json = json.loads(content)
                                # Save the response
                                self._save_json(content_json, json_path)
                                return content_json
                except Exception as e:
                    print(f"Error reading cached log file: {str(e)}")
                    # Continue with API call if log reading fails
                    raise
            """

            #exit()
                
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=1800
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

            response_text = response.text.strip()
            response_json = json.loads(response_text)
            if not response_json.get("choices") or not response_json["choices"][0].get("message"):
                raise Exception("Invalid response format from API")
            
            content = response_json["choices"][0]["message"]["content"].strip()
            print(f"content: {content}")
            content_json = json.loads(content)

            # Save the response
            self._save_json(content_json, json_path)

            return content_json
        except Exception as e:
            print("Full traceback:")
            traceback.print_exc()
            raise

    def _combine_outlines(self, outline_path, outlines):
        """Combine multiple outlines into a single coherent outline"""

        print(f"Combining outlines ... {outline_path}")
        print(f"outlines: {outlines}")

        prompt_system_message = self._load_content(os.path.join(os.path.dirname(__file__), "prompts", "combine_outlines_prompt_system_message.txt"))
        #print(f"prompt content: {prompt_system_message}")

        # Replace the placeholders directly since the template uses simple {chunk_index} and {chunk}
        prompt_system_message = prompt_system_message.replace("{outlines}", str(json.dumps(outlines, indent=2)))

        prompt_user_message = self._load_content(os.path.join(os.path.dirname(__file__), "prompts", "combine_outlines_prompt.txt"))
        #print(f"prompt content: {prompt_user_message}")

        # Replace the placeholders directly since the template uses simple {chunk_index} and {chunk}
        prompt_user_message = prompt_user_message.replace("{outlines}", str(json.dumps(outlines, indent=2)))
        #print(f"prompt_user_message: {prompt_user_message}")

        self._save_content(prompt_system_message, os.path.join(self.logs_dir, f"prompt_combined_system_message.txt"))
        self._save_content(prompt_user_message, os.path.join(self.logs_dir, f"prompt_combined_user_message.txt"))

        #raise Exception("Combining outlines")

        headers = {
            "Authorization": f"Bearer {self.openrouter_api_key}",
            "Content-Type": "application/json"
        }

        data = {
            #"model": "openai/o3", - openai cant be used through openrouter, only with its own api key
            #"model": "anthropic/claude-3-sonnet", - very bad performance for tokens above 5000
            "model": "openai/o4-mini-high",
            "messages": [
                {"role": "system", "content": prompt_system_message}, 
                {"role": "user", "content": prompt_user_message}
                ]
        }

        # Log the request
        self._log_api_interaction('request', {
            'timestamp': datetime.datetime.now().isoformat(),
            'headers': headers,
            'data': data,
            'prompt_system_message': prompt_system_message,
            'prompt_user_message': prompt_user_message,
        })        

        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=1800
            )

            # Log the response
            self._log_api_interaction('response', {
                'timestamp': datetime.datetime.now().isoformat(),
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'text': response.text,
                'encoding': response.encoding,
            })            

            if response.status_code != 200:
                raise Exception(f"OpenRouter API error: {response.text}")

            response_json = response.json()
            if not response_json.get("choices") or not response_json["choices"][0].get("message"):
                raise Exception("Invalid response format from API")
            
            content = response_json["choices"][0]["message"]["content"].strip()
            content_json = json.loads(content)

            # Save the response
            self._save_json(content_json, outline_path)

            return content_json
        except Exception as e:
            raise Exception(f"Error processing combining outlines {outline_path}: {str(e)}")

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
        chunks = SRTUtils.smart_chunk_by_paragraphs(srt_content, 10000)
        print(f"Content was split into {len(chunks)} chunks ... ")

        # Process each chunk
        chunk_outlines = []
        for i, chunk in enumerate(chunks, 1):
            print(f"Processing chunk {i}/{len(chunks)}")
            chunk_outline = self._process_chunk(chunk, i, len(chunks), outline_path)
            chunk_outlines.append(chunk_outline)

        # Combine all outlines
        print("Combining outlines...")
        if len(chunk_outlines) > 1:
            # Merge all chunk outlines into a single array
            merged_outlines = []
            for outline in chunk_outlines:
                if isinstance(outline, list):
                    merged_outlines.extend(outline)
                else:
                    merged_outlines.append(outline)

            #print(f"Merged outlines:")
            #print(json.dumps(merged_outlines, indent=2))

            #raise Exception("Merged outlines")
        

            final_outline = self._combine_outlines(outline_path, merged_outlines)
        else:
            final_outline = chunk_outlines[0]
        
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
            response_data = json.loads(content)
            return response_data
        except (json.JSONDecodeError, IOError) as e:
            raise Exception(f"Error loading json from {path}: {e}")

    def _save_json(self, data, path):
        """Save json to a file"""
        try:
            content = json.dumps(data, ensure_ascii=False, indent=2)
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

