"""
Upload LoRA checkpoints to HuggingFace Hub.

Each checkpoint is pushed to a separate branch of the same repo.
Only adapter files (not tokenizer, not optimizer state) are uploaded.

Run:
    cd /workspace/nietzche-sllm-project/ml/finetune
    poetry run python scripts/upload_lora.py
"""
from pathlib import Path
from huggingface_hub import HfApi, create_repo

ROOT = Path(__file__).resolve().parent.parent
LORA_DIR = ROOT / "outputs" / "nietzsche-lora-31b"

REPO_ID = "banzack/nietzsche-gemma4-31b-lora"
PRIVATE = True

CHECKPOINTS = {
    "epoch1": LORA_DIR / "checkpoint-144",
    "epoch2": LORA_DIR / "checkpoint-288",
    "epoch3": LORA_DIR / "checkpoint-432",
    "epoch4": LORA_DIR / "checkpoint-576",
    "epoch5": LORA_DIR / "checkpoint-720",
}

# 건너뛸 체크포인트 (이미 올린 것)
SKIP = set()  # 예: {"epoch1"}

def main():
    api = HfApi()
    create_repo(REPO_ID, private=PRIVATE, exist_ok=True)

    for tag, path in CHECKPOINTS.items():
        if tag in SKIP:
            print(f"[SKIP] {tag}: already uploaded")
            continue
        if not path.exists():
            print(f"[SKIP] {tag}: not found")
            continue

        print(f"\n=== Uploading {tag} from {path} ===")

        try:
            api.create_branch(repo_id=REPO_ID, branch=tag, exist_ok=True)
        except Exception as e:
            print(f"  branch create warning: {e}")

        # LoRA adapter 필수 파일만 업로드
        api.upload_folder(
            folder_path=str(path),
            repo_id=REPO_ID,
            revision=tag,
            allow_patterns=[
                "adapter_model.safetensors",
                "adapter_config.json",
                "README.md",
            ],
            commit_message=f"Upload {tag} checkpoint",
        )
        print(f"  done: https://huggingface.co/{REPO_ID}/tree/{tag}")

    print("\n=== all uploads complete ===")
    print(f"View: https://huggingface.co/{REPO_ID}")

if __name__ == "__main__":
    main()