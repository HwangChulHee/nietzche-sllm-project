"""
Nietzsche sLLM LoRA fine-tuning (Gemma 4, bf16).

Strategy:
- LoRA (not QLoRA) on bf16 base for faster per-step training
- Small rank (16) to limit overfitting on 2413 samples
- Conservative learning rate (1e-4) for small dataset
- 5 epochs with all checkpoints saved
- val split (5%) for loss monitoring only; final selection via Stage B
- eval.jsonl is held-out test set, NOT loaded here

Known limitation:
- assistant_only_loss is not supported for VLM (Gemma 4 is multi-modal base).
  Loss is computed over full text including user/system tokens.
  Acceptable trade-off given time constraints.

Env vars:
    MODEL=26b | 31b      (default: 31b)
    SMOKE=1              (smoke test: 50 samples, 1 epoch, no eval/save)

Run:
    cd /workspace/nietzche-sllm-project/ml/finetune
    SMOKE=1 poetry run python scripts/train.py                # 31b smoke
    MODEL=26b SMOKE=1 poetry run python scripts/train.py      # 26b smoke
    poetry run python scripts/train.py                        # 31b full
    MODEL=26b poetry run python scripts/train.py              # 26b full
"""
import os
from pathlib import Path

# wandb project는 trl import 전에 설정
os.environ.setdefault("WANDB_PROJECT", "nietzsche-sllm")

from unsloth import FastLanguageModel
from datasets import load_dataset
from transformers import set_seed
from trl import SFTTrainer, SFTConfig

# ---------- mode ----------
SMOKE = os.getenv("SMOKE") == "1"
MODEL_KEY = os.getenv("MODEL", "31b").lower()

MODEL_REGISTRY = {
    "26b": "google/gemma-4-26B-A4B-it",
    "31b": "google/gemma-4-31B-it",
}
if MODEL_KEY not in MODEL_REGISTRY:
    raise ValueError(f"MODEL must be one of {list(MODEL_REGISTRY)}, got {MODEL_KEY}")

MODEL_NAME = MODEL_REGISTRY[MODEL_KEY]

print("=" * 60)
print(f"MODEL: {MODEL_NAME}")
print(f"MODE: {'SMOKE TEST (50 samples, 1 epoch)' if SMOKE else 'FULL RUN'}")
print("=" * 60)

# ---------- paths ----------
ROOT = Path(__file__).resolve().parent.parent  # finetune/
DATA_DIR = ROOT / "data"
RUN_TAG = f"{MODEL_KEY}{'-smoke' if SMOKE else ''}"
OUTPUT_DIR = ROOT / "outputs" / f"nietzsche-lora-{RUN_TAG}"
LOG_DIR = ROOT / "logs"

# ---------- config ----------
MAX_SEQ_LEN = 384   # data max=355
LORA_R = 16
LORA_ALPHA = 32     # scale 2.0
LORA_DROPOUT = 0.0  # 0 enables Unsloth fast patching
EPOCHS = 1 if SMOKE else 5
LR = 1e-4
BATCH = 2
GRAD_ACCUM = 8      # effective batch 16
WARMUP_STEPS = 20   # ~3% of full run (~715 steps)
VAL_RATIO = 0.05
SEED = 42

set_seed(SEED)

# ---------- model + tokenizer ----------
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=MODEL_NAME,
    max_seq_length=MAX_SEQ_LEN,
    dtype=None,           # auto (bf16 on A100)
    load_in_4bit=False,   # LoRA, not QLoRA
)

# NOTE: Gemma 4 native chat template (<|turn>system...<|turn|>) 사용.
# unsloth.chat_templates.get_chat_template는 Gemma 2/3용 구식 (<start_of_turn>)
# 이라 system role이 user에 합쳐지는 문제가 있음. 호출하지 않음.

# ---------- chat template sanity check ----------
print("\n--- chat template sanity check ---")
_test_msgs = [
    {"role": "system",    "content": "SYSTEM_PROBE"},
    {"role": "user",      "content": "USER_PROBE"},
    {"role": "assistant", "content": "ASSISTANT_PROBE"},
]
_test_text = tokenizer.apply_chat_template(_test_msgs, tokenize=False)
print(_test_text)
assert "SYSTEM_PROBE" in _test_text, "system role lost in chat template!"
assert "USER_PROBE" in _test_text, "user role lost in chat template!"
assert "ASSISTANT_PROBE" in _test_text, "assistant role lost in chat template!"
assert _test_text.index("SYSTEM_PROBE") < _test_text.index("USER_PROBE"), \
    "system appears after user — likely merged into user message"
print("--- chat template OK ---\n")

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

if SMOKE:
    raw = raw.select(range(50))

split = raw.train_test_split(test_size=VAL_RATIO, seed=SEED)

train_ds = split["train"].map(format_example, remove_columns=split["train"].column_names)
val_ds   = split["test"].map(format_example,  remove_columns=split["test"].column_names)

print(f"train={len(train_ds)}  val={len(val_ds)}")
print("--- first sample (rendered) ---")
print(train_ds[0]["text"][:800])
print("-------------------------------\n")

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
    warmup_steps=WARMUP_STEPS,
    weight_decay=0.01,
    optim="adamw_8bit",

    bf16=True,
    fp16=False,

    max_seq_length=MAX_SEQ_LEN,
    dataset_text_field="text",
    packing=False,

    # assistant_only_loss는 Gemma 4가 VLM이라 trl에서 미지원.
    # 전체 텍스트에 loss 적용. 시간 제약으로 일단 우회.
    assistant_only_loss=False,

    # eval & save
    eval_strategy="no" if SMOKE else "epoch",
    save_strategy="no" if SMOKE else "epoch",
    save_total_limit=5,

    logging_steps=1 if SMOKE else 10,
    report_to="none" if SMOKE else "wandb",
    run_name=f"nietzsche-gemma4-{RUN_TAG}-lora-r{LORA_R}-e{EPOCHS}",
    seed=SEED,
)

trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=train_ds,
    eval_dataset=val_ds if not SMOKE else None,
    args=cfg,
)

# ---------- go ----------
if __name__ == "__main__":
    trainer.train()
    if not SMOKE:
        final_dir = OUTPUT_DIR / "final"
        trainer.save_model(str(final_dir))
        tokenizer.save_pretrained(str(final_dir))
        print(f"\nSaved final model to: {final_dir}")
    print("done.")