import os
import json
import datetime
import uuid

class ApiInteractionLogger:
    def __init__(self, log_dir):
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)

    def _log(self, base_name, interaction_type, data):
        base_name = os.path.splitext(os.path.basename(base_name))[0]
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        unique_id = uuid.uuid4().hex
        log_file = os.path.join(
            self.log_dir,
            f'{base_name}_{interaction_type}_{timestamp}_{unique_id}.json'
        )

        print(f"Logging {interaction_type} to {log_file}")
        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Failed to log {interaction_type}: {str(e)}")

    def log_request(self, base_name, data):
        self._log(base_name, 'request', data)

    def log_response(self, base_name, data):
        self._log(base_name, 'response', data) 