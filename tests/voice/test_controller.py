"""
Tests de la machine a etats et du threading.

Micro et moteur sont remplaces par des doublures : ce qui est teste ici,
c'est l'orchestration, pas la reconnaissance.

Voir SPEC_MODULE_VOCAL_PTT_V2.md sections 4 et 8.
"""

import time

import numpy as np
import pytest

from app.voice.config import VoiceConfig
from app.voice.controller import (
    ERROR,
    FINALIZING,
    IDLE,
    PARTIAL,
    RECORDING,
    RESULT,
    VoiceController,
)
from app.voice.engines.base import Transcription
from app.voice.recorder import Capture, ErreurMicro

ROSTER = [
    {"nom": "pascal", "equipe": 1, "position": "gauche"},
    {"nom": "arnaud", "equipe": 1, "position": "droite"},
    {"nom": "philippe", "equipe": 2, "position": "gauche"},
    {"nom": "alex", "equipe": 2, "position": "droite"},
]


def capture(duree_appui=1.0, silencieuse=False, tronquee=False):
    niveau = 0.0 if silencieuse else 0.05
    return Capture(
        audio=np.full(16000, niveau, dtype=np.float32),
        sample_rate=16000,
        duree_appui_s=duree_appui,
        tronquee=tronquee,
    )


class FauxRecorder:
    def __init__(self, resultat=None, erreur=None):
        self.en_cours = False
        self.depassement = False
        self.resultat = resultat or capture()
        self.erreur = erreur
        self.annulations = 0

    def demarrer(self):
        if self.erreur:
            raise self.erreur
        self.en_cours = True

    def arreter(self):
        self.en_cours = False
        return self.resultat

    def annuler(self):
        self.en_cours = False
        self.annulations += 1

    def fermer(self):
        self.en_cours = False


class FauxMoteur:
    def __init__(self, texte="", erreur=None):
        self.texte = texte
        self.erreur = erreur
        self.prompts = []

    def warmup(self):
        pass

    def transcrire(self, audio, prompt=None):
        self.prompts.append(prompt)
        if self.erreur:
            raise RuntimeError(self.erreur)
        return Transcription(texte=self.texte, confiance_acoustique=0.9)

    def fermer(self):
        pass


class Journal:
    """Enregistre les rappels, avec le thread qui les a emis."""

    def __init__(self):
        self.resultats = []
        self.partiels = []
        self.controles = []
        self.etats = []
        self.erreurs = []

    def brancher(self, controleur):
        controleur.on_result = self.resultats.append
        controleur.on_partial = lambda i, s: self.partiels.append((i, s))
        controleur.on_control = self.controles.append
        controleur.on_state_change = self.etats.append
        controleur.on_error = self.erreurs.append


def journal_slot(controleur):
    """Le slot que l'arbre attend, en etat PARTIAL."""
    return controleur.intention.slot_attendu(controleur.roster)


@pytest.fixture
def controleur():
    ctrl = VoiceController(VoiceConfig(), roster=ROSTER)
    ctrl.recorder = FauxRecorder()
    ctrl.moteur = FauxMoteur()
    ctrl._pret = True
    return ctrl


def attendre(controleur, timeout=5.0):
    """Attend le resultat du thread de travail, puis depile.

    La doublure de moteur est instantanee : un `poll()` precedent a pu
    depiler le resultat dans la meme passe qu'il a lance le worker. On
    verifie donc aussi qu'il ne reste rien en cours.
    """
    limite = time.time() + timeout
    while time.time() < limite:
        if not controleur._resultats.empty():
            controleur.poll()
            return
        if not controleur._occupe:
            return
        time.sleep(0.005)
    raise AssertionError("aucun resultat remonte")


# --------------------------------------------------------------------------
# Machine a etats
# --------------------------------------------------------------------------


def test_cycle_complet(controleur):
    journal = Journal()
    journal.brancher(controleur)
    controleur.moteur.texte = "point gagnant joueur trois filet revers"

    controleur.start_recording()
    assert controleur.etat == RECORDING

    controleur.stop_recording()
    assert controleur.etat == FINALIZING

    attendre(controleur)
    assert controleur.etat == RESULT
    assert journal.etats == [RECORDING, FINALIZING, RESULT]

    intention = journal.resultats[0]
    assert intention.type_coup_id() == "volee_R"


