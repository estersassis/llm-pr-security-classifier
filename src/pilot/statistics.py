from sklearn.metrics import (
    accuracy_score,
    cohen_kappa_score,
    confusion_matrix,
    precision_recall_fscore_support,
)
import json
import os
from dotenv import load_dotenv
load_dotenv()
from src.llm.llm_factory import LLMFactory
from src.utils import extract_json_from_response
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd


class PilotStatistics:
    def __init__(self, model, api_key):
        self.model = model
        self.api_key = api_key
        self.llm_handler = LLMFactory.get_processor(model, api_key)
    
    def generate_llm_pilot_prs_batch(self):
        with open('src/pilot/pilot_prs.json') as f:
            pilot_prs = json.load(f)
        n = len(pilot_prs)
        print(f"Generating LLM pilot PRs in one batch ({n} PRs)")
        user_payload = json.dumps(pilot_prs, ensure_ascii=False, indent=2)
        llm_response = self.llm_handler.generate(user_payload)
        parsed = extract_json_from_response(llm_response)
        if parsed is None:
            print(f"Error extracting JSON from batch response (first 800 chars): {llm_response[:800]!r}")
            return []
        if isinstance(parsed, dict):
            parsed = [parsed]
        if len(parsed) != n:
            print(f"Warning: batch returned {len(parsed)} items, pilot set has {n}")
        return parsed

    def create_llm_pilot_prs_file_batch(self):
        llm_pilot_prs = self.generate_llm_pilot_prs_batch()
        with open('src/pilot/pilot_llm_batch.json', 'w') as f:
            json.dump(llm_pilot_prs, f)

    def calculate_statistics_batch(self):
        y_humano = self.extract_categories('src/pilot/pilot_human.json')
        y_llm = self.extract_categories('src/pilot/pilot_llm_batch.json')
        y_humano_type_of_action = self.extract_type_of_action('src/pilot/pilot_human.json')
        y_llm_type_of_action = self.extract_type_of_action('src/pilot/pilot_llm_batch.json')

        categorias_owasp = [
            "A01: Broken Access Control", "A02: Security Misconfiguration",
            "A03: Software Supply Chain Failures", "A04: Cryptographic Failures",
            "A05: Injection", "A06: Insecure Design", "A07: Authentication Failures",
            "A08: Software or Data Integrity Failures", "A09: Security Logging and Alerting Failures",
            "A10: Mishandling of Exceptional Conditions", "NONE"
        ]

        categories_type_of_action = [
            "FIX/PREVENTION", "VULNERABILITY_INTRODUCTION", "N/A"
        ]

        kappa_owasp_category = cohen_kappa_score(y_humano, y_llm, labels=categorias_owasp)
        kappa_type_of_action = cohen_kappa_score(y_humano_type_of_action, y_llm_type_of_action, labels=categories_type_of_action)
        print(f"[batch LLM] Kappa Score Owasp Category: {kappa_owasp_category}")
        print(f"[batch LLM] Kappa Score Type of Action: {kappa_type_of_action}")
        self._print_classification_stats(
            y_true=y_humano,
            y_pred=y_llm,
            labels=categorias_owasp,
            title="[batch LLM] Owasp Category",
            positive_label="NONE",
            positive_is_match=False,
        )
        self._print_classification_stats(
            y_true=y_humano_type_of_action,
            y_pred=y_llm_type_of_action,
            labels=categories_type_of_action,
            title="[batch LLM] Type of Action",
            positive_label="N/A",
            positive_is_match=False,
        )

    def generate_llm_pilot_prs(self):
        pilot_prs = json.load(open('src/pilot/pilot_prs.json'))
        llm_pilot_prs = []
        for pr in pilot_prs:
            print(f"Generating LLM pilot PRs for {pr['context']['pr_id']}")
            llm_pilot_response = self.llm_handler.generate([pr])
            llm_pilot_response_formatted = extract_json_from_response(llm_pilot_response)
            try:
                print(f"LLM pilot PR response formatted: {llm_pilot_response_formatted[0]}")
            except Exception as e:
                print(f"Error extracting JSON from response: {llm_pilot_response}")
                continue
            print(f"LLM pilot PR response formatted: {llm_pilot_response_formatted[0]}")
            llm_pilot_prs.append(llm_pilot_response_formatted[0])
        return llm_pilot_prs

    def create_llm_pilot_prs_file(self):
        llm_pilot_prs = self.generate_llm_pilot_prs()
        with open('src/pilot/pilot_llm.json', 'w') as f:
            json.dump(llm_pilot_prs, f)

    def extract_categories(self, caminho_arquivo):
        with open(caminho_arquivo, 'r') as f:
            dados = json.load(f)
        return [item['owasp_category'] for item in sorted(dados, key=lambda x: x['pr_id'])]
    
    def extract_type_of_action(self, caminho_arquivo):
        with open(caminho_arquivo, 'r') as f:
            dados = json.load(f)
        return [item['nature'] for item in sorted(dados, key=lambda x: x['pr_id'])]
    
    def calculate_statistics(self):
        y_humano = self.extract_categories('src/pilot/pilot_human.json')
        y_llm = self.extract_categories('src/pilot/pilot_llm.json')
        y_humano_type_of_action = self.extract_type_of_action('src/pilot/pilot_human.json')
        y_llm_type_of_action = self.extract_type_of_action('src/pilot/pilot_llm.json')

        categorias_owasp = [
            "A01: Broken Access Control", "A02: Security Misconfiguration", 
            "A03: Software Supply Chain Failures", "A04: Cryptographic Failures", 
            "A05: Injection", "A06: Insecure Design", "A07: Authentication Failures", 
            "A08: Software or Data Integrity Failures", "A09: Security Logging and Alerting Failures", 
            "A10: Mishandling of Exceptional Conditions", "NONE"
        ]

        categories_type_of_action = [
            "FIX/PREVENTION", "VULNERABILITY_INTRODUCTION", "N/A"
        ]


        kappa_owasp_category = cohen_kappa_score(y_humano, y_llm, labels=categorias_owasp)
        kappa_type_of_action = cohen_kappa_score(y_humano_type_of_action, y_llm_type_of_action, labels=categories_type_of_action)
        print(f"Kappa Score Owasp Category: {kappa_owasp_category}")
        print(f"Kappa Score Type of Action: {kappa_type_of_action}")
        self._print_classification_stats(
            y_true=y_humano,
            y_pred=y_llm,
            labels=categorias_owasp,
            title="Owasp Category",
            positive_label="NONE",
            positive_is_match=False,
        )
        self._print_classification_stats(
            y_true=y_humano_type_of_action,
            y_pred=y_llm_type_of_action,
            labels=categories_type_of_action,
            title="Type of Action",
            positive_label="N/A",
            positive_is_match=False,
        )

    def _print_classification_stats(self, y_true, y_pred, labels, title, positive_label, positive_is_match=True):
        accuracy = accuracy_score(y_true, y_pred)
        precision_macro, recall_macro, f1_macro, _ = precision_recall_fscore_support(
            y_true,
            y_pred,
            labels=labels,
            average="macro",
            zero_division=0,
        )
        conf_matrix = confusion_matrix(y_true, y_pred, labels=labels)
        # pegar só A1, A2, A3, A4, A5, A6, A7, A8, A9, A10, NONE
        labels_simplified = [label.split(":")[0] for label in labels]
        plt.figure(figsize=(10, 10))
        sns.heatmap(conf_matrix, annot=True, fmt="d", cmap="Blues", xticklabels=labels_simplified, yticklabels=labels_simplified)
        plt.title(f"{title} - Confusion Matrix")
        plt.xlabel("Predicted")
        plt.ylabel("True")
        plt.savefig(f"src/pilot/plots/{title}.png")
        plt.close()
        print(f"Confusion matrix plot saved to {title}.png")

        if positive_is_match:
            y_true_positive = [value == positive_label for value in y_true]
            y_pred_positive = [value == positive_label for value in y_pred]
        else:
            y_true_positive = [value != positive_label for value in y_true]
            y_pred_positive = [value != positive_label for value in y_pred]

        tn, fp, fn, tp = confusion_matrix(
            y_true_positive,
            y_pred_positive,
            labels=[False, True],
        ).ravel()

        print(f"\n{title} - Classification Stats")
        print(f"Accuracy: {accuracy:.4f}")
        print(f"Macro Precision: {precision_macro:.4f}")
        print(f"Macro Recall: {recall_macro:.4f}")
        print(f"Macro F1: {f1_macro:.4f}")
        print(f"Binary TP: {tp} | FP: {fp} | FN: {fn} | TN: {tn}")
        print("Confusion Matrix (rows=true, cols=pred):")
        print("Labels order:", labels)
        print(conf_matrix)

# depending on the arguments call the appropriate method
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--create_llm_pilot_prs", action="store_true")
    parser.add_argument("--create_llm_pilot_prs_batch", action="store_true")
    parser.add_argument("--calculate_statistics", action="store_true")
    parser.add_argument("--calculate_statistics_batch", action="store_true")
    args = parser.parse_args()
    statistics = PilotStatistics(model="gemini-3.1-flash-lite", api_key=os.getenv("GEMINI_API_KEY"))
    if args.create_llm_pilot_prs:
        statistics.create_llm_pilot_prs_file()
    elif args.create_llm_pilot_prs_batch:
        statistics.create_llm_pilot_prs_file_batch()
    elif args.calculate_statistics:
        statistics.calculate_statistics()
    elif args.calculate_statistics_batch:
        statistics.calculate_statistics_batch()