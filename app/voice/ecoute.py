"""
Écoute permanente avec mot-clé.

**Ce module contredit délibérément le §2 de la spec** (« pas de VAD, pas de
wake-word, pas de micro ouvert »). Il vient *à côté* du push-to-talk, pas à
sa place : le PTT reste le mode d'annotation, où une erreur coûte cher.
L'écoute permanente sert au contrôle de lecture, où elle ne coûte rien.

Principe : le micro reste ouvert, mais Whisper ne tourne pas en continu. Un
seuil d'énergie découpe les segments de parole, et seuls ces segments sont
transcrits. Sur un micro silencieux, le GPU ne fait rien.

Mesure du 28/07/2026 : « OK STAT » ressort exact 17 fois sur 17, RMS de
0,0058 à 0,0135. C'est ce qui rend le mot-clé utilisable tel quel.
"""

from __future__ import annotations

import logging
import threading
from collections import deque
from typing import Callable, Optional

import numpy as np
from rapidfuzz import fuzz

from app.voice.normalizer import normaliser, ngrammes

logger = logging.getLogger(__name__)

#: Commandes reconnues en ecoute permanente, et ce qu'elles declenchent.
#:
#: Deux commandes distinctes plutot qu'une bascule : un declenchement
#: parasite devient sans effet — mettre en pause une video deja en pause ne
#: fait rien — la ou une bascule laissait dans un etat imprevisible. Et on
#: peut prononcer le mot sans redouter l'action inverse.
COMMANDES = {
    "pause": ["ok stat"],                       # mesure : 17/17 exact

    # Variantes relevees en session : « reprise » ressortait deforme faute
    # de figurer dans le biais de decodage. Le prompt est corrige, mais on
    # garde les formes mesurees — une reprise declenchee a tort ne coute
    # rien, une reprise ratee oblige a reprendre la souris.
    "reprise": ["reprise", "reprend", "reprends",
                "au prise", "bonne prise", "bonne paise"],

    # Deplacements. Le normaliseur convertit les chiffres en lettres, donc
    # « 3 secondes » et « trois secondes » sont la meme forme.
    "avance_3": ["trois secondes", "avance trois secondes"],
    "avance_5": ["cinq secondes", "avance cinq secondes"],
    "recul_3": ["recule trois secondes", "arriere trois secondes"],
    "recul_5": ["recule cinq secondes", "arriere cinq secondes"],
}

MOT_CLE = "ok stat"   # conserve : c'est celui qui a ete mesure

#: Sous ce niveau, on considère qu'il n'y a pas de parole. Choisi sous le
#: RMS le plus faible mesuré sur le mot-clé (0,0058) : mieux vaut une
#: transcription inutile qu'un mot-clé raté.
SEUIL_RMS = 0.004

#: Silence qui clôt un segment. C'est la principale source de latence
#: ressentie : elle s'ajoute intégralement au temps de transcription.
#:
#: Mais il ne peut pas être constant. Mesuré : à 320 ms, « OK STAT » était
#: coupé après « OK » — la micro-pause entre les deux mots suffisait à
#: clore le segment, et le mot-clé n'était jamais reconnu. Un segment court
#: est probablement une phrase inachevée : on lui laisse plus de temps.
SILENCE_FIN_MS = 320
SILENCE_FIN_COURT_MS = 600
DUREE_COURTE_S = 0.9

#: Audio conservé avant le déclenchement : sans lui, la première syllabe
#: est mangée, et « ok stat » devient « stat ».
PRE_ROLL_MS = 300

DUREE_MAX_SEGMENT_S = 5.0
DUREE_MIN_SEGMENT_S = 0.3

#: Le mot-clé peut être noyé dans une phrase : on cherche un n-gramme, pas
#: une égalité. « ok ok stat » doit déclencher.
SEUIL_MOTCLE = 85

#: Biais de décodage de l'écoute.
#:
#: Il doit contenir toutes les commandes — sans « reprise » dedans, elle
#: ressortait en « au prise » deux fois sur trois. Mais **il ne doit
#: surtout pas les répéter** : mesuré, un prompt qui les listait deux fois
#: faisait régurgiter le prompt lui-même par le modèle, et chaque segment
#: ressortait « OK Stat. Reprise. » quoi qu'on ait dit.
#:
#: Une mention par commande, dans une phrase naturelle. Pas plus.
PROMPT = ("Commandes vocales : OK Stat pour la pause, reprise pour relancer, "
          "trois secondes, cinq secondes.")


