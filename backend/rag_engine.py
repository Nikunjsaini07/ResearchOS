"""Pure, robust Research Paper RAG Engine.
Handles: PDF upload -> extraction -> hybrid search -> grounded Q&A with page/section citations.
"""

import json
import logging
import math
import os
import re
from collections import Counter
from typing import Any, Dict, List, Optional
from sqlalchemy import select, delete

from backend.db import Paper, Chunk, Message
from backend.research import chunk_pdf, llm, tokens, STOP

log = logging.getLogger("researchos.rag")

# 2 Complete, Realistic Sample Papers for instant 1-click exploration
SAMPLE_PAPERS: Dict[str, Dict[str, Any]] = {
    "attention": {
        "title": "Attention Is All You Need",
        "authors": "Ashish Vaswani, Noam Shazeer, Niki Parmar, Jakob Uszkoreit, Llion Jones, Aidan N. Gomez, Łukasz Kaiser, Illia Polosukhin",
        "year": 2017,
        "abstract": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks that include an encoder and a decoder. The best performing models also connect the encoder and decoder through an attention mechanism. We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely. Experiments on two machine translation tasks show these models to be superior in quality while being more parallelizable and requiring significantly less time to train.",
        "suggested_questions": [
            "What is the mathematical formula for Scaled Dot-Product Attention?",
            "How does Multi-Head Attention differ from single-head attention?",
            "What results did the Transformer achieve on the WMT 2014 translation benchmark?",
            "Why did the authors replace recurrence with positional encodings?"
        ],
        "chunks": [
            {
                "page": 1,
                "section": "Abstract",
                "text": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks that include an encoder and a decoder. We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely. On the WMT 2014 English-to-German translation task, the big model achieves 28.4 BLEU, improving over the existing best results by over 2 BLEU. On the English-to-French translation task, our model establishes a new single-model state-of-the-art BLEU score of 41.8 after training for 3.5 days on eight GPUs."
            },
            {
                "page": 2,
                "section": "1 Introduction",
                "text": "Recurrent neural networks, particularly LSTM and gated recurrent networks, have been firmly established as state of the art approaches in sequence modeling. Recurrent models typically factor computation along the symbol positions of the input and output sequences. Aligning the positions to steps in computation time, they generate a sequence of hidden states h_t, as a function of the previous hidden state h_{t-1} and the input for position t. This inherently sequential nature precludes parallelization within training examples, which becomes critical at longer sequence lengths, as memory constraints limit batching across examples."
            },
            {
                "page": 3,
                "section": "3.1 Encoder and Decoder Stacks",
                "text": "The encoder is composed of a stack of N = 6 identical layers. Each layer has two sub-layers. The first is a multi-head self-attention mechanism, and the second is a simple, position-wise fully connected feed-forward network. We employ a residual connection around each of the two sub-layers, followed by layer normalization. That is, the output of each sub-layer is LayerNorm(x + Sublayer(x)). To facilitate these residual connections, all sub-layers in the model produce outputs of dimension d_model = 512. The decoder is also composed of a stack of N = 6 identical layers with an additional third sub-layer that performs multi-head attention over the encoder output."
            },
            {
                "page": 4,
                "section": "3.2 Attention: Scaled Dot-Product Attention",
                "text": "An attention function can be described as mapping a query and a set of key-value pairs to an output, where the query, keys, values, and output are all vectors. The output is computed as a weighted sum of the values, where the weight assigned to each value is computed by a compatibility function of the query with the corresponding key. We compute the dot products of the query with all keys, divide each by sqrt(d_k), and apply a softmax function to obtain the weights on the values. In practice, we compute the attention function on a set of queries simultaneously, packed into a matrix Q: Attention(Q, K, V) = softmax(Q K^T / sqrt(d_k)) V."
            },
            {
                "page": 5,
                "section": "3.2.2 Multi-Head Attention",
                "text": "Instead of performing a single attention function with d_model-dimensional queries, keys and values, we found it beneficial to linearly project the queries, keys and values h times with different, learned linear projections to d_k, d_k and d_v dimensions, respectively. MultiHead(Q, K, V) = Concat(head_1, ..., head_h) W^O where head_i = Attention(Q W_i^Q, K W_i^K, V W_i^V). In this work we employ h = 8 parallel attention layers, or heads. For each of these we use d_k = d_v = d_model / h = 64. Due to the reduced dimension of each head, the total computational cost is similar to that of single-head attention with full dimensionality."
            },
            {
                "page": 6,
                "section": "3.5 Positional Encoding",
                "text": "Since our model contains no recurrence and no convolution, in order for the model to make use of the order of the sequence, we must inject some information about the relative or absolute positions of the tokens in the sequence. To this end, we add 'positional encodings' to the input embeddings at the bottoms of the encoder and decoder stacks. We use sine and cosine functions of different frequencies: PE(pos, 2i) = sin(pos / 10000^(2i/d_model)) and PE(pos, 2i+1) = cos(pos / 10000^(2i/d_model)), where pos is the position and i is the dimension."
            },
            {
                "page": 8,
                "section": "5.1 Training Data and Batching",
                "text": "We trained on the standard WMT 2014 English-German dataset consisting of about 4.5 million sentence pairs. Sentences were encoded using byte-pair encoding, which has a shared source-target vocabulary of about 37000 tokens. For English-French, we used the significantly larger WMT 2014 English-French dataset consisting of 36M sentences. Each training batch contained a set of sentence pairs containing approximately 25000 source tokens and 25000 target tokens."
            },
            {
                "page": 9,
                "section": "6.1 Machine Translation Results",
                "text": "On the WMT 2014 English-to-German task, the big transformer model outperforms the best previously reported models (including ensembles) by more than 2.0 BLEU, establishing a new state-of-the-art BLEU score of 28.4. On the WMT 2014 English-to-French task, our big model achieves a BLEU score of 41.0, outperforming all previously published single models at 1/4 the training cost of the previous state-of-the-art model."
            },
            {
                "page": 10,
                "section": "7 Conclusion and Future Work",
                "text": "In this work, we presented the Transformer, the first sequence transduction model based entirely on attention, replacing the recurrent layers most commonly used in encoder-decoder architectures with multi-headed self-attention. For translation tasks, the Transformer can be trained significantly faster than architectures based on recurrent or convolutional layers. We plan to extend the Transformer to problems involving input and output modalities other than text, such as images, audio and video. Another goal is investigating local, restricted attention mechanisms to efficiently handle very large inputs and outputs."
            }
        ]
    },
    "lora": {
        "title": "LoRA: Low-Rank Adaptation of Large Language Models",
        "authors": "Edward J. Hu, Yelong Shen, Phillip Wallis, Zeyuan Allen-Zhu, Yuanzhi Li, Shean Wang, Lu Wang, Weizhu Chen (Microsoft)",
        "year": 2021,
        "abstract": "An important paradigm of natural language processing consists of large-scale pre-training on general domain data and adaptation to specific tasks. Full fine-tuning becomes increasingly prohibitive as models scale to hundreds of billions of parameters. We propose Low-Rank Adaptation, or LoRA, which freezes the pre-trained model weights and injects trainable rank decomposition matrices into each layer of the Transformer architecture, greatly reducing the number of trainable parameters for downstream tasks.",
        "suggested_questions": [
            "What is the mathematical formulation of LoRA rank decomposition?",
            "How much does LoRA reduce trainable parameters and GPU memory?",
            "Does LoRA add any latency overhead during inference?",
            "On which Transformer weights is LoRA typically applied?"
        ],
        "chunks": [
            {
                "page": 1,
                "section": "Abstract",
                "text": "We propose Low-Rank Adaptation, or LoRA, which freezes the pre-trained model weights and injects trainable rank decomposition matrices into each layer of the Transformer architecture, greatly reducing the number of trainable parameters for downstream tasks. Compared to GPT-3 175B fine-tuned with Adam, LoRA can reduce the number of trainable parameters by 10,000 times and the GPU memory requirement by 3 times. LoRA performs on-par or better than fine-tuning in model quality on RoBERTa, DeBERTa, GPT-2, and GPT-3, despite having fewer trainable parameters, a higher training throughput, and, unlike adapters, no additional inference latency."
            },
            {
                "page": 2,
                "section": "1 Introduction",
                "text": "Many applications in natural language processing rely on adapting one large-scale, pre-trained language model to multiple downstream tasks. This adaptation is typically done via fine-tuning, which updates all the parameters of the pre-trained model. The major downside of fine-tuning is that the new model contains as many parameters as the original model. For instance, storing independent 175B checkpoint copies for each downstream task is prohibitively expensive. We take inspiration from Li et al. (2018a); Aghajanyan et al. (2020) which show that the learned over-parametrized models in fact reside on a low intrinsic dimension."
            },
            {
                "page": 3,
                "section": "4.1 Low-Rank Parameterized Update Matrices",
                "text": "A neural network contains many dense layers which perform matrix multiplication. For a pre-trained weight matrix W_0 in R^{d x k}, we constrain its update by representing the latter with a low-rank decomposition W_0 + Delta W = W_0 + B A, where B in R^{d x r}, A in R^{r x k}, and the rank r << min(d, k). During training, W_0 is frozen and does not receive gradient updates, while A and B contain trainable parameters. We use a random Gaussian initialization for A and zero for B, so Delta W = B A is zero at the beginning of training. We then scale Delta W by alpha / r, where alpha is a constant hyperparameter."
            },
            {
                "page": 4,
                "section": "4.2 Applying LoRA to Transformer",
                "text": "In principle, we can apply LoRA to any subset of weight matrices in a neural network to replace their parameter updates. In a Transformer architecture, there are four weight matrices in the self-attention module (W_q, W_k, W_v, W_o) and two in the MLP module. We treat W_q (or W_k, W_v) as a single matrix of dimension d_model x d_model, even though the output is typically sliced into attention heads. We limit our study to only adapting the attention weights for downstream tasks and freeze the MLP modules for simplicity and parameter efficiency. We find that adapting both W_q and W_v yields the best performance."
            },
            {
                "page": 6,
                "section": "5.1 Baselines and Models",
                "text": "We evaluate LoRA on RoBERTa (Liu et al., 2019), DeBERTa (He et al., 2021), GPT-2 (Radford et al., 2019), and GPT-3 175B (Brown et al., 2020). Our tasks range from natural language understanding (GLUE benchmark) to natural language generation (WikiSQL and SAMSum). We compare against full fine-tuning, prefix tuning, series adapters (Houlsby et al.), and parallel adapters. On GPT-3 175B, LoRA matches or exceeds full fine-tuning performance across all datasets while adapting only 0.01% of parameters."
            },
            {
                "page": 7,
                "section": "6.1 No Additional Inference Latency",
                "text": "When deploying in production, we can explicitly compute and store W = W_0 + B A and perform inference as usual. Since W_0 and Delta W = B A are both in R^{d x k}, we can simply add them together. When switching to another downstream task, we can recover W_0 by subtracting B A and then adding a different B' A', a quick operation with minimal memory overhead. Crucially, this means that LoRA introduces zero additional inference latency compared to a fully fine-tuned model, unlike adapter layers that add serial FLOPs."
            },
            {
                "page": 9,
                "section": "7.1 Which Weight Matrices in Transformer Should We Adapt?",
                "text": "Setting a parameter budget of 18M on GPT-3, we find that adapting both W_q and W_v results in the highest performance across all tasks. Adapting all four attention matrices (W_q, W_k, W_v, W_o) yields similar performance. Adapting only W_q or only W_k leads to noticeably lower accuracy, suggesting that projecting the query and value matrices captures the primary adaptation subspace."
            },
            {
                "page": 11,
                "section": "8 Conclusion",
                "text": "Fine-tuning enormous language models is prohibitive due to storage and deployment hardware costs. LoRA is an efficient adaptation method that introduces no inference latency and does not reduce input sequence length, while retaining high model performance. It enables quick task-switching when serving models as a service by sharing the vast majority of parameters."
            }
        ]
    }
}


