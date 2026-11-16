"""Mesure en tokens de l'exemple complet de docs/prompt_format.md."""

from transformers import AutoTokenizer

from scripts.prompt_format import SYSTEM_RULES, apply_limits, build_messages, build_system, build_user
from tests.test_prompt_format import example_inputs  # données de l'exemple du document

MODEL_ID = "unsloth/Ministral-3-8B-Instruct-2512-unsloth-bnb-4bit"

tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, fix_mistral_regex=True)


def count_tokens(text: str) -> int:
    """Nombre de tokens d'un texte, sans le <s> ajouté automatiquement."""
    return len(tokenizer.encode(text, add_special_tokens=False))


inputs = apply_limits(example_inputs(), count_tokens)
messages = build_messages(inputs)
full_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

print(f"Règles (Pixou)      : {count_tokens(SYSTEM_RULES.replace('{bot_name}', 'Pixou'))} tokens")
print(f"Message system      : {count_tokens(build_system(inputs))} tokens")
print(f"Message user        : {count_tokens(build_user(inputs))} tokens")
print(f"Total avec template : {count_tokens(full_text)} tokens")
