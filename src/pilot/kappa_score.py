from sklearn.metrics import cohen_kappa_score
import json

def extract_categories(caminho_arquivo):
    with open(caminho_arquivo, 'r') as f:
        dados = json.load(f)
    return [item['owasp_category'] for item in sorted(dados, key=lambda x: x['pr_id'])]

# Simulando os caminhos dos arquivos
y_humano = extract_categories('pilot_human.json')
y_llm = extract_categories('pilot_llm.json')

# As categorias devem ser exatamente as mesmas nos dois arquivos
categorias_owasp = [
    "A01: Broken Access Control", "A02: Security Misconfiguration", 
    "A03: Software Supply Chain Failures", "A04: Cryptographic Failures", 
    "A05: Injection", "A06: Insecure Design", "A07: Authentication Failures", 
    "A08: Software or Data Integrity Failures", "A09: Security Logging and Alerting Failures", 
    "A10: Mishandling of Exceptional Conditions", "NONE"
]

# O cálculo permanece o mesmo, o sklearn trata a multiclasse internamente
kappa = cohen_kappa_score(y_humano, y_llm, labels=categorias_owasp)
print(f"Kappa Score: {kappa}")