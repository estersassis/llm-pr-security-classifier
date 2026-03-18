import json


class PRFormatter:
  def _open_pr_file(self, file_path: str) -> dict:
      """
      Abre e carrega um arquivo JSON de Pull Request.

      Args:
          file_path (str): Caminho para o arquivo JSON do Pull Request.

      Returns:
          dict: Dados do Pull Request carregados do arquivo JSON.
      """
      with open(file_path, "r", encoding="utf-8") as f:
          pr_data = json.load(f)
      return pr_data

  def format_pr_data(self, input_data: dict) -> dict:
    """
    Formata os dados do PR para análise de segurança (OWASP), 
    seguindo as diretrizes de contexto e estrutura do PRIMES.
    """
    # 1. Metadados de Contexto (Essencial para reduzir alucinações)
    # Fonte: Framework PRIMES - Seção III-A [cite: 298]
    context = {
        "repository": input_data.get("base_repository", "unknown"),
        "pr_number": input_data.get("number"),
        "title": input_data.get("title", ""),
        "state": input_data.get("state", ""),
        "is_merged": input_data.get("merged", False),
        "created_at": input_data.get("created_at", {}).get("$date")
    }

    pr_description = input_data.get("body", "")

    # 2. Processamento de Threads e Discussões
    threads = []
    # Thread geral (comentários da timeline principal)
    general_discussion = []
    
    timeline_items = input_data.get("timeline_items", [])
    for item in timeline_items:
        typename = item.get("__typename", "")

        # Coleta comentários gerais (IssueComment)
        if typename == "IssueComment":
            body = item.get("body", "").strip()
            if body:
                # Dica: Se o comentário for muito longo (logs), 
                # pode ser útil truncar ou extrair apenas trechos chave.
                general_discussion.append(body)

        # Coleta revisões específicas de código (Review Threads)
        elif typename == "PullRequestReviewThread":
            path = item.get("path", "unknown_file")
            comments = item.get("comments", [])
            
            if not comments:
                continue

            # Identifica o escopo (Linha ou Arquivo)
            first_comment = comments[0]
            line = first_comment.get("line") or first_comment.get("start_line")
            scope = f"FILE:{path}" + (f"#L{line}" if line else "")

            discussion = [
                body
                for c in comments
                for body in [(c.get("body") or "").strip()]
                if body
            ]
            if discussion:
                threads.append({"scope": scope, "comments": discussion})

    # Consolida o retorno em uma estrutura clara para a LLM
    return {
        "context": context,
        "description": pr_description,
        "general_discussion": general_discussion,
        "code_review_threads": threads
    }

  def format_pr_discussions(self, file_path: str) -> dict:
      """
      Converte um objeto de Pull Request (como nos dumps do GraphQL/REST do GitHub)
      para o formato compacto descrito na docstring do módulo.

      Args:
          file_path (str): Caminho para o arquivo JSON do Pull Request.

      Returns:
          dict: Dados formatados do Pull Request.
      """
      input_data = self._open_pr_file(file_path)
      return self.format_pr_data(input_data)