import pytest

from scripts.contexts import load_matrix, load_pools
from scripts.eval_cases import load_cases
from scripts.export_batch import build_batch, build_generator_prompt
from scripts.prompt_format import SYSTEM_RULES

ITEMS = build_batch(1, 20, load_pools(), load_matrix())
PROMPT = build_generator_prompt(ITEMS)


def test_prompt_is_complete():
    assert "<<" not in PROMPT  # tous les marqueurs remplacés
    assert SYSTEM_RULES in PROMPT
    assert "Hollow Knight Silksong" in PROMPT  # réponse de l'exemple du doc
    assert all(item["id"] in PROMPT for item in ITEMS)


def test_prompt_contains_no_eval_message():
    # le générateur ne doit jamais voir l'examen
    for case in load_cases():
        assert case["inputs"]["message"] not in PROMPT


def test_exported_batch_is_never_exported_again(tmp_path):
    from scripts.export_batch import batch_dir, check_not_exported

    check_not_exported(tmp_path / "batch_099")  # lot neuf : pas d'erreur
    (tmp_path / "batch.json").write_text("[]", encoding="utf-8")
    with pytest.raises(SystemExit, match="ne se réexporte jamais"):
        check_not_exported(tmp_path)
    check_not_exported(tmp_path, force=True)
    (tmp_path / "output.jsonl").write_text("", encoding="utf-8")
    with pytest.raises(SystemExit, match="même avec --force"):
        check_not_exported(tmp_path, force=True)  # déjà envoyé au générateur
    with pytest.raises(SystemExit):
        check_not_exported(batch_dir(3))  # lot déjà généré, versionné dans le repo (les lots 1 et 2 ont été retirés)


def test_situations_fit_their_context():
    """Plus de situation impossible : emotes sans liste, fait_present sans autre fait que l'intro."""
    from scripts.contexts import situation_fits

    pools, matrix = load_pools(), load_matrix()
    for batch_id in range(3, 16):
        for item in build_batch(batch_id, 20, pools, matrix):
            assert situation_fits(item["situation"]["category"], item["inputs"])
