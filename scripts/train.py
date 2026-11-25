"""Entraînement QLoRA d'un modèle sur le dataset seed (phase 4).

Usage : uv run python -m scripts.train --config configs/train_v0_ministral3_3b.yaml
"""
from unsloth import FastModel  # en premier : Unsloth modifie transformers à l'import

import argparse
import json
from pathlib import Path

import yaml
from datasets import Dataset

import torch
from transformers import AutoTokenizer

from datetime import datetime
from importlib.metadata import version
from trl import SFTConfig, SFTTrainer

ROOT = Path(__file__).parent.parent


def load_config(path: str) -> dict:
    """Lit la config YAML de l'entraînement."""
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_split(path: str, chat_template_kwargs: dict | None = None) -> Dataset:
    """Charge un JSONL {id, category, messages} au format prompt/completion de TRL."""
    rows = []
    with open(ROOT / path, encoding="utf-8") as f:
        for line in f:
            example = json.loads(line)
            roles = [m["role"] for m in example["messages"]]
            if roles != ["system", "user", "assistant"]:
                raise ValueError(f"{example['id']} : rôles inattendus {roles}")
            row ={
                "prompt": example["messages"][:2],       # system + user : lu, pas appris
                "completion": example["messages"][2:],   # assistant : la seule partie apprise
            }
            if chat_template_kwargs:
                row["chat_template_kwargs"] = chat_template_kwargs
            rows.append(row)
    return Dataset.from_list(rows)

def load_model(config: dict):
    """Modèle de base en 4 bits (figé) + adaptateur LoRA entraînable, et tokenizer."""
    model_id = config["model"]["id"]
    model, _processor = FastModel.from_pretrained(
        model_id,
        max_seq_length=config["model"]["max_seq_length"],
        load_in_4bit=True,
        text_only=True,
    )
    # padding à droite pour l'entraînement (à gauche seulement pour générer)
    tokenizer = AutoTokenizer.from_pretrained(model_id, fix_mistral_regex=True, padding_side="right")

    lora = config["lora"]
    model = FastModel.get_peft_model(
        model,
        r=lora["r"],
        lora_alpha=lora["alpha"],
        lora_dropout=lora["dropout"],
        finetune_language_layers=lora["finetune_language_layers"],
        finetune_attention_modules=lora["finetune_attention_modules"],
        finetune_mlp_modules=lora["finetune_mlp_modules"],
        finetune_vision_layers=lora["finetune_vision_layers"],
        bias="none",
        use_gradient_checkpointing="unsloth",  # recalcule au lieu de stocker : beaucoup moins de VRAM
        random_state=config["seed"],
    )

    vision_lora = [name for name, _ in model.named_modules() if "lora_A" in name and "vision" in name]
    if vision_lora:
        raise ValueError(f"{len(vision_lora)} adaptateurs sur la vision, ex. {vision_lora[0]}")
    return model, tokenizer

def build_trainer(config: dict, model, tokenizer, train_set, val_set, output_dir: Path) -> SFTTrainer:
    """Prépare l'entraînement : tous les réglages viennent de la config."""
    training = config["training"]
    args = SFTConfig(
        output_dir=str(output_dir),
        max_length=config["model"]["max_seq_length"],  # sinon 1024 par défaut : exemples coupés
        completion_only_loss=True,                     # perte sur la réponse seulement
        num_train_epochs=training["epochs"],
        max_steps=training.get("max_steps", -1),       # -1 = toutes les époques
        learning_rate=training["learning_rate"],
        lr_scheduler_type=training["lr_scheduler"],
        warmup_steps=training["warmup_steps"],
        per_device_train_batch_size=training["batch_size"],
        per_device_eval_batch_size=training["batch_size"],
        gradient_accumulation_steps=training["gradient_accumulation"],
        optim=training["optimizer"],
        weight_decay=training["weight_decay"],
        logging_steps=training["logging_steps"],
        eval_strategy="steps",
        eval_steps=training["eval_steps"],
        save_steps=training["save_steps"],
        bf16=True,
        seed=config["seed"],
        report_to="tensorboard",
    )
    return SFTTrainer(
        model=model,
        processing_class=tokenizer,
        args=args,
        train_dataset=train_set,
        eval_dataset=val_set,
    )