#: Whisper hallucine ces phrases sur du quasi-silence : elles viennent de
#: son corpus d'entrainement, truffe de sous-titres. Elles ne matchent
#: aucune commande, mais les journaliser noie la trace et les compter
#: fausserait toute mesure du taux de declenchement.
HALLUCINATIONS = (
    "amara",
    "sous titres",
    "sous titrage",
    "merci d avoir regarde",
    "abonnez vous",
)


def est_hallucination(texte: str) -> bool:
    forme = normaliser(texte)
    return any(marqueur in forme for marqueur in HALLUCINATIONS)


def _formes(commande: str) -> list:
    """Formes normalisées d'une commande, dont la variante collée.

    Les 17 mesures donnent toutes « ok stat » en deux mots, mais rien
    n'interdit au moteur de les coller un jour.
    """
    formes = []
    for expression in COMMANDES[commande]:
        forme = normaliser(expression)
        if not forme:
            continue
        formes.append(forme)
        if " " in forme:
            formes.append(forme.replace(" ", ""))
    return formes


FORMES = {commande: _formes(commande) for commande in COMMANDES}
TAILLE_MAX = max(len(f.split()) for formes in FORMES.values() for f in formes)


def detecter_commande(texte: str, seuil: int = SEUIL_MOTCLE) -> Optional[str]:
    """Quelle commande d'écoute a été prononcée, s'il y en a une ?

    On cherche un n-gramme, pas une égalité : la commande peut être noyée
    dans une phrase, et « ok ok stat » — mesuré — doit déclencher.

    **Si deux commandes différentes matchent le même segment, on n'en
    exécute aucune.** Mesuré : un prompt trop répétitif faisait régurgiter
    « OK Stat. Reprise. » au modèle, et le départage arbitraire mettait la
    vidéo en pause à chaque parole. Mieux vaut ne rien faire que se tromper
    d'action — l'utilisateur répétera.
    """
    mots = normaliser(texte).split()
    if not mots:
        return None

    trouves = []
    for debut, longueur, ngramme in ngrammes(mots, taille_max=TAILLE_MAX):
        for commande, formes in FORMES.items():
            for forme in formes:
                if longueur != len(forme.split()):
                    continue
                score = fuzz.ratio(ngramme, forme)
                if score >= seuil:
                    trouves.append((debut, longueur, commande, score))

    # Deux commandes peuvent matcher au MEME endroit — « recule trois
    # secondes » contient « trois secondes » — ou a des endroits
    # DIFFERENTS. Le premier cas se tranche par la longueur, comme dans
    # l'extraction ; le second est une vraie ambiguite.
    retenues, consommes = set(), set()
    for debut, longueur, commande, _ in sorted(
            trouves, key=lambda t: (-t[1], -t[3])):
        positions = set(range(debut, debut + longueur))
        if positions & consommes:
            continue                # recouvre un match plus long : ignore
        consommes |= positions
        retenues.add(commande)

    if len(retenues) != 1:
        return None                 # rien reconnu, ou deux commandes
    return retenues.pop()


def contient_motcle(texte: str, seuil: int = SEUIL_MOTCLE) -> bool:
    """Rétrocompatibilité : une commande d'écoute a-t-elle été prononcée ?"""
    return detecter_commande(texte, seuil) is not None