def test_start_est_idempotent(controleur):
    controleur.start_recording()
    controleur.start_recording()          # auto-repetition clavier
    assert controleur.etat == RECORDING
    assert controleur.recorder.en_cours


def test_appui_trop_court_ignore(controleur):
    journal = Journal()
    journal.brancher(controleur)
    controleur.recorder.resultat = capture(duree_appui=0.1)

    controleur.start_recording()
    controleur.stop_recording()

    assert controleur.etat == IDLE
    assert journal.resultats == []
    assert journal.erreurs == []


def test_audio_silencieux_donne_une_erreur(controleur):
    journal = Journal()
    journal.brancher(controleur)
    controleur.recorder.resultat = capture(silencieuse=True)

    controleur.start_recording()
    controleur.stop_recording()

    assert controleur.etat == ERROR
    assert journal.erreurs == ["rien entendu"]
    assert journal.resultats == []


def test_cancel_jette_tout(controleur):
    controleur.moteur.texte = "point gagnant"
    controleur.start_recording()
    controleur.stop_recording()
    attendre(controleur)
    assert controleur.etat == PARTIAL
    assert controleur.intention is not None

    controleur.cancel()
    assert controleur.etat == IDLE
    assert controleur.intention is None
    assert controleur.recorder.annulations == 1


# --------------------------------------------------------------------------
# Garde-fou de duree
# --------------------------------------------------------------------------


def test_le_garde_fou_coupe_vraiment(controleur):
    """Le recorder cesse d'accumuler ; c'est poll() qui coupe. Sans ca,
    l'interface reste figee sur RECORDING et ca se lit comme un plantage."""
    journal = Journal()
    journal.brancher(controleur)
    controleur.moteur.texte = "point gagnant joueur un service"

    controleur.start_recording()
    assert controleur.etat == RECORDING
    controleur.recorder.depassement = True

    controleur.poll()

    # La capture est coupee sans attendre le relachement : on a quitte
    # RECORDING et le flux est ferme.
    assert not controleur.recorder.en_cours
    assert controleur.etat != RECORDING
    attendre(controleur)
    assert controleur.etat == RESULT


def test_apres_coupure_il_faut_relacher(controleur):
    """La touche est encore enfoncee : l'auto-repetition relancerait une
    capture en boucle."""
    controleur.start_recording()
    controleur.recorder.depassement = True
    controleur.poll()
    attendre(controleur)

    controleur.recorder.depassement = False
    controleur.start_recording()              # auto-repetition
    assert not controleur.recorder.en_cours

    controleur.stop_recording()               # vrai relachement
    controleur.start_recording()
    assert controleur.recorder.en_cours


# --------------------------------------------------------------------------
# Threading
# --------------------------------------------------------------------------


def test_aucun_rappel_avant_poll(controleur):
    """Regle absolue : rien ne remonte a l'UI depuis un thread secondaire."""
    journal = Journal()
    journal.brancher(controleur)
    controleur.moteur.texte = "point gagnant joueur trois filet revers"

    controleur.start_recording()
    controleur.stop_recording()

    limite = time.time() + 5.0
    while time.time() < limite and controleur._resultats.empty():
        time.sleep(0.005)

    assert journal.resultats == []            # le worker a fini, rien n'a fuit
    controleur.poll()
    assert len(journal.resultats) == 1


def test_echec_du_moteur_ne_fait_pas_tomber_l_app(controleur):
    journal = Journal()
    journal.brancher(controleur)
    controleur.moteur.erreur = "cuda out of memory"

    controleur.start_recording()
    controleur.stop_recording()
    attendre(controleur)

    assert controleur.etat == ERROR
    assert journal.erreurs
    assert controleur.disponible          # une panne ponctuelle ne desactive pas


def test_micro_indisponible_desactive_le_module(controleur):
    journal = Journal()
    journal.brancher(controleur)
    controleur.recorder.erreur = ErreurMicro("aucun peripherique")

    controleur.start_recording()

    assert not controleur.disponible
    assert controleur.etat == ERROR
    assert journal.erreurs

    controleur.start_recording()          # ne retente pas indefiniment
    assert controleur.etat == ERROR


