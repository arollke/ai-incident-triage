import json

from app.cli import main


def test_cli_defaults_to_deterministic_mode(capsys):
    exit_code = main(["ingest", "seed_data/incidents/payment_outage.md"])

    captured = capsys.readouterr()
    with open("seed_data/expected/payment_outage.json", encoding="utf-8") as expected_file:
        expected = json.load(expected_file)

    assert exit_code == 0
    assert json.loads(captured.out) == expected
    assert captured.err == ""


def test_cli_llm_mode_fails_clearly_without_api_key(monkeypatch, capsys):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    exit_code = main(["ingest", "seed_data/incidents/payment_outage.md", "--mode", "llm"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "OPENAI_API_KEY is required for llm mode" in captured.err
    assert captured.out == ""
