# chat_500.py - Test GOODBOY at 500 steps
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

CHECKPOINT = "./smollm2-sft-identity/checkpoint-500"

print(f"Loading GOODBOY from {CHECKPOINT}...")
model = AutoModelForCausalLM.from_pretrained(
    CHECKPOINT,
    torch_dtype=torch.float32,
    device_map="cpu",
    low_cpu_mem_usage=True
)
tokenizer = AutoTokenizer.from_pretrained(CHECKPOINT)
tokenizer.pad_token = tokenizer.eos_token

print("=" * 50)
print("GOODBOY 500-step model loaded!")
print("Type 'exit' to quit.")
print("=" * 50)

def chat(prompt):
    text = f"Question: {prompt}\nAnswer:"
    inputs = tokenizer(text, return_tensors="pt")
    
    outputs = model.generate(
        inputs["input_ids"],
        max_new_tokens=100,
        temperature=0.7,
        do_sample=True,
        top_k=50,
        top_p=0.95,
        repetition_penalty=1.0,
        pad_token_id=tokenizer.eos_token_id,
    )
    
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    if "Answer:" in response:
        response = response.split("Answer:")[-1].strip()
    return response

# Test identity automatically
print("\n--- Testing Identity ---")
test_prompts = [
    "Who made you?",
    "Who are you?",
    "What is your name?",
    "Who is your creator?",
    "hi",
]

for p in test_prompts:
    print(f"\nYou: {p}")
    print(f"Bot: {chat(p)}")

print("\n" + "=" * 50)
print("Interactive mode ready!")
print("=" * 50)

# Interactive loop
while True:
    user_input = input("\nYou: ")
    if user_input.lower() in ["exit", "quit", "bye"]:
        print("Later!")
        break
    print(f"\nBot: {chat(user_input)}")
