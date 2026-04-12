# train.py - SmolLM2-1.7B FULL FP32 (No 4-bit)
import os
import json
import torch
from datasets import load_dataset, Dataset, concatenate_datasets
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
)
from trl import SFTTrainer
from peft import LoraConfig, get_peft_model

# ============================================
# SETUP - Use /tmp/ for space
# ============================================
CACHE_DIR = "/tmp/huggingface_cache"
os.makedirs(CACHE_DIR, exist_ok=True)
os.environ["HF_HOME"] = CACHE_DIR

MODEL_NAME = "HuggingFaceTB/SmolLM2-1.7B"
OUTPUT_DIR = "./smollm2-sft-identity"

# ============================================
# LOAD MODEL - FP32, No Quantization
# ============================================
print("Loading raw SmolLM2-1.7B (FP32, full precision)...")
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    torch_dtype=torch.float32,
    device_map="cpu",
    low_cpu_mem_usage=True
)
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
tokenizer.pad_token = tokenizer.eos_token

# ============================================
# LoRA - Efficient fine-tuning
# ============================================
lora_config = LoraConfig(
    r=8,
    lora_alpha=16,
    target_modules=["q_proj", "v_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
)
model = get_peft_model(model, lora_config)
print(f"Trainable parameters: {model.num_parameters(only_trainable=True):,}")

# ============================================
# LOAD DATASETS
# ============================================
print("Loading Alpaca 52k...")
alpaca = load_dataset("tatsu-lab/alpaca", split="train", cache_dir=CACHE_DIR)

with open("identity_data.json", "r") as f:
    identity_data = json.load(f)
identity_dataset = Dataset.from_list(identity_data)

def format_chat(example):
    content = example["instruction"]
    if example.get("input") and example["input"]:
        content += "\n" + example["input"]
    text = f"Question: {content}\nAnswer: {example['output']}"
    return {"text": text}

print("Formatting datasets...")
alpaca = alpaca.map(format_chat)
identity_dataset = identity_dataset.map(format_chat)

# Repeat identity data 10x to hammer it in
identity_repeated = concatenate_datasets([identity_dataset] * 10)
dataset = concatenate_datasets([alpaca, identity_repeated])

print(f"Total examples: {len(dataset):,} (Alpaca: 52,002 + Identity: {len(identity_repeated)})")

# ============================================
# TRAIN - 1000 steps, save every 100
# ============================================
print("\n" + "=" * 50)
print("Starting training: 1000 steps, save every 100")
print("Expected pace: ~7-8 seconds/step on CPU")
print("=" * 50 + "\n")

trainer = SFTTrainer(
    model=model,
    args=TrainingArguments(
        output_dir=OUTPUT_DIR,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        num_train_epochs=1,
        max_steps=1000,              # Full 1000 steps
        logging_steps=25,            # Print loss every 25 steps
        save_steps=100,              # Save checkpoint every 100 steps
        fp16=False,
        report_to="none",
        learning_rate=2e-4,
        save_total_limit=3,
    ),
    train_dataset=dataset,
)

trainer.train()

# ============================================
# SAVE FINAL MODEL
# ============================================
print("\n" + "=" * 50)
print(f"Saving final model to {OUTPUT_DIR}...")
print("=" * 50)

model.save_pretrained(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)

print("\n✅ DONE! 1000-step GOODBOY model saved.")
print(f"   Location: {OUTPUT_DIR}")
