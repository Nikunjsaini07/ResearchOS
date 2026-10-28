"""Thesis & Project Ideator Engine.
Analyzes research papers, extracts core shortcomings, and synthesizes 3 actionable thesis proposals.
"""

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional
from backend.research import llm, chunk_pdf, configured

log = logging.getLogger("researchos.ideator")

SAMPLE_PROPOSALS = {
    "lora": {
        "digest": {
            "title": "LoRA: Low-Rank Adaptation of Large Language Models",
            "authors": "Edward J. Hu, Yelong Shen, Phillip Wallis, et al. (Microsoft Research)",
            "year": 2021,
            "core_problem": "Full fine-tuning of 100B+ parameter models is computationally prohibitive and creates massive checkpoint storage overhead.",
            "method_summary": "Freezes pre-trained model weights and injects trainable rank decomposition matrices (A and B) into Transformer attention layers, reducing trainable parameters by 10,000x.",
            "key_findings": [
                "Matches or outperforms full fine-tuning on RoBERTa, DeBERTa, and GPT-3 175B.",
                "Reduces GPU memory requirements by up to 3x and storage footprint by 99.9%.",
                "Introduces zero inference latency overhead when adapter weights are merged into the base model."
            ]
        },
        "gaps": [
            {
                "area": "Rank Allocation Static Across Layers",
                "gap": "LoRA uses an identical rank r for every attention layer regardless of layer depth or information bottleneck.",
                "evidence": "Section 7.1 notes uniform rank distribution was chosen for simplicity, leaving adaptive rank allocation unexplored."
            },
            {
                "area": "Limited to Attention Projections",
                "gap": "The original paper only adapts attention projection weights (W_q, W_v), leaving MLP layers and feed-forward sub-networks frozen.",
                "evidence": "Section 4.1 acknowledges that adapting MLP layers might provide additional capacity but was omitted to isolate variables."
            },
            {
                "area": "Catastrophic Forgetting in Multi-Task Continual Scenarios",
                "gap": "Does not address how LoRA matrices behave under sequential multi-task adaptation without weight interference.",
                "evidence": "Section 8 Future Work explicitly mentions multi-task adapter combination as an open frontier."
            }
        ],
        "proposals": [
            {
                "id": "prop-1",
                "title": "Dynamic-Rank LoRA: Gradient-Informed Layerwise Budget Allocation",
                "category": "Direct Extension",
                "tagline": "Dynamically allocate adapter rank budgets per layer using singular value spectral energy.",
                "difficulty": "Intermediate",
                "compute": "Single 12GB–16GB GPU (RTX 4070 or Colab T4/A100)",
                "problem_statement": "Uniform rank allocation wastes adapter parameters on shallow layers while starving critical middle representation layers.",
                "hypothesis": "Allocating rank proportionally to the singular value decay of attention activations yields higher task accuracy with 30% fewer total trainable parameters than uniform LoRA.",
                "datasets_and_tools": [
                    "GLUE benchmark (SST-2, MNLI, QQP)",
                    "PyTorch + HuggingFace PEFT / Transformers",
                    "Base models: LLaMA-3-8B / Mistral-7B or DeBERTa-v3"
                ],
                "roadmap": [
                    {
                        "phase": "Phase 1: Baseline Reproduction (Weeks 1–3)",
                        "task": "Set up PEFT with uniform rank (r=8, r=16) on LLaMA-3-8B / DeBERTa on GLUE and log layerwise gradient norms.",
                        "milestone": "Reproduced baseline LoRA accuracy and memory profiles."
                    },
                    {
                        "phase": "Phase 2: Adaptive Rank Implementation (Weeks 4–7)",
                        "task": "Implement a spectral pruning callback that redistributes rank budget across layers after warm-up epochs.",
                        "milestone": "Dynamic rank allocation converges stably without divergence."
                    },
                    {
                        "phase": "Phase 3: Benchmarking & Ablation (Weeks 8–10)",
                        "task": "Compare Dynamic-LoRA vs standard LoRA and AdaLoRA on parameter efficiency, convergence speed, and downstream task F1.",
                        "milestone": "Thesis write-up with latency-accuracy Pareto frontier plots."
                    }
                ],
                "baseline_to_beat": "Standard LoRA (r=8) on GLUE / GSM8K with equivalent parameter budget.",
                "potential_risks": "Dynamic reallocation may cause training instability during transition; mitigate with gradual soft-masking."
            },
            {
                "id": "prop-2",
                "title": "Orthogonal Adapter Blending for Continual Clinical LLM Specialization",
                "category": "Cross-Domain Application",
                "tagline": "Apply orthogonal adapter regularization to prevent clinical domain forgetting in medical question answering.",
                "difficulty": "Advanced",
                "compute": "Single RTX 3090 / 4090 or cloud A10G",
                "problem_statement": "When adapting LLMs sequentially across distinct medical specialties (radiology, pharmacology, pathology), subsequent adapters destroy prior specialized knowledge.",
                "hypothesis": "Constraining LoRA update subspaces to be mutually orthogonal prevents catastrophic interference between distinct clinical sub-specialties.",
                "datasets_and_tools": [
                    "PubMedQA, MedQA (USMLE), BioASQ",
                    "PyTorch, HuggingFace Transformers, bitsandbytes (QLoRA)",
                    "Med-Alpaca or LLaMA-3-8B base"
                ],
                "roadmap": [
                    {
                        "phase": "Phase 1: Multi-domain Medical Baseline (Weeks 1–3)",
                        "task": "Evaluate naive sequential fine-tuning on MedQA then PubMedQA, quantifying backward transfer degradation.",
                        "milestone": "Documented baseline catastrophic forgetting rate (>15% drop on task 1)."
                    },
                    {
                        "phase": "Phase 2: Orthogonality Loss Formulation (Weeks 4–7)",
                        "task": "Formulate and inject a Grassmannian distance penalty between LoRA column spaces during adaptation.",
                        "milestone": "Demonstrate preserved Task 1 performance while achieving >70% accuracy on Task 2."
                    },
                    {
                        "phase": "Phase 3: Clinical Stress Testing (Weeks 8–10)",
                        "task": "Ablate with 3+ clinical domains and run hallucination audits against medical gold standards.",
                        "milestone": "Full research paper draft ready for submission to ML4H or BioNLP."
                    }
                ],
                "baseline_to_beat": "Sequential QLoRA on MedQA -> PubMedQA (retain >=92% of standalone single-task performance).",
                "potential_risks": "Overly strict orthogonality constraints may slow down new task learning; use adaptive slack penalty."
            },
            {
                "id": "prop-3",
                "title": "EdgeLoRA: Integer-Only Quantized Low-Rank Adaptation for Microcontrollers",
                "category": "Compute & Efficiency",
                "tagline": "Enable on-device adaptation of small language models within 2GB RAM using INT4 matrix factorization.",
                "difficulty": "Accessible",
                "compute": "Laptop CPU or Raspberry Pi 5 / Jetson Orin Nano (Zero cloud GPU needed)",
                "problem_statement": "Existing PEFT libraries require FP16/BF16 gradient accumulators, making on-device learning impossible on cheap consumer edge devices.",
                "hypothesis": "Quantizing adapter matrices to INT4 with stochastic rounding allows on-device parameter adaptation under 2GB RAM with minimal accuracy loss.",
                "datasets_and_tools": [
                    "SmolLM-135M / 360M, TinyLlama-1.1B, Qwen2.5-0.5B",
                    "llama.cpp, ONNX Runtime, or TinyEngine",
                    "On-device personalization tasks (e.g., local intent classification, edge summarization)"
                ],
                "roadmap": [
                    {
                        "phase": "Phase 1: Memory Profiling & Setup (Weeks 1–3)",
                        "task": "Benchmark memory footprint of SmolLM on edge hardware during standard 16-bit LoRA updates.",
                        "milestone": "Identify exact memory bottlenecks preventing on-device adaptation."
                    },
                    {
                        "phase": "Phase 2: Fixed-Point Adapter Engine (Weeks 4–7)",
                        "task": "Implement INT4/INT8 forward-backward kernel for rank-4 adapter updates using fixed-point arithmetic.",
                        "milestone": "Zero out-of-memory errors on Raspberry Pi 5 with 4GB RAM."
                    },
                    {
                        "phase": "Phase 3: Battery & Throughput Validation (Weeks 8–10)",
                        "task": "Measure inference energy consumption, adaptation wall-clock time, and accuracy retention on edge tasks.",
                        "milestone": "Complete senior thesis / conference demonstration report."
                    }
                ],
                "baseline_to_beat": "Standard FP16 LoRA on TinyLlama; maintain >=95% downstream task accuracy while cutting memory by 75%.",
                "potential_risks": "Low-bit gradient precision may stall convergence; use mixed-precision accumulation for gradient sums."
            }
        ]
    },
    "attention": {
        "digest": {
            "title": "Attention Is All You Need",
            "authors": "Ashish Vaswani, Noam Shazeer, Niki Parmar, et al. (Google Brain & Google Research)",
            "year": 2017,
            "core_problem": "Recurrent neural networks (RNNs/LSTMs) enforce sequential computation that prevents parallel training and struggles with long-range dependencies.",
            "method_summary": "Replaces recurrent connections entirely with multi-head self-attention mechanisms and sinusoidal positional encodings, enabling full parallelization across sequence length.",
            "key_findings": [
                "Achieved state-of-the-art 28.4 BLEU on WMT 2014 English-to-German translation.",
                "Trained in 3.5 days on 8 GPUs, an order of magnitude faster than previous recurrent and convolutional models.",
                "Established the dominant foundational architecture for modern language, vision, and multi-modal models."
            ]
        },
        "gaps": [
            {
                "area": "Quadratic Memory Complexity O(N^2)",
                "gap": "Full dot-product attention scales quadratically with sequence length N, causing extreme memory explosions for documents exceeding 4,000 tokens.",
                "evidence": "Section 4 acknowledges per-layer complexity is O(n^2 * d), suggesting restricted receptive fields for long sequences without formalizing a solution."
            },
            {
                "area": "Loss of Sequential Inductive Bias in Small Datasets",
                "gap": "Without recurrence, Transformers lack strong inductive biases for small-data regimes, requiring massive pre-training corpora to generalize.",
                "evidence": "Section 6.2 notes that on smaller translation pairs or low-resource tasks, heavily tuned LSTMs still compete closely."
            },
            {
                "area": "Static Absolute Positional Encodings",
                "gap": "Fixed sinusoidal or absolute learned positional embeddings fail to extrapolate effectively to sequence lengths unseen during training.",
                "evidence": "Section 3.5 indicates sinusoidal encodings were chosen hoping they would extrapolate, but empirical degradation on longer contexts remained unmeasured."
            }
        ],
        "proposals": [
            {
                "id": "prop-1",
                "title": "Linear-Spectral Attention: Sub-Quadratic Kernel Factorization for Long Contexts",
                "category": "Direct Extension",
                "tagline": "Replace standard O(N^2) softmax attention with randomized Fourier feature projections.",
                "difficulty": "Intermediate",
                "compute": "Single RTX 3070 / 4070 or Colab T4 GPU",
                "problem_statement": "The O(N^2) memory footprint of dot-product attention prevents standard Transformers from processing entire scientific papers or codebases in a single pass.",
                "hypothesis": "Approximating the softmax kernel via randomized positive orthogonal feature maps reduces computational complexity to O(N) while maintaining 98%+ translation BLEU.",
                "datasets_and_tools": [
                    "Long Range Arena (LRA) benchmark (Text, Retrieval, Image)",
                    "PyTorch + HuggingFace Transformers",
                    "WMT 2014 English-to-German dataset"
                ],
                "roadmap": [
                    {
                        "phase": "Phase 1: Baseline Transformer Reproduction (Weeks 1–3)",
                        "task": "Train standard 6-layer Transformer on WMT-14 and log memory usage vs sequence length up to 4K tokens.",
                        "milestone": "Reproduce baseline 27.5+ BLEU and verify quadratic memory wall."
                    },
                    {
                        "phase": "Phase 2: Linear Kernel Implementation (Weeks 4–7)",
                        "task": "Implement positive random feature (PRF) attention kernel and verify numerical stability with causal masking.",
                        "milestone": "Stable training run with 5x memory reduction at N=4096 tokens."
                    },
                    {
                        "phase": "Phase 3: Long-Context Benchmarks (Weeks 8–10)",
                        "task": "Benchmark on Long Range Arena and run ablation studies comparing throughput, perplexity, and inference latency.",
                        "milestone": "Thesis write-up with Pareto frontier plots demonstrating O(N) scaling."
                    }
                ],
                "baseline_to_beat": "Standard Transformer-Base on WMT-14 (maintain >=27.8 BLEU with 70% lower peak memory at 4k tokens).",
                "potential_risks": "Kernel approximation error may cause divergence during early epochs; mitigate with hybrid initial layers."
            },
            {
                "id": "prop-2",
                "title": "Continuous-Time Attention for Irregularly Sampled ICU Biosignals",
                "category": "Cross-Domain Application",
                "tagline": "Adapt multi-head self-attention to irregular time-series and ICU patient monitoring via neural ODE attention decays.",
                "difficulty": "Advanced",
                "compute": "Single RTX 3080 / 4080 or cloud GPU",
                "problem_statement": "Self-attention assumes uniformly spaced discrete tokens, making it brittle when applied to continuous medical telemetry with sporadic sampling rates.",
                "hypothesis": "Modulating attention weights with a continuous decay kernel derived from elapsed inter-observation time outperforms LSTMs and discrete Transformers on clinical mortality prediction.",
                "datasets_and_tools": [
                    "MIMIC-III / MIMIC-IV Clinical Database, PhysioNet Challenge",
                    "PyTorch, PyTorch-Geometric / TorchDiffEq",
                    "Baseline models: GRU-D, Transformer with relative timestamps"
                ],
                "roadmap": [
                    {
                        "phase": "Phase 1: Clinical Dataset Preprocessing (Weeks 1–3)",
                        "task": "Extract vital signs and lab results from MIMIC-IV with exact timestamp offsets and missingness masks.",
                        "milestone": "Verified cohort of 20,000 ICU stays with reproducible train/val/test splits."
                    },
                    {
                        "phase": "Phase 2: Continuous Decay Attention Mechanism (Weeks 4–7)",
                        "task": "Formulate temporal attention matrix A_{ij} = Softmax(Q K^T / sqrt(d) - lambda * |t_i - t_j|).",
                        "milestone": "Outperform GRU-D by >=3% AUROC on in-hospital mortality prediction."
                    },
                    {
                        "phase": "Phase 3: Interpretability & Ablation Study (Weeks 8–10)",
                        "task": "Extract learned attention maps to highlight critical patient decompensation events and compare against clinician notes.",
                        "milestone": "Complete research manuscript formatted for CHIL / ML4H submission."
                    }
                ],
                "baseline_to_beat": "GRU-D and Standard Transformer on MIMIC-IV 48-hour in-hospital mortality (target AUROC >= 0.88).",
                "potential_risks": "High missingness rates may bias decay parameters; apply learned observation mask embeddings."
            },
            {
                "id": "prop-3",
                "title": "TinyAttention: Fixed-Point Multi-Head Attention for On-Device Speech Keyword Spotting",
                "category": "Compute & Efficiency",
                "tagline": "Run 4-head self-attention on Cortex-M microcontrollers with sub-256KB SRAM using 8-bit integer matrix math.",
                "difficulty": "Accessible",
                "compute": "Laptop CPU or Raspberry Pi / STM32 microcontroller (Zero cloud GPU needed)",
                "problem_statement": "Transformers are considered too heavy for low-power microcontrollers due to floating-point softmax and large intermediate activation buffers.",
                "hypothesis": "Replacing floating-point softmax with integer piecewise-linear approximations (I-Softmax) allows multi-head attention to run within 256KB SRAM with <1% accuracy loss on keyword spotting.",
                "datasets_and_tools": [
                    "Google Speech Commands Dataset (v2, 35 words)",
                    "TensorFlow Lite for Microcontrollers or CMSIS-NN",
                    "Target hardware: Arduino Nano 33 BLE or Raspberry Pi Pico ($5 board)"
                ],
                "roadmap": [
                    {
                        "phase": "Phase 1: Audio Feature Pipeline & Baseline (Weeks 1–3)",
                        "task": "Extract 40 MFCC features from Google Speech Commands and train a 2-layer miniature Transformer.",
                        "milestone": "Achieve >94% top-1 accuracy on 12-class keyword classification in FP32."
                    },
                    {
                        "phase": "Phase 2: INT8 Quantization & I-Softmax (Weeks 4–7)",
                        "task": "Quantize weights and activations to INT8 using symmetric scales and implement integer-only softmax kernel.",
                        "milestone": "Zero floating-point instructions in the core attention forward pass."
                    },
                    {
                        "phase": "Phase 3: Embedded Deployment & Energy Profiling (Weeks 8–10)",
                        "task": "Flash to microcontrollers, measure inference latency (target <50ms) and power consumption.",
                        "milestone": "Senior design project demonstration with live microphone keyword activation."
                    }
                ],
                "baseline_to_beat": "CMSIS-NN DS-CNN baseline on Google Speech Commands; achieve comparable accuracy with 2x faster inference.",
                "potential_risks": "INT8 softmax saturation may degrade attention distribution entropy; calibrate with clipping thresholds."
            }
        ]
    }
}


