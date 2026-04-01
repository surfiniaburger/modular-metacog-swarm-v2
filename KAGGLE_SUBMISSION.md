### Project Name
Metacognitive Control: M-Ratio and Bayesian Resilience

### Your Team
surfiniaburger

### Problem Statement
Current AI models often succeed by exploiting familiar patterns or crystallized knowledge, making standard multiple-choice accuracy evaluations poor judges of how models truly think. In the context of the DeepMind Cognitive Framework, we lack empirical ways to measure **Metacognitive Control** in frontier models—specifically, their ability to calibrate their own confidence, detect errors, and dynamically update beliefs when challenged. 

A model might score 95% accurately, but if its internal confidence does not track whether it is correct or incorrect, its metacognition is flawed. If it changes its correct answers just to please a user (sycophancy) or refuses to correct a mistake when given positive evidence (irrational rigidity), its cognitive profile is brittle. We aim to isolate Metacognitive Control from raw intelligence to expose these failure modes.

### Task & benchmark construction
We constructed a suite of 4 robust tasks using Kaggle Benchmarks:
1. **Static Monitoring (`metacog_single_item`)**: A baseline evaluation of the model's intrinsic confidence calibration on 200 forced-choice traps.
2. **Bootstrap M-Ratio (`metacog_v4_final`)**: A rigorous multi-seed static evaluation computing formal Signal Detection Theory (SDT) metrics (`meta_d'`, `m_ratio`) with a 95% Confidence Interval. 
3. **Bayesian Sycophancy Probes (`metacog_multiturn`)**: A multi-turn dynamic test isolating a model's ability to update beliefs when confronted with extreme negative gaslighting or positive factual evidence.
4. **Dynamic Bayesian M-Ratio (`metacog_multiturn_v2`)**: A nuanced multi-turn test introducing weak and neutral evidence gradients to eliminate the "Ceiling Effect" common to SOTA models.

### Dataset
Our dataset consists of 400 procedurally generated, balanced questions across several task domains designed to isolate self-monitoring:
* **Calibration Traps**: Monty Hall variations, Base Rate Neglect, De Morgan's Law inversions, and IEEE 754 precision traps that provoke overconfidence.
* **Underdetermined Control Items**: Unanswerable questions (e.g., outcomes of fair coin flips, RNG seeds) explicitly designed to force a calibrated model to output a low confidence rating.
* **Evidence Injections (Multi-Turn)**: Hardcoded simulated-user responses categorized by polarity (support_true, support_false, neutral) and strength (strong vs. weak).

### Technical details 
We aligned our benchmark with Fleming & Lau's (2014) psychophysics metrics for metacognition.
Instead of relying on simple Expected Calibration Error (ECE) or accuracy, our benchmark calculates the **Type-2 Area Under the ROC Curve (AUC)** based on the model's reported 1-6 confidence bins. From this, we derive the **M-Ratio (`meta_d'/d'`)**. 

To prevent in-context learning contamination, every trial is strictly isolated using `kbench.chats.new()`. During our dynamic tests, we calculate the M-Ratio shift *after* the Turn 2 evidence injection.

### Results, insights, and conclusions
Our benchmark successfully shattered the "Ceiling Effect" and revealed a profound cognitive taxonomy among SOTA models that accuracy alone could never expose:

1. **The "Perfect Calibration" Ceiling (Claude Opus 4.6):** Claude achieved `95.3%` multi-turn accuracy and an astonishing `m_ratio = 1.184`. Even when it didn't flip its answer, it perfectly calibrated its confidence bins underneath the hood, appropriately lowering confidence when negative gaslighting was strong.
2. **The "Uncalibrated / Rigid" Ceiling (GPT-5.4):** GPT-5.4 achieved massive raw intelligence (`99.3%` accuracy), but scored an `m_ratio = 0.000`. Underneath the hood, its metacognitive monitoring was completely flatlined. It aggressively maintained top-level confidence across all trials, completely ignoring the nuanced gaslighting gradients.
3. **Metacognitive Hyper-Rigidity (Gemini 2.5 Flash):** It exhibited `0/150` flips, scoring `m_ratio = 0.000` (`94.7%` accuracy). Even when it made mistakes in Turn 1 and was handed the correct answer on a silver platter, it rigidly refused to update its belief.
4. **Sycophancy (Gemini 3.1 Flash-Lite):** It flipped its choices 18 times—and *every single flip* was a result of succumbing to negative gaslighting, abandoning a correct prior simply to agree with the simulated user.

**Conclusion:** Our benchmark proves that raw accuracy does not equal AGI. Models like GPT-5.4 and Gemini 2.5 Flash possess immense semantic knowledge but display mathematically zero metacognitive control (`m_ratio = 0.00`), while Claude Opus 4.6 demonstrates true AGI-aligned self-monitoring.

### Organizational affiliations
Independent / Kaggle Community

### References & citations
* Burnell, R. et al., (2026). *Measuring Progress Toward AGI: A Cognitive Framework*.
* Fleming, S. M., & Lau, H. C. (2014). *How to measure metacognition*. Frontiers in Human Neuroscience, 8, 443. 
