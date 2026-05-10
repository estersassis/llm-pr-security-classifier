class PromptRepository:
    def __init__(self, model_name: str):
        self.model_name = 'gemini' if 'gemini' in model_name.lower() else 'ollama'

    def get_system_prompt(self) -> str:
        SYSTEM_PROMPT = {
            "gemini": """<role>
You are a security expert specializing in OWASP Top 10 2025 vulnerabilities in code reviews and PR discussions. 
</role>

<instructions>
Analyze the provided list of PRs. For each PR, execute the following steps:
            - Determine if the discussion DIRECTLY SPECIFIES a security hole.
            - Map concerns ONLY to the provided <categories>.
            - Identify the "Nature of Action": Is this a FIX/PREVENTION or a VULNERABILITY_INTRODUCTION?
            - Present the final answer as a list of JSON objects, one for each PR analyzed.
</instructions>

<categories>
"A01: Broken Access Control", "A02: Security Misconfiguration", "A03: Software Supply Chain Failures", "A04: Cryptographic Failures", "A05: Injection", "A06: Insecure Design", "A07: Authentication Failures", "A08: Software or Data Integrity Failures", "A09: Security Logging and Alerting Failures", "A10: Mishandling of Exceptional Conditions", "NONE"
</categories>

<output_format>
Return a JSON list:
[{
    "pr_id": "PR_ID",
    "owasp_category": "Category Name",
    "nature": "FIX/PREVENTION | VULNERABILITY_INTRODUCTION | NONE if owasp_category is NONE",
    "summary": "Short justification for the category classification, MUST be NONE if owasp_category is NONE."
}]
</output_format>

<constraints>
    - The PR must have a discussion to be classified, only the title and description are not enough.
    - Prioritize the ultimate security risk over the implementation mechanism. Classify fundamental logic flaws (e.g., security questions, MFA bypasses) as "A06: Insecure Design"; prioritize "A02: Security Misconfiguration" for technical exposures (stack traces) or incorrect permissions (ACLs); and use "A08: Software or Data Integrity Failures" for any lack of verification regarding untrusted data, headers, signatures, or deserialization (Pickle/JSON).
    - If no security issues are found, return "NONE" for owasp_category, nature and summary, but the PR must be classified.
</constraints>
""",
            "ollama": None
        }

        return SYSTEM_PROMPT[self.model_name]
    
    def get_user_prompt(self, user_content: str) -> str:
        USER_PROMPT = {
            "gemini": f"""<context>
{user_content}
</context>
<final_instruction>
Analyze the pull requests in the context above. Execute the OWASP 2025 security analysis following the system instructions. Think step-by-step. 
</final_instruction>""",
            "ollama": None
        }

        return USER_PROMPT[self.model_name]