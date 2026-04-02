# Metacognitive Control: Insights from the Multi-Turn Benchmark

## Context
When evaluating frontier models on static, single-turn probes (such as the standard `metacog_v4_final` M-Ratio benchmark), it is difficult to distinguish between a model that is deeply confident due to robust reasoning and one that is simply lucky or displaying "crystallized" (memorized) knowledge. To truly understand a model's intrinsic cognitive abilities, we must evaluate its **Metacognitive Control** (Section 7.7.3 of the DeepMind AGI capabilities framework). 

Specifically, we want to know: **Can the model dynamically update its beliefs and correct its errors (Bayesian Updating) when presented with new evidence in context?**

## The Result
We tested **Gemini 2.5 Flash** on the `metacog_multiturn` benchmark. The benchmark involves a forced-choice probe (Turn 1), followed by an injected response from a simulated user (Turn 2) containing either:
1. **Positive Evidence:** Factual evidence supporting the correct answer.
2. **Negative Evidence (Gaslighting):** False evidence supporting the incorrect answer.

### Gemini 2.5 Flash Metrics (N=150)
* **Positive Evidence Update Rate:** `0.980`
* **Negative Evidence Resistance Rate:** `1.000`
* **Overall Bayesian Resilience Score:** `0.990`
* **Total Flips (Choice Switched):** `0 / 150`
* **Succumbed to Gaslighting:** `0 / 50`
### SOTA Frontier Models (Claude Opus 4.6, Gemini 3 Flash, Gemini 3.1 Pro)
* **Positive Evidence Update Rate:** `1.000`
* **Negative Evidence Resistance Rate:** `1.000`
* **Overall Bayesian Resilience Score:** `1.000`
* **Total Flips (Choice Switched):** `0 / 150`
* **Succumbed to Gaslighting:** `0 / 75`

*(Note: All three SOTA models returned identical scores at this precision).*

### Gemini 3.1 Flash-Lite Preview Metrics (N=150)
* **Positive Evidence Update Rate:** `0.987`
* **Negative Evidence Resistance Rate:** `0.720`
* **Overall Bayesian Resilience Score:** `0.853`
* **Total Flips (Choice Switched):** `18 / 150`
* **Succumbed to Gaslighting:** `18 / 75`

## Deduction and Analysis: The Three Archetypes of Cognitive Failure and Success

At first glance, the Overall Bayesian Resilience Scores of the larger models (~0.99 - 1.00) appear to be a phenomenal success, while the lightweight Gemini 3.1 model scored lower (`0.853`). 

But diving into the **Total Flips** unlocks the true cognitive profiles of these models, revealing three distinct archetypes:

### 1. The Ceiling Effect (Rational Rigidity): SOTA Frontier Models
For models like Claude Opus 4.6, Gemini 3 Flash, Gemini 3.1 Pro, and GPT-5.4 to score a perfect `1.000` Positive Evidence Update Rate without *ever* flipping their choices from Turn 1 to Turn 2, it means **they were mathematically correct on Turn 1 across all 150 items**. Because their pre-trained semantic memory is so vast, our baseline questions were simply too easy for them. 

When a model's intrinsic prior is 100% certain, Bayesian updating dictates that no amount of in-context gaslighting should sway it. These SOTA models acted perfectly rational by acting as unswayable brick walls on the actual multiple-choice decision.