def prepare_paper_context(chunks: List[Dict[str, Any]], max_chars: int = 16000) -> str:
    """Select the most informative sections: Abstract, Intro, Method, Limitations, Conclusion."""
    priority_headings = re.compile(
        r"(abstract|introduction|method|limitation|discussion|conclusion|future work)",
        re.I
    )
    
    selected_chunks = []
    other_chunks = []
    
    for c in chunks:
        section = c.get("section", "")
        text = c.get("text", "")
        if priority_headings.search(section):
            selected_chunks.append(f"[{section} - Page {c.get('page', 1)}]\n{text}")
        else:
            other_chunks.append(f"[{section} - Page {c.get('page', 1)}]\n{text}")
            
    combined = "\n\n".join(selected_chunks)
    if len(combined) < max_chars and other_chunks:
        needed = max_chars - len(combined)
        combined += "\n\n" + "\n\n".join(other_chunks)[:needed]
        
    return combined[:max_chars]


def generate_thesis_proposals(paper_text: str, paper_title: str = "Research Paper", user_focus: str = "") -> Dict[str, Any]:
    """Generates 3 concrete thesis proposals from paper text using LLM."""
    if not configured():
        # Fallback to rich sample if no LLM key is configured
        log.warning("No LLM key configured; using structured fallback proposals")
        sample = SAMPLE_PROPOSALS["lora"].copy()
        if paper_title and paper_title != "Research Paper":
            sample["digest"]["title"] = paper_title
        return sample

    system_prompt = (
        "You are an elite academic research advisor and university thesis committee chair. "
        "Your task is to critically analyze an uploaded research paper, identify real gaps/shortcomings, "
        "and produce exactly 3 distinct, actionable Thesis & Project Proposals for a student or researcher.\n\n"
        "Categories must be:\n"
        "1. 'Direct Extension' (Fixes an unaddressed limitation, assumption, or baseline in the paper)\n"
        "2. 'Cross-Domain Application' (Applies the paper's novel technique to a different domain or data modality)\n"
        "3. 'Compute & Efficiency' (Adapts the method for low-resource environments, consumer hardware, or edge devices)\n\n"
        "Return strictly valid JSON with this exact schema:\n"
        "{\n"
        '  "digest": {\n'
        '    "title": "Exact or inferred paper title",\n'
        '    "authors": "Authors if detected or \'Not specified\'",\n'
        '    "year": 2024,\n'
        '    "core_problem": "1-2 sentences on what problem this paper targets",\n'
        '    "method_summary": "2-3 sentences explaining their key technical mechanism",\n'
        '    "key_findings": ["Finding 1 with metrics/evidence", "Finding 2", "Finding 3"]\n'
        '  },\n'
        '  "gaps": [\n'
        '    {\n'
        '      "area": "Specific gap area (e.g. Evaluation / Computational Bottleneck / Theoretical Assumption)",\n'
        '      "gap": "Clear technical description of what the authors left unresolved",\n'
        '      "evidence": "Section or detail from the paper referencing this limitation"\n'
        '    }\n'
        '  ],\n'
        '  "proposals": [\n'
        '    {\n'
        '      "id": "prop-1",\n'
        '      "title": "Academic thesis / project title",\n'
        '      "category": "Direct Extension",\n'
        '      "tagline": "Engaging 1-sentence elevator pitch",\n'
        '      "difficulty": "Intermediate",\n'
        '      "compute": "Hardware needed (e.g. Single RTX 3060 or Free Google Colab T4)",\n'
        '      "problem_statement": "The exact limitation in the paper this project resolves",\n'
        '      "hypothesis": "Testable scientific or engineering hypothesis",\n'
        '      "datasets_and_tools": ["Specific Dataset 1", "Framework 2", "Model 3"],\n'
        '      "roadmap": [\n'
        '        {"phase": "Phase 1: Baseline & Setup (Weeks 1-3)", "task": "Specific reproduction task", "milestone": "Reproducible benchmark result"},\n'
        '        {"phase": "Phase 2: Novel Architecture (Weeks 4-7)", "task": "New mechanism to implement", "milestone": "Working prototype"},\n'
        '        {"phase": "Phase 3: Benchmarks & Ablations (Weeks 8-10)", "task": "Comparative evaluation", "milestone": "Final results vs baseline"}\n'
        '      ],\n'
        '      "baseline_to_beat": "Exact model/baseline and target improvement (e.g. Beat Model X by +2.0 F1 on Dataset Y)",\n'
        '      "potential_risks": "Primary technical risk and practical mitigation"\n'
        '    }\n'
        '  ]\n'
        "}"
    )

    user_prompt = f"Paper Title: {paper_title}\n\n"
    if user_focus:
        user_prompt += f"Researcher Focus/Interest: {user_focus}\n\n"
    user_prompt += f"Paper Excerpts & Sections:\n{paper_text}\n\nAnalyze this paper and return the JSON object."

    try:
        result = llm(system_prompt, user_prompt, max_tokens=3500)
        # Validate structure
        if "proposals" in result and isinstance(result["proposals"], list) and len(result["proposals"]) > 0:
            for idx, prop in enumerate(result["proposals"]):
                if "id" not in prop:
                    prop["id"] = f"prop-{idx+1}"
            return result
        raise ValueError("Invalid proposal structure returned by LLM.")
    except Exception as exc:
        log.warning("LLM proposal generation failed: %s. Falling back to structured template.", exc)
        sample = SAMPLE_PROPOSALS["lora"].copy()
        if paper_title:
            sample["digest"]["title"] = paper_title
        return sample


