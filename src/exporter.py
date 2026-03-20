"""
Exporta resultados do pilot.json para planilha Excel no formato de avaliação.
"""
import json
from pathlib import Path
from src.pr_formatter import PRFormatter


def create_evaluation_excel(
    input_path: str = "pilot.json",
    output_path: str = "evaluation_output.xlsx",
) -> str:
    """
    Cria arquivo Excel similar ao evaluation_sample.xlsx com base no pilot.json.

    Colunas: PR_ID, Category, Issue_Description, PR_Formatted, LLM_Output, Evaluation, Justify

    Args:
        input_path: Caminho do arquivo JSON de entrada (pilot.json)
        output_path: Caminho do arquivo Excel de saída

    Returns:
        Caminho do arquivo criado
    """
    try:
        import pandas as pd
    except ImportError:
        raise ImportError("pandas é necessário. Instale com: pip install pandas")

    try:
        from openpyxl.styles import Alignment
    except ImportError:
        raise ImportError("openpyxl é necessário. Instale com: pip install openpyxl")

    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {input_path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("O JSON deve conter uma lista de issues")

    rows = []
    for item in data:
        if not isinstance(item, dict):
            continue
        pr_id = item.get("pr_id", "")
        owasp = item.get("owasp_category", "")
        nature = item.get("nature", "")
        summary = item.get("summary", "")

        llm_output = json.dumps(
            {
                "pr_id": pr_id,
                "owasp_category": owasp,
                "nature": nature,
                "summary": summary
            },
            ensure_ascii=False,
        )
        if len(llm_output) > 1000:
            llm_output = llm_output[:1000] + "..."
        
        # Abrir arquivo django/ cujo nome é o pr_id e carregar o conteúdo
        pr_file_path = Path("django") / f"{pr_id}.json"
        try:
            pr_formatted = PRFormatter().format_pr_discussions(pr_file_path)
        except Exception as e:
            print(f"Erro ao formatar PR {pr_id}: {e}")
            pr_formatted = f"Erro ao formatar PR {pr_id}: {e}"

        rows.append({
            "PR_ID": pr_id,
            "Category": owasp,
            "Issue_Description": summary,
            "PR_Formatted": pr_formatted,  # pilot.json não possui PR formatado
            "LLM_Output": llm_output,
            "Evaluation": "",
            "Justify": "",
        })

    df = pd.DataFrame(rows)
    df = df[["PR_ID", "Category", "Issue_Description", "PR_Formatted", "LLM_Output", "Evaluation", "Justify"]]

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="PR_Evaluation", index=False)
        ws = writer.sheets["PR_Evaluation"]

        column_widths = {
            "A": 30,
            "B": 25,
            "C": 40,
            "D": 80,
            "E": 60,
            "F": 15,
            "G": 40,
        }
        for col, width in column_widths.items():
            ws.column_dimensions[col].width = width

        for row in ws.iter_rows(min_row=2):
            for cell in row:
                if cell.column_letter in ["C", "D", "E", "G"]:
                    cell.alignment = Alignment(wrap_text=True, vertical="top")

    return str(out)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Cria planilha Excel de avaliação a partir do pilot.json")
    parser.add_argument("-i", "--input", default="pilot.json", help="Arquivo JSON de entrada")
    parser.add_argument("-o", "--output", default="evaluation_output.xlsx", help="Arquivo Excel de saída")
    args = parser.parse_args()

    output = create_evaluation_excel(args.input, args.output)
    print(f"Planilha criada: {output}")
