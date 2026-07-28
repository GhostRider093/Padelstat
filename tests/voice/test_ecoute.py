"""
Tests de la détection du mot-clé.

Mesure du 28/07/2026 : « OK STAT » ressort exact 17 fois sur 17. Ces tests
figent ce que le détecteur doit accepter, et surtout ce qu'il doit refuser —
un faux déclenchement met la vidéo en pause au milieu d'un échange.
"""

import pytest

from app.voice.ecoute import MOT_CLE, contient_motcle, detecter_commande


@pytest.mark.parametrize("texte", [
    "OK Stat.",
    "ok stat",
    "OK STAT",
    "Ok, stat !",
    "OK OK Stat.",            # mesuré : le « OK » doublé
    "okstat",
])
def test_pause(texte):
    assert detecter_commande(texte) == "pause"


@pytest.mark.parametrize("texte", [
    "Reprise.",
    "reprise",
    "Reprends.",
    "On reprend.",
    # Déformations relevées en session, faute de biais de décodage.
    "Au prise.",
    "Bonne prise.",
    "Bonne paise.",
])
def test_reprise(texte):
    assert detecter_commande(texte) == "reprise"


@pytest.mark.parametrize("texte, attendu", [
    ("Trois secondes.", "avance_3"),
    ("3 secondes", "avance_3"),
    ("Cinq secondes.", "avance_5"),
    ("5 secondes", "avance_5"),
    ("Recule trois secondes.", "recul_3"),
    ("Recule cinq secondes.", "recul_5"),
])
def test_deplacements(texte, attendu):
    assert detecter_commande(texte) == attendu


@pytest.mark.parametrize("texte", [
    "OK Stat. Reprise.",          # mesuré : le modèle régurgitait le prompt
    "reprise ok stat",
])
def test_deux_commandes_dans_un_segment_n_executent_rien(texte):
    """Mieux vaut ne rien faire que se tromper d'action : c'est ce qui
    mettait la vidéo en pause à chaque parole."""
    assert detecter_commande(texte) is None


def test_le_prompt_ne_repete_aucune_commande():
    """Un prompt répétitif fait régurgiter le prompt par le modèle : chaque
    segment ressortait « OK Stat. Reprise. » quoi qu'on ait dit."""
    from app.voice.ecoute import PROMPT

    prompt = PROMPT.lower()
    for terme in ("ok stat", "reprise", "trois secondes", "cinq secondes"):
        assert prompt.count(terme) == 1, f"{terme!r} répété dans le prompt"


def test_le_prompt_contient_toutes_les_commandes():
    """Une commande absente du biais ressort déformée : « reprise » ratait
    deux fois sur trois tant qu'elle n'y figurait pas."""
    from app.voice.ecoute import PROMPT

    prompt = PROMPT.lower()
    assert "ok stat" in prompt
    assert "reprise" in prompt


def test_deux_commandes_distinctes_pas_une_bascule():
    """Une bascule laisse dans un état imprévisible après un déclenchement
    parasite ; deux commandes sont idempotentes."""
    assert detecter_commande("OK Stat.") == "pause"
    assert detecter_commande("Reprise.") == "reprise"


@pytest.mark.parametrize("texte", [
    "OK Stat.",
    "ok stat",
    "OK OK Stat.",
    "okstat",
    "Reprise.",
])
def test_declenche(texte):
    assert contient_motcle(texte), f"{texte!r} aurait dû déclencher"


@pytest.mark.parametrize("texte", [
    "",
    "point gagnant joueur trois filet revers",
    "faute directe joueur deux service",
    "d'accord",
    "OK",                     # « OK » seul ne suffit pas
    "statistique",
    "c'est bon on y va",
    "annuler",
    "bandeja",
])
def test_ne_declenche_pas(texte):
    assert not contient_motcle(texte), f"{texte!r} n'aurait pas dû déclencher"


@pytest.mark.parametrize("texte", [
    "Sous-titres réalisés par la communauté d'Amara.org",
    "Sous-titrage Société Radio-Canada",
    "Merci d'avoir regardé cette vidéo !",
    "Abonnez-vous !",
])
def test_hallucinations_filtrees(texte):
    """Whisper produit ces phrases sur du quasi-silence, héritées de son
    corpus de sous-titres. Elles ne doivent pas encombrer la trace."""
    from app.voice.ecoute import est_hallucination
    assert est_hallucination(texte)


@pytest.mark.parametrize("texte", [
    "OK Stat.",
    "Reprise.",
    "point gagnant joueur trois filet revers",
])
def test_la_parole_utile_n_est_pas_filtree(texte):
    from app.voice.ecoute import est_hallucination
    assert not est_hallucination(texte)


def test_le_mot_cle_est_bien_celui_mesure():
    assert MOT_CLE == "ok stat"


def test_seuil_strict_refuse_les_approximations():
    """Au seuil par défaut on tolère la déformation ; en le montant, non."""
    assert contient_motcle("ok stade", seuil=80)
    assert not contient_motcle("ok stade", seuil=95)