# --------------------------------------------------------------------------
# Completion progressive
# --------------------------------------------------------------------------


def test_partial_conserve_et_complete(controleur):
    journal = Journal()
    journal.brancher(controleur)

    controleur.moteur.texte = "point gagnant joueur trois bandeja"
    controleur.start_recording()
    controleur.stop_recording()
    attendre(controleur)

    assert controleur.etat == PARTIAL
    intention, slot = journal.partiels[0]
    assert slot == "zone"
    assert intention.coup_bh == "bandeja"

    controleur.moteur.texte = "filet"
    controleur.start_recording()
    controleur.stop_recording()
    attendre(controleur)

    assert controleur.etat == RESULT
    assert journal.resultats[0].type_coup_id() == "volee_BH_bandeja"
    assert controleur.intention is None


def test_le_prompt_est_restreint_au_noeud_attendu(controleur):
    """Un terme prononce seul est mal reconnu ; l'arbre sait ce qu'il
    attend, on s'en sert pour biaiser le decodeur."""
    controleur.moteur.texte = ("point gagnant joueur trois "
                               "fond de court balle haute")
    controleur.start_recording()
    controleur.stop_recording()
    attendre(controleur)
    assert controleur.etat == PARTIAL
    assert journal_slot(controleur) == "coup_bh"

    controleur.moteur.texte = "bandeja"
    controleur.start_recording()
    controleur.stop_recording()
    attendre(controleur)

    prompt = controleur.moteur.prompts[-1]
    assert prompt is not None
    assert "bandeja" in prompt
    assert "bajada" in prompt          # fond de court : C4 l'autorise
    assert "filet" not in prompt       # la zone est deja resolue
    assert "coup droit" not in prompt
    # « annuler » reste toujours proposable : c'est en completion qu'on a
    # le plus besoin de se retracter.
    assert "annuler" in prompt


def test_annuler_reste_dans_le_biais_en_completion(controleur):
    controleur.moteur.texte = "point gagnant joueur trois bandeja"
    controleur.start_recording()
    controleur.stop_recording()
    attendre(controleur)

    controleur.moteur.texte = "annuler"
    controleur.start_recording()
    controleur.stop_recording()
    attendre(controleur)

    assert "annuler" in controleur.moteur.prompts[-1]
    assert controleur.intention is None      # la saisie est bien jetee


def test_premier_enonce_sans_prompt_contextuel(controleur):
    controleur.moteur.texte = "point gagnant joueur trois filet revers"
    controleur.start_recording()
    controleur.stop_recording()
    attendre(controleur)

    assert controleur.moteur.prompts == [None]     # biais general du config


# --------------------------------------------------------------------------
# Commandes de controle
# --------------------------------------------------------------------------


def test_annuler_depuis_idle_remonte_a_l_app(controleur):
    journal = Journal()
    journal.brancher(controleur)
    controleur.moteur.texte = "annuler"

    controleur.start_recording()
    controleur.stop_recording()
    attendre(controleur)

    assert journal.controles == ["annuler"]
    assert controleur.etat == IDLE


def test_annuler_depuis_partial_jette_la_saisie(controleur):
    journal = Journal()
    journal.brancher(controleur)

    controleur.moteur.texte = "point gagnant joueur trois bandeja"
    controleur.start_recording()
    controleur.stop_recording()
    attendre(controleur)
    assert controleur.intention is not None

    controleur.moteur.texte = "annuler"
    controleur.start_recording()
    controleur.stop_recording()
    attendre(controleur)

    assert controleur.intention is None
    assert controleur.etat == IDLE
    assert journal.controles == []      # on n'efface pas le point precedent


# --------------------------------------------------------------------------
# Roster
# --------------------------------------------------------------------------


def test_roster_sans_equipes_est_signale(controleur, caplog):
    controleur.set_roster(["pascal", "arnaud", "philippe", "alex"])
    assert "desactivee" in caplog.text


def test_roster_avec_equipes_ne_previent_pas(controleur, caplog):
    controleur.set_roster(ROSTER)
    assert "desactivee" not in caplog.text
