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

  def _format_pr_data(self, input_data: dict) -> dict:
      """
      Format PR data directly from dictionary input (for async processing).
      
      Args:
          input_data (dict): Raw PR data dictionary
          
      Returns:
          dict: Formatted PR data in the standard format
      """
      pr_title = input_data.get("title", "")
      pr_id = input_data.get("id", "")
      pr_description = input_data.get("body", "")

      threads = []
      general_thread = {"scope": "PR", "discussion": []}

      timeline_items = input_data.get("timeline_items", [])
      for item in timeline_items:
          typename = item.get("__typename", "")

          if typename == "IssueComment":
              comment_body = item.get("body", "").strip()
              if comment_body:
                  general_thread["discussion"].append(comment_body)

          elif typename == "PullRequestReviewThread":
              path = item.get("path", "")
              subject_type = item.get("subject_type", "")
              comments = item.get("comments", [])

              if not path or not comments:
                  continue

              if subject_type == "FILE":
                  scope = f"FILE:{path}"
              elif subject_type == "LINE":
                  first_comment = comments[0]
                  line_info = first_comment.get("line", None)
                  start_line_info = first_comment.get("start_line", None)
                  end_line_info = first_comment.get("end_line", None)

                  if line_info is not None:
                      scope = f"LINE:{path}#L{line_info}"
                  elif start_line_info is not None and end_line_info is not None:
                      scope = f"LINE:{path}#L{start_line_info}-L{end_line_info}"
                  else:
                      scope = f"FILE:{path}"  # Fallback
              else:
                  scope = f"FILE:{path}"  # Fallback

              discussion = []
              for comment in comments:
                  comment_body = comment.get("body", "").strip()
                  if comment_body:
                      discussion.append(comment_body)

              if discussion:
                  threads.append({"scope": scope, "discussion": discussion})

      if general_thread["discussion"]:
          threads.insert(0, general_thread)  # Coloca o thread geral no início

      return {
          "pr": {
              "title": pr_title,
              "id": pr_id,
              "description": pr_description
          },
          "threads": threads
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
      return self._format_pr_data(input_data)