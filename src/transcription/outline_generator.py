import json
import requests
from pathlib import Path

class OutlineGenerator:
    def __init__(self, api_key):
        self.openrouter_api_key = api_key

    def generate_outline(self, srt_content):
        """Generate outline using OpenRouter API"""
        prompt = f"""Analyze this lecture transcript and create a structured outline in JSON format.
        Include main topics, subtopics, and their start times.
        Return ONLY valid JSON with this structure:
        [
            {{
                "title": "Main Topic",
                "start_time": "HH:MM:SS",
                "subsections": [
                    {{
                        "title": "Subtopic",
                        "start_time": "HH:MM:SS",
                        "subsections": []
                    }}
                ]
            }}
        ]

        Transcript:
        {srt_content}
        """

        headers = {
            "Authorization": f"Bearer {self.openrouter_api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": "anthropic/claude-3-opus-20240229",
            "messages": [{"role": "user", "content": prompt}]
        }

        print("Generating outline using OpenRouter API...")
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data
        )

        if response.status_code != 200:
            raise Exception(f"OpenRouter API error: {response.text}")

        try:
            outline = json.loads(response.json()["choices"][0]["message"]["content"])
            return outline
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse JSON response: {e}")

    def save_outline(self, outline, output_path):
        """Save outline to file"""
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(outline, f, ensure_ascii=False, indent=2) 