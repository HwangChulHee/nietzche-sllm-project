"""
Nietzsche sLLM LoRA fine-tuning (Gemma 4 26B, bf16).
Run: poetry run python scripts/train.py
"""
from pathlib import Path

from unsloth import FastLanguageModel
from unsloth.chat_templates import get_chat_template
from datasets import load_dataset
from trl import SFTTrainer, SFTConfig

# ---------- paths ----------
ROOT = Path(__file__).resolve().parent.parent  # finetune/
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "outputs" / "nietzsche-lora"
LOG_DIR = ROOT / "logs"

# ---------- config ----------
MODEL_NAME = "google/gemma-4-26B-A4B-it"  # 실제 ID 확인 필요
MAX_SEQ_LEN = 1024  # 데이터 길이 분포 확인 후 조정
LORA_R = 16
LORA_ALPHA = 32   # scale 2.0
LORA_DROPOUT = 0.05
EPOCHS = 5
LR = 1e-4
BATCH = 2
GRAD_ACCUM = 8    # effective 16
WARMUP_RATIO = 0.03
VAL_RATIO = 0.05
SEED = 42

# ---------- model + tokenizer ----------
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=MODEL_NAME,
    max_seq_length=MAX_SEQ_LEN,
    dtype=None,          # auto (bf16 on A100)
    load_in_4bit=False,  # LoRA (not QLoRA)
)

tokenizer = get_chat_template(tokenizer, chat_template="gemma")

# ---------- LoRA ----------
model = FastLanguageModel.get_peft_model(
    model,
    r=LORA_R,
    lora_alpha=LORA_ALPHA,
    lora_dropout=LORA_DROPOUT,
    bias="none",
    target_modules=[
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ],
    use_gradient_checkpointing="unsloth",
    random_state=SEED,
)

# ---------- data ----------
def format_example(example):
    text = tokenizer.apply_chat_template(
        example["messages"],
        tokenize=False,
        add_generation_prompt=False,
    )
    return {"text": text}

raw = load_dataset("json", data_files=str(DATA_DIR / "train.jsonl"), split="train")
split = raw.train_test_split(test_size=VAL_RATIO, seed=SEED)

train_ds = split["train"].map(format_example, remove_columns=split["train"].column_names)
val_ds   = split["test"].map(format_example,  remove_columns=split["test"].column_names)

print(f"train={len(train_ds)}  val={len(val_ds)}")
print("--- sample ---")
print(train_ds[0]["text"][:500])
print("--------------")

# ---------- trainer config ----------
cfg = SFTConfig(
    output_dir=str(OUTPUT_DIR),
    logging_dir=str(LOG_DIR),

    num_train_epochs=EPOCHS,
    per_device_train_batch_size=BATCH,
    per_device_eval_batch_size=BATCH,
    gradient_accumulation_steps=GRAD_ACCUM,

    learning_rate=LR,
    lr_scheduler_type="cosine",
    warmup_ratio=WARMUP_RATIO,
    weight_decay=0.01,
    optim="adamw_8bit",

    bf16=True,
    fp16=False,

    max_seq_length=MAX_SEQ_LEN,
    dataset_text_field="text",
    packing=False,

    # --- eval & save ---
    # val loss는 모니터링 전용, 체크포인트 선택은 Stage B에서 수행
    eval_strategy="epoch",
    save_strategy="epoch",
    save_total_limit=5,   # epoch 1~5 전부 보존

    logging_steps=10,
    report_to="wandb",
    run_name="nietzsche-gemma4-lora-r16-e5",
    seed=SEED,
)

trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=train_ds,
    eval_dataset=val_ds,
    args=cfg,
)

# ---------- go ----------
if __name__ == "__main__":
    import os
    os.environ.setdefault("WANDB_PROJECT", "nietzsche-sllm")
    trainer.train()
    trainer.save_model(str(OUTPUT_DIR / "final"))
    tokenizer.save_pretrained(str(OUTPUT_DIR / "final"))
    print("done.")