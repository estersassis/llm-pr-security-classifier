import re
import json

def extract_json_from_response(response):
    # First try to find JSON objects
    json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    
    match = re.search(json_pattern, response, re.DOTALL)
    if match:
        json_str = match.group(0)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
    
    # Try to find JSON arrays (including empty arrays)
    array_pattern = r'\[\s*(?:\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}\s*(?:,\s*\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}\s*)*)?\]'
    array_match = re.search(array_pattern, response, re.DOTALL)
    if array_match:
        array_str = array_match.group(0)
        try:
            return json.loads(array_str)
        except json.JSONDecodeError:
            pass
    
    # Try to find simple empty array
    empty_array_pattern = r'\[\s*\]'
    empty_match = re.search(empty_array_pattern, response)
    if empty_match:
        return []
    
    return None