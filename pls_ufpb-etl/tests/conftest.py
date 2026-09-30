import pytest

from common import comunidade


@pytest.fixture(autouse=True)
def _sem_contagem_ufpb(tmp_path, monkeypatch):
    """Testes nao leem ref/comunidade_ufpb.csv real: sem ele, a comunidade vem do INEP gravado pelo teste."""
    monkeypatch.setattr(comunidade, "ARQUIVO", tmp_path / "comunidade_ufpb.csv")