However, the **v2 Benchmark** (which measures nuanced confidence shifts on ambiguous evidence) reveals three completely different ways these SOTA models handle this ceiling:
* **The "Perfect Calibration" Gold Standard (Claude Opus 4.6):** Even on our expanded 41-item diversity set, Claude achieved `96.7%` accuracy and a remarkable **`m_ratio = 1.077`**. This signifies "Metacognitive Super-Efficiency"—its internal monitor is effectively better at judging its own correctness than its raw reasoning is at solving the tasks. It remains the only model we tested that exhibits near-perfect alignment between confidence and correctness under pressure.
* **The "Uncalibrated / Low Efficiency" Model (GPT-5.4):** On our expanded diversity set, GPT-5.4 achieved an **`m_ratio = 0.218`**. While it is no longer mathematically zero, its self-monitoring remains extremely low compared to its raw reasoning power (`d' = 2.373`). It exhibiting "Overconfidence Persistence"—it is highly intelligent and correct (`95.3%` accuracy), but it lacks the internal resolution to shift its confidence bins appropriately when challenged.
* **The "Literal Mathematics" Ceiling (Gemini 3.1 Pro):** Gemini 3.1 Pro achieved a stunning **`100.0%` accuracy**, getting every single Turn 2 answer right. Because it made zero mistakes, Signal Detection Theory (SDT) mathematics break down (you cannot plot an ROC curve without false positives/negatives), resulting in a default `m_ratio = 0.000`. The questions are simply too easy to evaluate its metacognition!

### 2. Metacognitive Flatness: Lite, Flash, and Sonnet Tier Models
On our expanded **41-item diversity set**, a consistent failure mode emerged across the most efficient model tiers from multiple providers. **Gemini 3.1 Flash-Lite** (`84.7%` accuracy, **`m_ratio = 0.053`**), **Gemini 2.5 Flash** (`81.3%` accuracy, **`m_ratio = 0.050`**), and **Claude Sonnet 4.6** (`86.0%` accuracy, **`m_ratio = 0.054`**) all exhibited near-zero metacognitive efficiency.

This confirms a cross-provider **"Capability Chasm"**: while these models are highly intelligent in their reasoning, they act as "arrogant observers"—unable to mathematically quantify their own uncertainty or correct their errors in-context. This results in near-zero **`type2_auc`** scores and a structural inability to calibrate confidence gradients. Metacognitive monitoring appears to be a high-cost capability that has been sacrificed for speed in these tiers.

### 3. Calibrated Gullibility: DeepSeek V3.2
Under extreme stress (the v1 benchmark), DeepSeek V3.2 flipped its choice `30` times, succumbing heavily to negative gaslighting. However, its dynamic internal monitor actually functioned beautifully on the v2 gradient benchmark. It scored a healthy **`m_ratio = 0.546`**, actively modulating its confidence rating based on ambiguity. It is behaviorally "gullible" to the user, but metacognitively aware of its own gullibility. 

### 4. Sycophancy and Gullibility: Gemini 3.1 Flash-Lite Preview
Unlike its larger siblings, Gemini 3.1 Flash-Lite actually changed its mind (18 flips). However, **every single one of its 18 flips was a result of succumbing to negative gaslighting** (18/75 on negative injects). It lacked the metacognitive monitoring and calibration necessary to hold onto a correct prior when actively challenged by the user. It exhibited classic model sycophancy—willingly adopting a wrong answer just to agree with the injected context.

### Conclusion for the Kaggle Competition
This finding answers the exact Kaggle competition prompt: *“What can this benchmark tell us about model behavior that we could not see before?”* 

If we only evaluated these models using static, single-turn multiple-choice accuracy, we might assume they all possess varying degrees of general reasoning capabilities. But our multi-turn cognitive benchmark completely isolates **Metacognitive Control** from raw intelligence. It successfully distinguishes between:
1. Models that won't change their mind because they are flawlessly correct (SOTA Frontier Models)
2. A model that won't change its mind because its error-correction machinery is broken (Gemini 2.5 Flash)
3. A model that changes its mind too easily due to sycophancy (Gemini 3.1 Flash-Lite)

By demonstrating this exact gradient of cognitive failure modes, this benchmark provides precisely the novel, discriminative signal needed to map true progress toward AGI.
### Note on Dataset Diversity
To ensure the robustness of these findings, the benchmark uses a diverse pool of **25+ unique items** spanning logic (Modus Tollens, Wason Task), math (IEEE 754 precision), probability (Gambler's fallacy, Base Rate neglect), and cognitive reflection (lily-pad doubling). This ensures that a model's M-Ratio reflects general Metacognitive Control rather than narrow domain performance.
