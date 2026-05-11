[batch LLM] Kappa Score Owasp Category: 0.886052871467639
[batch LLM] Kappa Score Type of Action: 1.0
Confusion matrix plot saved to [batch LLM] Owasp Category.png

[batch LLM] Owasp Category - Classification Stats
Accuracy: 0.9000
Macro Precision: 0.9136
Macro Recall: 0.8991
Macro F1: 0.8946
Binary TP: 37 | FP: 1 | FN: 0 | TN: 12
Confusion Matrix (rows=true, cols=pred):
Labels order: ['A01: Broken Access Control', 'A02: Security Misconfiguration', 'A03: Software Supply Chain Failures', 'A04: Cryptographic Failures', 'A05: Injection', 'A06: Insecure Design', 'A07: Authentication Failures', 'A08: Software or Data Integrity Failures', 'A09: Security Logging and Alerting Failures', 'A10: Mishandling of Exceptional Conditions', 'NONE']
[[ 5  0  0  0  0  0  0  0  0  0  0]
 [ 1  4  0  0  0  0  0  0  0  0  0]
 [ 0  0  2  0  1  0  0  0  0  0  0]
 [ 0  0  0  3  0  0  0  0  0  0  0]
 [ 0  0  0  0  3  0  0  0  0  0  0]
 [ 0  0  0  0  0  3  1  0  0  0  0]
 [ 0  0  0  0  0  0  4  0  0  0  0]
 [ 0  0  0  0  0  0  1  3  0  0  0]
 [ 0  0  0  0  0  0  0  0  4  0  0]
 [ 0  0  0  0  0  0  0  0  0  2  0]
 [ 0  1  0  0  0  0  0  0  0  0 12]]
Confusion matrix plot saved to [batch LLM] Type of Action.png

[batch LLM] Type of Action - Classification Stats
Accuracy: 0.9800
Macro Precision: 0.6491
Macro Recall: 0.6667
Macro F1: 0.6577
Binary TP: 50 | FP: 0 | FN: 0 | TN: 0
Confusion Matrix (rows=true, cols=pred):
Labels order: ['FIX/PREVENTION', 'VULNERABILITY_INTRODUCTION', 'N/A']
[[18  0  0]
 [ 0 19  0]
 [ 0  0  0]]

# Refinement

[batch LLM] Kappa Score Owasp Category: 0.9771271729185728
[batch LLM] Kappa Score Type of Action: 1.0
Confusion matrix plot saved to [batch LLM] Owasp Category.png

[batch LLM] Owasp Category - Classification Stats
Accuracy: 0.9800
Macro Precision: 0.9848
Macro Recall: 0.9818
Macro F1: 0.9816
Binary TP: 37 | FP: 0 | FN: 0 | TN: 13
Confusion Matrix (rows=true, cols=pred):
Labels order: ['A01: Broken Access Control', 'A02: Security Misconfiguration', 'A03: Software Supply Chain Failures', 'A04: Cryptographic Failures', 'A05: Injection', 'A06: Insecure Design', 'A07: Authentication Failures', 'A08: Software or Data Integrity Failures', 'A09: Security Logging and Alerting Failures', 'A10: Mishandling of Exceptional Conditions', 'NONE']
[[ 5  0  0  0  0  0  0  0  0  0  0]
 [ 1  4  0  0  0  0  0  0  0  0  0]
 [ 0  0  3  0  0  0  0  0  0  0  0]
 [ 0  0  0  3  0  0  0  0  0  0  0]
 [ 0  0  0  0  3  0  0  0  0  0  0]
 [ 0  0  0  0  0  4  0  0  0  0  0]
 [ 0  0  0  0  0  0  4  0  0  0  0]
 [ 0  0  0  0  0  0  0  4  0  0  0]
 [ 0  0  0  0  0  0  0  0  4  0  0]
 [ 0  0  0  0  0  0  0  0  0  2  0]
 [ 0  0  0  0  0  0  0  0  0  0 13]]
Confusion matrix plot saved to [batch LLM] Type of Action.png

[batch LLM] Type of Action - Classification Stats
Accuracy: 1.0000
Macro Precision: 0.6667
Macro Recall: 0.6667
Macro F1: 0.6667
Binary TP: 50 | FP: 0 | FN: 0 | TN: 0
Confusion Matrix (rows=true, cols=pred):
Labels order: ['FIX/PREVENTION', 'VULNERABILITY_INTRODUCTION', 'N/A']
[[18  0  0]
 [ 0 19  0]
 [ 0  0  0]]