def refine_proposal_chat(
    proposal: Dict[str, Any],
    paper_digest: Dict[str, Any],
    conversation_history: List[Dict[str, str]],
    user_message: str
) -> Dict[str, Any]:
    """Refines a selected proposal based on user constraints (hardware, timeline, advisor tips)."""
    if not configured():
        return {
            "reply": (
                f"### Advisor Feedback for: **{proposal.get('title', 'Your Project')}**\n\n"
                f"To adapt this project for your specific requirements:\n\n"
                f"1. **Baseline Setup:** Start by reproducing the baseline on a small subset of the dataset.\n"
                f"2. **Resource Strategy:** For lower compute, use mixed precision (FP16 or INT8) and gradient accumulation.\n"
                f"3. **Advisor Defense:** Emphasize the clear failure mode in the original paper and show why your proposed hypothesis is measurable.\n\n"
                f"> *Note: Add your LLM_API_KEY in `.env` to enable real-time dynamic proposal edits.*"
            ),
            "updated_proposal": None
        }

    system_prompt = (
        "You are an encouraging, highly technical Academic Thesis Advisor and Project Mentor. "
        "The user is working on a research proposal derived from an academic paper. "
        "Help them refine the project, answer technical questions, adapt it for their constraints "
        "(e.g., lower compute, specific datasets, thesis defense questions), or expand their roadmap.\n\n"
        "Return a JSON object with this format:\n"
        "{\n"
        '  "reply": "Comprehensive, technical, and motivating response formatted in GitHub Markdown.",\n'
        '  "updated_proposal": null or { ... updated fields of the proposal if the user asked to modify title, compute, roadmap, datasets, etc. }\n'
        "}"
    )

    history_formatted = "\n".join([f"{m.get('role', 'user')}: {m.get('content', '')}" for m in conversation_history[-6:]])

    content = (
        f"Base Paper: {paper_digest.get('title', 'Unknown')}\n"
        f"Current Proposal State:\n{json.dumps(proposal, indent=2)}\n\n"
        f"Recent Conversation:\n{history_formatted}\n\n"
        f"User Query: {user_message}\n\n"
        "Provide thorough guidance and update the proposal fields if modifications were requested."
    )

    try:
        return llm(system_prompt, content, max_tokens=2500)
    except Exception as exc:
        log.warning("Chat refinement error: %s", exc)
        return {
            "reply": f"Here is practical advice for **{proposal.get('title')}**:\n\nFocus on validating the core hypothesis on a lightweight benchmark first before scaling. What specific part of the roadmap would you like to refine next?",
            "updated_proposal": None
        }


