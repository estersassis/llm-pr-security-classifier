import re
import json

def extract_json_from_response(response):
    # Handle None or empty response
    if response is None or not isinstance(response, str):
        return None

    stripped = response.strip()

    # Tenta parse completo primeiro (resposta JSON limpa)
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    # Resposta pode vir embutida em texto; extrai JSON iniciando em [ ou {
    for start_char, end_char in [("[", "]"), ("{", "}")]:
        if start_char in stripped:
            start = stripped.find(start_char)
            # Tenta parse do primeiro [ ou { até o fim, encurtando até obter JSON válido
            for end in range(len(stripped), start, -1):
                candidate = stripped[start:end]
                if not candidate.endswith(end_char):
                    continue
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    continue
            break

    # Fallback: busca primeiro objeto ou array via regex
    json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    match = re.search(json_pattern, stripped, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    array_pattern = r'\[\s*(?:\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}\s*(?:,\s*\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}\s*)*)?\]'
    array_match = re.search(array_pattern, stripped, re.DOTALL)
    if array_match:
        try:
            return json.loads(array_match.group(0))
        except json.JSONDecodeError:
            pass

    if re.search(r'\[\s*\]', stripped):
        return []
    
    return None