class EcoutePermanente:
    """Micro ouvert, découpage par énergie, transcription à la demande.

    `on_segment` est appelé depuis un thread de travail avec le texte
    transcrit ; c'est à l'appelant de le remonter à l'UI par une queue.
    """

    def __init__(self, config, moteur,
                 on_segment: Callable[[str, Optional[str]], None],
                 seuil_rms: float = SEUIL_RMS):
        self.config = config
        self.moteur = moteur
        self.on_segment = on_segment
        self.seuil_rms = seuil_rms

        self._stream = None
        self._suspendu = False
        self._verrou = threading.Lock()

        chunk_ms = config.taille_chunk_ms
        self._pre_roll = deque(maxlen=max(1, PRE_ROLL_MS // chunk_ms))
        self._segment: list = []
        self._en_parole = False
        self._silence_ms = 0
        self._max_frames = int(config.sample_rate * DUREE_MAX_SEGMENT_S)

        self._a_transcrire: deque = deque()
        self._reveil = threading.Event()
        self._arret = threading.Event()
        self._worker: Optional[threading.Thread] = None

    # ------------------------------------------------------------- cycle

    @property
    def active(self) -> bool:
        return self._stream is not None

    def demarrer(self) -> None:
        if self.active:
            return

        import sounddevice as sd

        self._arret.clear()
        self._worker = threading.Thread(target=self._boucle, daemon=True)
        self._worker.start()

        self._stream = sd.InputStream(
            device=self.config.peripherique_audio,
            samplerate=self.config.sample_rate,
            channels=1,
            dtype="float32",
            blocksize=self.config.taille_chunk,
            callback=self._callback,
        )
        self._stream.start()
        logger.info("écoute permanente démarrée (mot-clé « %s »)", MOT_CLE)

    def arreter(self) -> None:
        self._arret.set()
        self._reveil.set()
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as erreur:
                logger.debug("fermeture écoute : %s", erreur)
            finally:
                self._stream = None
        self._reinitialiser()

    def suspendre(self) -> None:
        """Pendant un push-to-talk : deux flux sur le même micro se gênent,
        et on ne veut pas transcrire deux fois la même phrase."""
        self._suspendu = True
        self._reinitialiser()

    def reprendre(self) -> None:
        self._suspendu = False

    # ----------------------------------------------------------- capture

    def _callback(self, indata, frames, horodatage, statut) -> None:
        """Thread audio. Rien de coûteux ici : un RMS et des append."""
        if self._suspendu:
            return

        bloc = indata[:, 0].copy() if indata.ndim > 1 else indata.copy()
        niveau = float(np.sqrt(np.mean(np.square(bloc))))

        if niveau >= self.seuil_rms:
            if not self._en_parole:
                self._en_parole = True
                self._segment = list(self._pre_roll)   # rattrape l'attaque
            self._silence_ms = 0
            self._segment.append(bloc)
        elif self._en_parole:
            self._segment.append(bloc)                 # laisse retomber
            self._silence_ms += self.config.taille_chunk_ms
            if self._silence_ms >= self._silence_requis():
                self._clore_segment()
        else:
            self._pre_roll.append(bloc)

        if self._en_parole and sum(len(b) for b in self._segment) > self._max_frames:
            self._clore_segment()

    def _silence_requis(self) -> int:
        """Silence à attendre avant de clore, selon ce qui est déjà capté.

        « OK STAT » dure moins d'une seconde et porte une pause au milieu :
        le clore sur un silence court le ampute de son second mot.
        """
        frames = sum(len(bloc) for bloc in self._segment)
        duree = frames / self.config.sample_rate
        return (SILENCE_FIN_COURT_MS if duree < DUREE_COURTE_S
                else SILENCE_FIN_MS)

    def _clore_segment(self) -> None:
        segment, self._segment = self._segment, []
        self._en_parole = False
        self._silence_ms = 0
        self._pre_roll.clear()

        if not segment:
            return
        audio = np.concatenate(segment)
        if len(audio) < self.config.sample_rate * DUREE_MIN_SEGMENT_S:
            return

        with self._verrou:
            self._a_transcrire.append(audio)
        self._reveil.set()

    def _reinitialiser(self) -> None:
        self._segment = []
        self._en_parole = False
        self._silence_ms = 0
        self._pre_roll.clear()
        with self._verrou:
            self._a_transcrire.clear()

    # ---------------------------------------------------------- worker

    def _boucle(self) -> None:
        """Transcrit les segments hors du thread audio."""
        while not self._arret.is_set():
            self._reveil.wait(timeout=0.2)
            self._reveil.clear()

            while True:
                with self._verrou:
                    if not self._a_transcrire:
                        break
                    audio = self._a_transcrire.popleft()

                if self._suspendu or self._arret.is_set():
                    continue
                try:
                    resultat = self.moteur.transcrire(audio, prompt=PROMPT)
                except Exception as erreur:
                    logger.warning("écoute : transcription échouée (%s)", erreur)
                    continue

                texte = resultat.texte.strip()
                if not texte or est_hallucination(texte):
                    continue
                self.on_segment(texte, detecter_commande(texte))