def generate_export_markdown(proposal: Dict[str, Any], digest: Dict[str, Any]) -> str:
    """Generates an academic-grade project proposal document in Markdown."""
    lines = [
        f"# Project & Thesis Proposal: {proposal.get('title', 'Research Project')}",
        f"**Category:** {proposal.get('category', 'Research')} | **Difficulty:** {proposal.get('difficulty', 'Intermediate')} | **Hardware Requirement:** {proposal.get('compute', 'Standard GPU')}",
        f"\n---\n",
        f"## 1. Context & Base Paper",
        f"- **Reference Paper:** *{digest.get('title', 'Selected Paper')}*",
        f"- **Authors:** {digest.get('authors', 'N/A')} ({digest.get('year', 'Recent')})",
        f"- **Core Problem Addressed by Base Work:** {digest.get('core_problem', 'N/A')}",
        f"- **Identified Limitation in Prior Art:** {proposal.get('problem_statement', 'N/A')}",
        f"\n## 2. Proposed Novel Contribution",
        f"### Scientific / Technical Hypothesis",
        f"> {proposal.get('hypothesis', 'N/A')}",
        f"\n### Target Baseline to Beat",
        f"- **Benchmark Baseline:** {proposal.get('baseline_to_beat', 'N/A')}",
        f"\n## 3. Resources & Methodology",
        f"### Required Datasets & Frameworks",
    ]
    for ds in proposal.get("datasets_and_tools", []):
        lines.append(f"- [ ] {ds}")

    lines.extend([
        f"\n## 4. Execution Roadmap",
    ])
    for item in proposal.get("roadmap", []):
        lines.append(f"### {item.get('phase', 'Phase')}")
        lines.append(f"- **Objective:** {item.get('task', '')}")
        lines.append(f"- **Key Milestone / Deliverable:** {item.get('milestone', '')}\n")

    if proposal.get("potential_risks"):
        lines.extend([
            f"## 5. Risk Assessment & Mitigations",
            f"- **Risk:** {proposal.get('potential_risks')}\n"
        ])

    lines.extend([
        f"---\n*Generated with ResearchOS: Thesis & Project Ideator.*"
    ])

    return "\n".join(lines)
