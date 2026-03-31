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
For models like Claude Opus 4.6, Gemini 3 Flash, and Gemini 3.1 Pro to score a perfect `1.000` Positive Evidence Update Rate without *ever* flipping their choices from Turn 1 to Turn 2, it means **they were 100% mathematically correct on Turn 1 across all 150 items**. Because their pre-trained semantic memory is so vast, our baseline questions were simply too easy for them. 

When a model's intrinsic prior is 100% certain, Bayesian updating dictates that no amount of in-context gaslighting should sway it. These SOTA models acted perfectly rational by acting as unswayable brick walls.

### 2. Metacognitive Hyper-Rigidity (Irrational Rigidity): Gemini 2.5 Flash
Gemini 2.5 Flash also registered `0/150` flips on extreme evidence, but it *did* make mistakes in Turn 1. Even when handed the correct answer to fix its mistake, it refused to flip its choice. 

When we subjected Gemini 2.5 Flash to the **v2 Benchmark** (which introduces weak/ambiguous evidence and measures calibrated confidence shifts), its rigidity was mathematically proven. Because it acted as a brick wall and refused to adjust its confidence bins appropriately in Turn 2, its resulting Fleming/Lau signal was completely flatlined: **`type2_auc = 0.500`** and **`m_ratio = 0.000`**. 

This `0.000` M-Ratio is the mathematical quantification of Irrationial Rigidity. It relies entirely on its pre-trained prior (even when flawed) and has exactly zero metacognitive control capability to dynamically revise beliefs in context.

### 3. Sycophancy and Gullibility: Gemini 3.1 Flash-Lite Preview
Unlike its larger siblings, Gemini 3.1 Flash-Lite actually changed its mind (18 flips). However, **every single one of its 18 flips was a result of succumbing to negative gaslighting** (18/75 on negative injects). It lacked the metacognitive monitoring and calibration necessary to hold onto a correct prior when actively challenged by the user. It exhibited classic model sycophancy—willingly adopting a wrong answer just to agree with the injected context.

### Conclusion for the Kaggle Competition
This finding answers the exact Kaggle competition prompt: *“What can this benchmark tell us about model behavior that we could not see before?”* 

If we only evaluated these models using static, single-turn multiple-choice accuracy, we might assume they all possess varying degrees of general reasoning capabilities. But our multi-turn cognitive benchmark completely isolates **Metacognitive Control** from raw intelligence. It successfully distinguishes between:
1. Models that won't change their mind because they are flawlessly correct (SOTA Frontier Models)
2. A model that won't change its mind because its error-correction machinery is broken (Gemini 2.5 Flash)
3. A model that changes its mind too easily due to sycophancy (Gemini 3.1 Flash-Lite)

By demonstrating this exact gradient of cognitive failure modes, this benchmark provides precisely the novel, discriminative signal needed to map true progress toward AGI.
