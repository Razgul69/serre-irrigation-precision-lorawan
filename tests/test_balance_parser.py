"""Tests du parseur de trames SICS de la balance Ohaus."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "balance"))

from collect_balance import parse_frame


def test_poids_stable():
    weight, stable, status = parse_frame("S S       11.5 g")
    assert weight == 11.5
    assert stable is True
    assert status == "ok"


def test_poids_dynamique():
    weight, stable, status = parse_frame("S D      62.20 g")
    assert weight == 62.20
    assert stable is False
    assert status == "ok"


def test_kilogrammes_convertis_en_grammes():
    weight, _, status = parse_frame("S S 1.234 kg")
    assert weight == 1234.0
    assert status == "ok"


def test_poids_negatif():
    weight, _, status = parse_frame("S S       -0.5 g")
    assert weight == -0.5
    assert status == "ok"


def test_surcharge():
    weight, stable, status = parse_frame("S +")
    assert weight is None
    assert status == "surcharge"


def test_sous_charge():
    assert parse_frame("S -")[2] == "sous_charge"


def test_erreur_syntaxe():
    assert parse_frame("ES")[2] == "erreur_syntaxe"


def test_trame_vide():
    assert parse_frame("")[2] == "empty"


def test_trame_inconnue():
    assert parse_frame("garbage 123")[2] == "trame_inconnue"
