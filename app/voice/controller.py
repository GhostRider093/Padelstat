"""
Orchestration du module vocal : machine a etats et threads.

**Regle absolue : aucun appel Tkinter depuis un thread secondaire.** Tout
remonte vers l'UI par `_resultats`, depilee par `poll()` dans le thread
principal. C'est la seule facon d'avoir une transcription qui tourne pendant
que la video continue.

Deux threads suffisent — capture, puis transcription au relachement. Mesure :
faster-whisper `small` sur GPU tourne a x0,08 temps reel, soit ~160 ms pour
un enonce de 2 s. Transcrire au fil de l'eau ajouterait un thread, un tampon
partiel et une classe entiere de bugs de synchronisation, pour rien.

Voir SPEC_MODULE_VOCAL_PTT_V2.md sections 4 et 8.
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from typing import Callable, Optional

from app.voice import arbre, vocabulaire
from app.voice.config import VoiceConfig
from app.voice.engines import creer_moteur
from app.voice.parser import Commande, Intention, parser
from app.voice.recorder import ErreurMicro, PTTRecorder

logger = logging.getLogger(__name__)

IDLE = "IDLE"
RECORDING = "RECORDING"
FINALIZING = "FINALIZING"
RESULT = "RESULT"
PARTIAL = "PARTIAL"
ERROR = "ERROR"


def _rien(*_args, **_kwargs):
    pass


class VoiceController:
    """Pilote le module vocal depuis les evenements clavier.

    Cycle : `warmup()` une fois au demarrage, puis `start_recording()` /
    `stop_recording()` sur KeyPress / KeyRelease, et `poll()` appele
    regulierement depuis la boucle Tk.
    """

    def __init__(self, config: Optional[VoiceConfig] = None,
                 roster=None,
                 on_result: Callable[[Intention], None] = _rien,
                 on_partial: Callable[[Intention, str], None] = _rien,
                 on_control: Callable[[str], None] = _rien,
                 on_state_change: Callable[[str], None] = _rien,
                 on_error: Callable[[str], None] = _rien,
                 on_motcle: Callable[[str], None] = _rien) -> None:
        self.config = config or VoiceConfig()
        self.roster = roster or []

        self.on_result = on_result
        self.on_partial = on_partial
        self.on_control = on_control
        self.on_state_change = on_state_change
        self.on_error = on_error
        self.on_motcle = on_motcle

        self.recorder = PTTRecorder(self.config)
        self.moteur = creer_moteur(self.config)
        self.ecoute = None          # ecoute permanente, optionnelle

        self._resultats: queue.Queue = queue.Queue()
        self._etat = IDLE
        self._pret = False
        self._occupe = False
        self._disponible = True          # faux si le micro ou le modele manque
        self._intention: Optional[Intention] = None

        # Apres une coupure automatique, la touche est encore enfoncee :
        # l'auto-repetition clavier relancerait une capture en boucle.
        self._attend_relachement = False

    # ---------------------------------------------------------------- etat

    @property
    def etat(self) -> str:
        return self._etat

    @property
    def pret(self) -> bool:
        return self._pret

    @property
    def disponible(self) -> bool:
        """Faux si le module s'est desactive. L'app reste utilisable."""
        return self._disponible

    @property
    def intention(self) -> Optional[Intention]:
        """L'intention en cours de construction, en etat PARTIAL."""
        return self._intention

    def _changer_etat(self, etat: str) -> None:
        if etat == self._etat:
            return
        self._etat = etat

        # L'ecoute reprend des que le micro est rendu. On la laisse muette
        # pendant la capture et la transcription pour ne pas dedoubler.
        if self.ecoute is not None and etat not in (RECORDING, FINALIZING):
            self.ecoute.reprendre()

        self.on_state_change(etat)

    # -------------------------------------------------------------- warmup

    def warmup(self) -> None:
        """Charge le modele et le fait tourner une fois a vide.

        Bloquant. A appeler UNE FOIS au demarrage, jamais a la premiere
        commande : c'est tout l'objet du warmup.
        """
        try:
            self.moteur.warmup()
            self._pret = True
        except Exception as erreur:
            self._desactiver(f"modele indisponible : {erreur}")

    def warmup_en_arriere_plan(self) -> None:
        """Warmup sur un thread, pour ne pas figer l'UI au demarrage.

        L'etat remonte par la queue : `poll()` emettra `on_state_change`.
        """
        threading.Thread(target=self._warmup_worker, daemon=True).start()

    def _warmup_worker(self) -> None:
        debut = time.perf_counter()
        try:
            self.moteur.warmup()
        except Exception as erreur:
            self._resultats.put(("indisponible", f"modele : {erreur}"))
            return
        self._resultats.put(("pret", time.perf_counter() - debut))

    # ------------------------------------------------- ecoute permanente

    def demarrer_ecoute(self) -> bool:
        """Ouvre le micro en permanence pour guetter le mot-cle.

        Vient a cote du push-to-talk, jamais a sa place : le PTT reste le
        mode d'annotation. Le mot-cle sert au controle de lecture, ou une
        erreur ne coute rien.
        """
        if self.ecoute is not None or not self._disponible:
            return False

        from app.voice.ecoute import EcoutePermanente

        try:
            self.ecoute = EcoutePermanente(
                self.config, self.moteur, self._segment_entendu)
            self.ecoute.demarrer()
            return True
        except Exception as erreur:
            self.ecoute = None
            logger.warning("ecoute permanente indisponible : %s", erreur)
            self.on_error(f"écoute permanente indisponible : {erreur}")
            return False

    def arreter_ecoute(self) -> None:
        if self.ecoute is not None:
            self.ecoute.arreter()
            self.ecoute = None

    def _segment_entendu(self, texte: str, commande) -> None:
        """Thread de l'ecoute. Rien ne remonte a l'UI d'ici."""
        self._resultats.put(("ecoute", (texte, commande)))

    def set_roster(self, roster) -> None:
        """Met a jour les joueurs du match.

        Les prenoms deviennent des synonymes, et C1/C2 redeviennent
        applicables. Sans equipes dans le roster, C2 est desactivee — et
        signalee, jamais contournee en silence.
        """
        self.roster = roster or []
        if self.roster and arbre.roster_sans_equipes(self.roster):
            logger.warning(
                "roster sans equipes : la contrainte « defenseur adverse » "
                "est desactivee")

    # ------------------------------------------------------------- capture

    def start_recording(self) -> None:
        """KeyPress. Idempotent : l'auto-repetition clavier ne doit rien
        relancer ni perdre ce qui est deja capture."""
        if not self._disponible or not self._pret:
            return
        if self._occupe or self._attend_relachement:
            return
        if self.recorder.en_cours:
            return

        # Deux flux sur le meme micro se genent, et on ne veut pas
        # transcrire deux fois la meme phrase.
        if self.ecoute is not None:
            self.ecoute.suspendre()

        try:
            self.recorder.demarrer()
        except ErreurMicro as erreur:
            self._desactiver(f"micro indisponible : {erreur}")
            if self.ecoute is not None:
                self.ecoute.reprendre()
            return

        self._changer_etat(RECORDING)

    def stop_recording(self) -> None:
        """KeyRelease. Declenche flush et parsing."""
        self._attend_relachement = False
        self._finaliser(coupe=False)

    def cancel(self) -> None:
        """ESC. Jette l'audio ET l'intention en cours, retour a IDLE."""
        self.recorder.annuler()
        self._intention = None
        self._attend_relachement = False
        self._changer_etat(IDLE)

    def shutdown(self) -> None:
        try:
            self.arreter_ecoute()
            self.recorder.fermer()
        finally:
            self.moteur.fermer()
            self._pret = False

    # ---------------------------------------------------------------- poll

    def poll(self) -> None:
        """Depuis `root.after(30, ...)`. Le seul endroit qui touche a l'UI.

        Assure aussi le garde-fou de duree : le recorder cesse d'accumuler
        au-dela du plafond, mais c'est ici que la capture est reellement
        coupee. Sans ca, l'interface reste figee sur RECORDING jusqu'au
        relachement, ce qui se lit comme un plantage.
        """
        if self.recorder.en_cours and self.recorder.depassement:
            self._attend_relachement = True
            self._finaliser(coupe=True)

        try:
            while True:
                genre, charge = self._resultats.get_nowait()
                self._traiter(genre, charge)
        except queue.Empty:
            pass

    # ------------------------------------------------------------- interne

    def _finaliser(self, coupe: bool) -> None:
        if not self.recorder.en_cours:
            return

        capture = self.recorder.arreter()

        if not coupe and capture.duree_appui_s < self.config.duree_min_appui_ms / 1000:
            # Anti-rebond : ignore silencieusement, sans perdre le PARTIAL.
            self._changer_etat(PARTIAL if self._intention else IDLE)
            return

        if capture.vide or capture.silencieuse:
            self._erreur("rien entendu")
            return

        self._occupe = True
        self._changer_etat(FINALIZING)
        threading.Thread(target=self._transcrire_worker,
                         args=(capture, self._intention),
                         daemon=True).start()

    def _transcrire_worker(self, capture, base) -> None:
        """Thread de travail. Aucun appel UI, aucune ecriture d'etat
        partagee : le resultat repart par la queue."""
        try:
            transcription = self.moteur.transcrire(
                capture.audio, prompt=self._prompt_contextuel(base))
            resultat = parser(
                transcription.texte,
                roster=self.roster,
                base=base,
                confiance_acoustique=transcription.confiance_acoustique,
                seuil=self.config.seuil_fuzzy,
            )
            self._resultats.put(("parse", (resultat, transcription)))
        except Exception as erreur:                      # jamais de crash
            logger.exception("echec de transcription")
            self._resultats.put(("erreur", str(erreur)))

    def _prompt_contextuel(self, base) -> Optional[str]:
        """Biais de decodage restreint au noeud attendu.

        Mesure : un terme prononce seul est bien moins reconnu qu'en phrase
        — « lob » isole ressort « nouvelle » ou « l'objet », alors qu'il ne
        rate jamais en phrase. Or completer un slot manquant, c'est
        precisement repondre par un mot isole. L'arbre sait ce qu'il attend,
        on l'utilise pour biaiser le decodeur.
        """
        if base is None:
            return None
        noeud = arbre.noeud_courant(base, self.roster)
        if noeud is None:
            return None

        termes = list(vocabulaire.termes_du_noeud(noeud))

        # Les commandes de controle restent toujours dans le biais. Sans
        # ca, « annuler » etait defavorise precisement en completion, le
        # moment ou l'on a le plus besoin de se retracter.
        for synonymes in vocabulaire.CONTROLE.values():
            termes.extend(str(t) for t in synonymes)

        if not termes:
            return None
        return "Commande de padel. " + ", ".join(termes) + "."

    def _traiter(self, genre: str, charge) -> None:
        """Thread principal uniquement."""
        if genre == "pret":
            self._pret = True
            logger.info("moteur pret en %.1f s", charge)
            self._changer_etat(IDLE)
            return

        if genre == "indisponible":
            self._desactiver(str(charge))
            return

        if genre == "erreur":
            self._occupe = False
            self._erreur(str(charge))
            return

        if genre == "ecoute":
            texte, commande = charge
            print(f"[ECOUTE] {texte!r}"
                  + (f"   << {commande.upper()}" if commande else ""))
            if commande:
                self.on_motcle(commande)
            return

        if genre == "parse":
            self._occupe = False
            resultat, transcription = charge
            self._tracer(resultat, transcription)
            self._appliquer(resultat)

    def _tracer(self, resultat, transcription) -> None:
        """Trace console : ce qui a ete entendu, et ce qui en a ete compris.

        Le journal de l'interface ne sort pas de l'interface. Sans cette
        trace, un desaccord entre ce qu'on a dit et ce qui a ete annote est
        indiagnosticable.
        """
        print(f"[VOCAL] entendu   : {transcription.texte!r}"
              f"   (confiance {transcription.confiance_acoustique:.2f},"
              f" {transcription.duree_calcul_s * 1000:.0f} ms)")

        if isinstance(resultat, Commande):
            print(f"[VOCAL] compris   : commande {resultat.nom}")
            return

        print(f"[VOCAL] compris   : {resultat.slots_resolus()}")
        if resultat.deduits:
            print(f"[VOCAL] deduits   : {sorted(resultat.deduits)}")
        if resultat.ignores:
            print(f"[VOCAL] IGNORES   : {resultat.ignores}")
        if not resultat.est_complete(self.roster):
            print(f"[VOCAL] manque    : {resultat.slot_attendu(self.roster)}")

    def _appliquer(self, resultat) -> None:
        # Commande de controle : ne passe jamais par l'arbre.
        if isinstance(resultat, Commande):
            if resultat.nom == "annuler" and self._intention is not None:
                self._intention = None          # annule la saisie en cours
                self._changer_etat(IDLE)
            else:
                self._changer_etat(IDLE)
                self.on_control(resultat.nom)
            return

        if resultat.est_complete(self.roster):
            self._intention = None
            self._changer_etat(RESULT)
            self.on_result(resultat)
            return

        # Incomplet : on garde l'intention et on demande LE noeud courant,
        # jamais une liste de slots manquants.
        self._intention = resultat
        slot = resultat.slot_attendu(self.roster)
        self._changer_etat(PARTIAL)
        self.on_partial(resultat, slot)

    def _erreur(self, message: str) -> None:
        self._changer_etat(ERROR)
        self.on_error(message)

    def _desactiver(self, message: str) -> None:
        """Le module se retire, l'application reste utilisable au clavier."""
        self._disponible = False
        self._pret = False
        logger.error("module vocal desactive : %s", message)
        self._changer_etat(ERROR)
        self.on_error(message)
