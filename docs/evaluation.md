# Evaluating Your RAG Application

This guide helps you understand how to evaluate your RAG (Retrieval-Augmented Generation) application. Don't worry if you're new to this—we'll walk through everything step by step.

## Why Evaluate?

Before deploying your RAG application, you need to know if it actually works well. Evaluation helps you answer questions like:

- **Is my chatbot giving correct answers?**
- **Does it find the right documents?**
- **Is it making things up (hallucinating)?**
- **How does it compare to other approaches?**

Without evaluation, you're flying blind. With it, you can confidently improve your application.

## Quick Start

### 1. Install the Evaluation CLI

The `rag-eval` CLI helps you find and manage evaluation datasets:

```bash
# From your rag-facile workspace
cd my-rag-app
uv pip install -e apps/rag-eval
```

### 2. Explore Available Datasets

See what evaluation datasets are available:

```bash
# List known dataset sources
rag-eval sources

# Search for French QA datasets
rag-eval search hf "french QA"

# Browse official French government datasets
rag-eval search agent-public

# Browse preference datasets from Compar:IA
rag-eval search comparia
```

## Understanding Evaluation Datasets

### What's in an Evaluation Dataset?

An evaluation dataset typically contains:

| Field | Description | Example |
|-------|-------------|---------|
| `question` | What a user might ask | "Quels sont les délais pour une demande de carte d'identité?" |
| `ground_truth` | The correct answer | "Le délai moyen est de 3 à 4 semaines..." |
| `context` | (Optional) Relevant documents | Text from service-public.fr |

### Key Dataset Sources

#### AgentPublic (MediaTech Collection)
Official French government datasets, pre-processed and ready to use:

- **`AgentPublic/legi`** - French legislation
- **`AgentPublic/travail-emploi`** - Labor code and employment
- **`AgentPublic/service-public`** - Public service information

```bash
# Explore all AgentPublic datasets
rag-eval search agent-public
```

#### Compar:IA (Preference Data)
Real user interactions comparing AI models, from the French Ministry of Culture:

- **`ministere-culture/comparia-conversations`** - 289k+ real Q&A conversations
- **`ministere-culture/comparia-votes`** - 97k+ user preferences
- **`ministere-culture/comparia-reactions`** - 59k+ message-level reactions

```bash
# Explore Compar:IA datasets
rag-eval search comparia
```

## Basic Evaluation Workflow

Here's a simple workflow to evaluate your RAG application:

### Step 1: Choose Your Dataset

Pick a dataset that matches your use case:

```bash
# For legal/administrative questions
rag-eval search hf "french administrative" --sort downloads

# For general French QA
rag-eval search hf "french QA" -n 20
```

### Step 2: Load the Dataset

Using the HuggingFace `datasets` library:

```python
from datasets import load_dataset

# Load a dataset
dataset = load_dataset("AgentPublic/service-public")

# See what's inside
print(dataset)
print(dataset["train"][0])  # First example
```

### Step 3: Run Your RAG Pipeline

For each question in the dataset, run your RAG application:

```python
results = []
for example in dataset["train"]:
    question = example["question"]
    
    # Your RAG pipeline
    answer = your_rag_pipeline(question)
    
    results.append({
        "question": question,
        "expected": example["ground_truth"],
        "actual": answer,
    })
```

### Step 4: Measure Quality

Compare your answers to the ground truth:

```python
# Simple exact match (strict)
exact_matches = sum(1 for r in results if r["expected"] == r["actual"])
accuracy = exact_matches / len(results)
print(f"Exact match accuracy: {accuracy:.1%}")

# For more nuanced evaluation, use semantic similarity or LLM-as-judge
```

## What to Measure

### Core Metrics

| Metric | What it Measures | Good For |
|--------|------------------|----------|
| **Accuracy** | Correct answers / Total questions | Overall quality |
| **Retrieval Recall** | Did we find the right documents? | Search quality |
| **Faithfulness** | Does the answer match the sources? | Detecting hallucinations |
| **Latency** | Response time | User experience |

### French Government Specific

For sovereign AI applications, also consider:

| Metric | What it Measures |
|--------|------------------|
| **Sovereignty** | Only uses authorized sources (*.gouv.fr) |
| **Energy Score** | Carbon footprint of inference |
| **Language Quality** | Correct French grammar and style |

## Next Steps

### Learn More About Evaluation

- [Letta Evals](https://github.com/letta-ai/letta-evals) - Framework for testing AI agents
- [MTEB Leaderboard](https://huggingface.co/spaces/mteb/leaderboard) - Embedding model benchmarks
- [BEIR Benchmark](https://github.com/beir-cellar/beir) - Information retrieval benchmarks

### Coming Soon

- **Synthetic dataset generation** - Create test data from your own documents
- **Automated evaluation pipelines** - CI/CD integration for continuous testing
- **Custom graders** - Domain-specific evaluation metrics

## Getting Help

- **Questions?** Open an issue on [GitHub](https://github.com/etalab-ia/rag-facile/issues)
- **Found a bug?** We welcome contributions! See [CONTRIBUTING.md](../CONTRIBUTING.md)
