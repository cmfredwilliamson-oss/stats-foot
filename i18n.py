"""
i18n.py - Langue de l'application.

Tous les textes sont écrits en français dans le code et passent par T("texte").
Les traductions anglaises sont dans traductions.json : {"texte français": {"en": "English text"}}.
Un texte sans traduction s'affiche en français.
Les variables s'écrivent entre accolades : T("{n} matchs", n=12).
"""

import json
import os

import streamlit as st

LANGUES = {"fr": "🇫🇷 Français", "en": "🇬🇧 English"}

_CHEMIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "traductions.json")
_JOURNAL = os.environ.get("I18N_MANQUANTS")      # tests : fichier où noter les textes non traduits


@st.cache_resource
def _charger(mtime):
    try:
        with open(_CHEMIN, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def _dico():
    try:
        return _charger(os.path.getmtime(_CHEMIN))
    except OSError:
        return {}


def langue():
    return st.session_state.get("langue", "fr")


def T(texte, **valeurs):
    lg = langue()
    if not isinstance(texte, str):
        return texte
    trad = texte
    if lg != "fr":
        entree = _dico().get(texte)
        if entree and entree.get(lg):
            trad = entree[lg]
        elif _JOURNAL and texte.strip():
            with open(_JOURNAL, "a", encoding="utf-8") as f:
                f.write(json.dumps(texte, ensure_ascii=False) + "\n")
    if valeurs:
        try:
            return trad.format(**valeurs)
        except (KeyError, IndexError, ValueError):
            return texte.format(**valeurs)
    return trad


def langue_navigateur():
    try:
        loc = (st.context.locale or "")[:2].lower()
    except Exception:
        loc = ""
    return loc if loc in LANGUES else "fr"


def initialiser():
    """Langue choisie : ?lang=xx dans l'adresse, sinon choix précédent, sinon langue du navigateur."""
    ss = st.session_state
    lg = st.query_params.get("lang")
    if lg in LANGUES:
        ss["langue"] = lg
    ss.setdefault("langue", langue_navigateur())


def selecteur(conteneur):
    def _changer():
        st.query_params["lang"] = st.session_state["_choix_langue"]
        st.session_state["langue"] = st.session_state["_choix_langue"]
    codes = list(LANGUES)
    conteneur.selectbox("🌐", codes, index=codes.index(langue()), format_func=LANGUES.get,
                        key="_choix_langue", on_change=_changer, label_visibility="collapsed")