def check_labels(trainer: SFTTrainer, tokenizer, raw_set: Dataset, max_length: int, suffix: str):
    """Vérifie que chaque exemple n'apprend que sa réponse, suivie de </s>, sans être coupé."""
    prepared = trainer.train_dataset
    if len(prepared) != len(raw_set):
        raise ValueError(f"{len(raw_set)} exemples au départ, {len(prepared)} après préparation")
    longest = 0
    for i in range(len(prepared)):
        batch = trainer.data_collator([prepared[i]])
        labels = batch["labels"][0]
        longest = max(longest, len(labels))
        learned = tokenizer.decode(labels[labels != -100], skip_special_tokens=False)
        expected = raw_set[i]["completion"][0]["content"] + suffix
        if learned != expected:
            raise ValueError(f"exemple {i} : labels {learned!r} au lieu de {expected!r}")
    if longest >= max_length:
        raise ValueError(f"un exemple atteint {longest} tokens : il a sans doute été coupé")
    print(f"Labels vérifiés : {len(prepared)}/{len(raw_set)} exemples, réponse + {suffix!r} seulement")
    print(f"Exemple le plus long : {longest} tokens (limite {max_length})")

def save_run_info(run_dir: Path, config: dict):
    """Copie la config et les versions dans le run, pour savoir comment l'adaptateur a été obtenu."""
    run_dir.mkdir(parents=True, exist_ok=True)
    with open(run_dir / "config.yaml", "w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, allow_unicode=True, sort_keys=False)
    versions = {name: version(name) for name in ["torch", "transformers", "trl", "peft", "unsloth", "bitsandbytes"]}
    versions["gpu"] = torch.cuda.get_device_name()
    with open(run_dir / "versions.json", "w", encoding="utf-8") as f:
        json.dump(versions, f, indent=2)

def main():
    parser = argparse.ArgumentParser(description="Entraîne un adaptateur LoRA.")
    parser.add_argument("--config", required=True, help="fichier YAML de l'entraînement")
    parser.add_argument("--check-only", action="store_true", help="vérifie les labels sans entraîner")
    parser.add_argument("--max-steps", type=int, help="limite d'étapes (entraînement test)")
    args = parser.parse_args()

    config = load_config(args.config)
    if args.max_steps:
        config["training"]["max_steps"] = args.max_steps
        config["run_name"] += "_test"
    template_kwargs = config["model"].get("chat_template_kwargs")
    train_set = load_split(config["data"]["train"], template_kwargs)
    val_set = load_split(config["data"]["val"], template_kwargs)
    print(f"Modèle : {config['model']['id']}")
    print(f"Exemples : train {len(train_set)}, val {len(val_set)}")
    print(f"Première réponse à apprendre : {train_set[0]['completion'][0]['content']}")

    model, tokenizer = load_model(config)
    print(f"VRAM après chargement + LoRA : {torch.cuda.memory_allocated() / 1e9:.2f} Go")
    model.print_trainable_parameters()

    run_dir = ROOT / "runs" / f"{datetime.now():%Y%m%d-%H%M}_{config['run_name']}"
    trainer = build_trainer(config, model, tokenizer, train_set, val_set, run_dir)
    suffix = config["model"].get("completion_suffix", tokenizer.eos_token)   # Ministral : </s> 
    check_labels(trainer, tokenizer, train_set, config["model"]["max_seq_length"], suffix)
    if args.check_only:
        return

    save_run_info(run_dir, config)
    print(f"Run : {run_dir}")
    trainer.train()

    trainer.save_model(str(run_dir / "adapter"))   # l'adaptateur LoRA seul, pas le modèle de base
    tokenizer.save_pretrained(str(run_dir / "adapter"))
    with open(run_dir / "metrics.json", "w", encoding="utf-8") as f:
        json.dump({
            "log_history": trainer.state.log_history,
            "peak_vram_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2),
        }, f, indent=2)
    print(f"Adaptateur : {run_dir / 'adapter'}")
    print(f"Pic de VRAM : {torch.cuda.max_memory_allocated() / 1e9:.2f} Go")

if __name__ == "__main__":
    main()