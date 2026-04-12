# resume_train.py - Resume GOODBOY from 700 to 1000
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

CHECKPOINT = "./smollm2-sft-identity/checkpoint-700"  # Changed to 700
OUTPUT_DIR = "./smollm2-sft-identity"

# ============================================
# LOAD MODEL FROM CHECKPOINT-700
# ============================================
print("Loading GOODBOY from checkpoint-700...")
model = AutoModelForCausalLM.from_pretrained(
    CHECKPOINT,
    torch_dtype=torch.float32,
    device_map="cpu",
    low_cpu_mem_usage=True
)
tokenizer = AutoTokenizer.from_pretrained(CHECKPOINT)
tokenizer.pad_token = tokenizer.eos_token

# ============================================
# LoRA - Re-apply (weights loaded from checkpoint)
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

# Repeat identity data 10x
identity_repeated = concatenate_datasets([identity_dataset] * 10)
dataset = concatenate_datasets([alpaca, identity_repeated])

print(f"Total examples: {len(dataset):,}")

# ============================================
# RESUME TRAINING - 700 to 1000
# ============================================
print("\n" + "=" * 50)
print("Resuming training from step 700 to 1000")
print("=" * 50 + "\n")

trainer = SFTTrainer(
    model=model,
    args=TrainingArguments(
        output_dir=OUTPUT_DIR,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        num_train_epochs=1,
        max_steps=1000,
        logging_steps=25,
        save_steps=100,
        fp16=False,
        report_to="none",
        learning_rate=2e-4,
        save_total_limit=3,
    ),
    train_dataset=dataset,
)

# RESUME FROM CHECKPOINT
trainer.train(resume_from_checkpoint=CHECKPOINT)

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