def search_chunks(chunks: List[Any], query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """Retrieves top_k chunks using term frequency overlap + BM25-style scoring."""
    q_tokens = [t for t in tokens(query) if t not in STOP]
    if not q_tokens:
        # Fallback to general tokens
        q_tokens = tokens(query)[:8]
    if not q_tokens:
        return []

    q_counts = Counter(q_tokens)
    scored_results = []

    priority_sections = re.compile(
        r"(abstract|method|architecture|results?|experiments?|conclusion)",
        re.I
    )

    for c in chunks:
        # c can be dict or Chunk model
        text = c["text"] if isinstance(c, dict) else c.text
        page = c["page"] if isinstance(c, dict) else c.page
        section = c["section"] if isinstance(c, dict) else c.section
        chunk_id = c.get("id", f"chk-{page}") if isinstance(c, dict) else c.id

        c_tokens = tokens(text)
        if not c_tokens:
            continue
        c_counts = Counter(c_tokens)

        # Term overlap with frequency dampening
        overlap = sum(min(q_counts[t], c_counts.get(t, 0)) for t in q_tokens)
        if overlap == 0:
            continue

        # Lexical score normalized by log length
        score = overlap / (1.0 + math.log(max(10, len(c_tokens))))

        # Section relevance boost
        if priority_sections.search(section):
            score *= 1.3

        # Exact phrase bonus
        if query.lower() in text.lower():
            score *= 1.5

        snippet = " ".join(text.split())
        if len(snippet) > 280:
            snippet = snippet[:280] + "…"

        scored_results.append({
            "chunk_id": str(chunk_id),
            "page": page,
            "section": section,
            "snippet": snippet,
            "full_text": text,
            "score": round(score, 4),
        })

    scored_results.sort(key=lambda x: x["score"], reverse=True)
    return scored_results[:top_k]


def build_rag_answer(
    paper_title: str,
    question: str,
    retrieved_chunks: List[Dict[str, Any]],
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> str:
    """Generates a grounded answer from retrieved chunks using the configured LLM."""
    if not retrieved_chunks:
        return (
            "I could not find relevant sections in the uploaded paper to answer this question. "
            "Please try rephrasing or asking about a topic covered in the document."
        )

    # Build context string with explicit source tags
    context_parts = []
    for idx, c in enumerate(retrieved_chunks, 1):
        context_parts.append(
            f"--- [SOURCE {idx} | Page {c['page']}, Section: {c['section']}] ---\n{c['full_text']}"
        )
    context_text = "\n\n".join(context_parts)

    system_prompt = (
        "You are an expert research paper AI assistant. "
        "Your mission is to answer questions strictly and accurately based on the provided research paper excerpts.\n\n"
        "Instructions:\n"
        "1. Direct & Grounded: Answer the question clearly, citing specific facts from the sources.\n"
        "2. Citations: When stating key findings or formulas, reference the page or section like **[Page X]** or **[Section Y]**.\n"
        "3. Concise Structure: Use bolding for key terms and bullet points where helpful.\n"
        "4. Honesty: If the provided excerpts do not mention an aspect of the question, explicitly state that it is not covered in the excerpts."
    )

    history_str = ""
    if conversation_history:
        recent = conversation_history[-4:]
        for msg in recent:
            role = "User" if msg.get("role") == "user" else "Assistant"
            history_str += f"{role}: {msg.get('content')}\n"

    user_prompt = (
        f"Research Paper Title: {paper_title}\n\n"
        f"Evidence Excerpts from Paper:\n{context_text}\n\n"
    )
    if history_str:
        user_prompt += f"Recent Conversation:\n{history_str}\n\n"
    user_prompt += f"Question: {question}\n\nProvide a clear, grounded answer:"

    try:
        raw_answer = llm(system_prompt, user_prompt, max_tokens=1500)
        if isinstance(raw_answer, dict):
            # If the LLM returned JSON or choice
            answer_text = raw_answer.get("answer") or raw_answer.get("text") or str(raw_answer)
        else:
            answer_text = str(raw_answer).strip()

        # Clean reasoning tags if any
        answer_text = re.sub(r"<think>[\s\S]*?</think>", "", answer_text).strip()
        return answer_text or "No answer could be synthesized from the provided evidence."
    except Exception as exc:
        log.warning("LLM generation failed: %s. Falling back to excerpt compilation.", exc)
        top = retrieved_chunks[0]
        return (
            f"**From Page {top['page']} ({top['section']}):**\n\n"
            f"{top['full_text']}\n\n"
            f"*(AI synthesis temporarily unavailable; extracted directly from paper)*"
        )

