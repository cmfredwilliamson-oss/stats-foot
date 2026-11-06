"""
Stats & Prédictions Foot - application Streamlit.

Lancement :  py -m streamlit run app.py      (ou : streamlit run app.py)
Données   :  rechargées automatiquement toutes les 3 h

Le menu de gauche reprend les 28 états du notebook STAT_DES_MATCHS, avec la même numérotation,
puis les prédictions et les données brutes.
"""

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

import time

import abonnement as ab
import i18n
import stats_core as sc
from i18n import T
from notifications import notifier_visite

st.set_page_config(page_title="Stats & Prédictions Foot", page_icon="⚽", layout="wide",
                   initial_sidebar_state="collapsed")

i18n.initialiser()  # langue choisie par l'utilisateur
notifier_visite()   # e-mail à chaque nouvelle visite (si les secrets e-mail sont configurés)

BLEU = "#3987e5"                                   # série unique (bleu adapté au thème sombre)
TEXTE_GRAPH = "#c3c2b7"                            # libellés des graphiques sur fond sombre
COULEURS_1X2 = ["#3987e5", "#d95926", "#199e70"]   # domicile / nul / extérieur (thème sombre)

# =========================================================
# DÉFINITION DES ÉTATS DU NOTEBOOK
# type : "champ" (par championnat), "equipe" (par équipe),
#        "resultats" (états 12-14), "forme" (états 27-28)
# =========================================================
ETATS = [
    (4,  "BTTS par championnat", "champ", "BTTS - les deux équipes marquent", "Matchs BTTS", "% BTTS",
     "Matchs où les deux équipes ont marqué."),
    (5,  "BTTS par équipe", "equipe", "BTTS - les deux équipes marquent", "Matchs BTTS", "% BTTS",
     "Matchs de l'équipe où les deux équipes ont marqué."),
    (6,  "Au moins 2 buts dans le match (over 1.5) par championnat", "champ",
     "Au moins 2 buts dans le match (over 1.5)", "Matchs à 2 buts ou +", "% over 1.5",
     "Matchs avec au moins 2 buts au total."),
    (7,  "Au moins 2 buts dans le match (over 1.5) par équipe", "equipe",
     "Au moins 2 buts dans le match (over 1.5)", "Matchs à 2 buts ou +", "% over 1.5",
     "Matchs de l'équipe avec au moins 2 buts au total (marqués + encaissés)."),
    (8,  "Au moins 3 buts dans le match (over 2.5) par championnat", "champ",
     "Au moins 3 buts dans le match (over 2.5)", "Matchs à 3 buts ou +", "% over 2.5",
     "Matchs avec au moins 3 buts au total."),
    (9,  "Au moins 3 buts dans le match (over 2.5) par équipe", "equipe",
     "Au moins 3 buts dans le match (over 2.5)", "Matchs à 3 buts ou +", "% over 2.5",
     "Matchs de l'équipe avec au moins 3 buts au total."),
    (10, "Au moins 4 buts dans le match (over 3.5) par championnat", "champ",
     "Au moins 4 buts dans le match (over 3.5)", "Matchs à 4 buts ou +", "% over 3.5",
     "Matchs avec au moins 4 buts au total."),
    (11, "Au moins 4 buts dans le match (over 3.5) par équipe", "equipe",
     "Au moins 4 buts dans le match (over 3.5)", "Matchs à 4 buts ou +", "% over 3.5",
     "Matchs de l'équipe avec au moins 4 buts au total."),
    (12, "Équipes avec le plus de victoires", "resultats", "W", "Victoires", "% victoires",
     "Classement au pourcentage de victoires ; à égalité, le plus grand nombre de victoires passe devant."),
    (13, "Équipes avec le plus de défaites", "resultats", "L", "Défaites", "% défaites",
     "Classement au pourcentage de défaites ; à égalité, le plus grand nombre de défaites passe devant."),
    (14, "Équipes avec le plus de matchs nuls", "resultats", "D", "Nuls", "% nuls",
     "Classement au pourcentage de nuls ; à égalité, le plus grand nombre de nuls passe devant."),
    (15, "Championnats : plus de buts en 2e qu'en 1re période", "champ",
     "Plus de buts en 2e qu'en 1re période", "Matchs 2e période > 1re", "% 2e > 1re",
     "Matchs où la 2e période compte plus de buts que la 1re (les deux équipes confondues)."),
    (16, "Équipes : plus de buts en 2e qu'en 1re période", "equipe",
     "Plus de buts en 2e qu'en 1re période", "Matchs 2e période > 1re", "% 2e > 1re",
     "Matchs de l'équipe où la 2e période compte plus de buts que la 1re."),
    (17, "Championnats : plus de buts en 1re qu'en 2e période", "champ",
     "Plus de buts en 1re qu'en 2e période", "Matchs 1re période > 2e", "% 1re > 2e",
     "Matchs où la 1re période compte plus de buts que la 2e."),
    (18, "Équipes : plus de buts en 1re qu'en 2e période", "equipe",
     "Plus de buts en 1re qu'en 2e période", "Matchs 1re période > 2e", "% 1re > 2e",
     "Matchs de l'équipe où la 1re période compte plus de buts que la 2e."),
    (19, "Championnats : autant de buts dans les deux périodes", "champ",
     "Autant de buts dans les deux périodes", "Matchs périodes égales", "% périodes égales",
     "Matchs avec le même nombre de buts dans chaque période (0-0 inclus)."),
    (20, "Équipes : autant de buts dans les deux périodes", "equipe",
     "Autant de buts dans les deux périodes", "Matchs périodes égales", "% périodes égales",
     "Matchs de l'équipe avec le même nombre de buts dans chaque période (0-0 inclus)."),
    (21, "Équipes qui marquent au moins 1 but", "equipe", "L'équipe marque au moins 1 but",
     "Matchs avec au moins 1 but marqué", "% au moins 1 but", "Seuls les buts marqués par l'équipe comptent."),
    (22, "Équipes qui marquent au moins 2 buts", "equipe", "L'équipe marque au moins 2 buts",
     "Matchs avec au moins 2 buts marqués", "% au moins 2 buts", "Seuls les buts marqués par l'équipe comptent."),
    (23, "Équipes qui marquent au moins 3 buts", "equipe", "L'équipe marque au moins 3 buts",
     "Matchs avec au moins 3 buts marqués", "% au moins 3 buts", "Seuls les buts marqués par l'équipe comptent."),
    (24, "Équipes qui marquent au moins 4 buts", "equipe", "L'équipe marque au moins 4 buts",
     "Matchs avec au moins 4 buts marqués", "% au moins 4 buts", "Seuls les buts marqués par l'équipe comptent."),
    (25, "Équipes qui marquent moins de 2 buts (0 ou 1 but)", "equipe", "L'équipe marque moins de 2 buts",
     "Matchs avec 0 ou 1 but marqué", "% moins de 2 buts", "Seuls les buts marqués par l'équipe comptent."),
    (26, "Équipes qui marquent moins de 1 but (0 but)", "equipe", "L'équipe ne marque pas (moins de 1 but)",
     "Matchs sans marquer", "% sans marquer", "Matchs où l'équipe n'a marqué aucun but."),
    (27, "Top équipes : victoires sur les 5 derniers matchs", "forme", "W", "", "", ""),
    (28, "Top équipes : défaites sur les 5 derniers matchs", "forme", "L", "", "", ""),
    (41, "Top équipes : matchs nuls sur les 5 derniers matchs", "forme", "D", "", "", ""),
]
BONUS = [
    (29, "Équipes qui n'encaissent pas (clean sheet)", "equipe", "L'équipe n'encaisse pas (clean sheet)",
     "Matchs sans encaisser", "% clean sheet", "Matchs où l'équipe n'a encaissé aucun but."),
    (30, "Équipes qui encaissent au moins 1 but", "equipe", "L'équipe encaisse au moins 1 but",
     "Matchs avec au moins 1 but encaissé", "% au moins 1 but encaissé",
     "Seuls les buts encaissés par l'équipe comptent."),
    (31, "Équipes qui encaissent au moins 2 buts", "equipe", "L'équipe encaisse au moins 2 buts",
     "Matchs avec au moins 2 buts encaissés", "% au moins 2 buts encaissés",
     "Seuls les buts encaissés par l'équipe comptent."),
    (32, "Équipes qui encaissent au moins 3 buts", "equipe", "L'équipe encaisse au moins 3 buts",
     "Matchs avec au moins 3 buts encaissés", "% au moins 3 buts encaissés",
     "Seuls les buts encaissés par l'équipe comptent."),
]


TITRES_TICKETS = {"BTTS - les deux équipes marquent": "Les deux équipes marquent (BTTS)",
                  "12 Yes - victoire et les deux équipes marquent": "12 Yes (victoire + les 2 marquent)"}

NB_EQUIPES = [10, 20, 30, 50, 100, 0]   # 0 = toutes les équipes

# États 33 à 40 : moyennes et médianes de buts
# (numéro, titre, niveau "equipe"/"champ", sens "for"/"against", mesure "mean"/"median")
ETATS_STATS = [
    (33, "Moyenne de buts marqués par équipe", "equipe", "for", "mean"),
    (34, "Moyenne de buts marqués par championnat", "champ", "for", "mean"),
    (35, "Médiane de buts marqués par équipe", "equipe", "for", "median"),
    (36, "Médiane de buts marqués par championnat", "champ", "for", "median"),
    (37, "Moyenne de buts encaissés par équipe", "equipe", "against", "mean"),
    (38, "Moyenne de buts encaissés par championnat", "champ", "against", "mean"),
    (39, "Médiane de buts encaissés par équipe", "equipe", "against", "median"),
    (40, "Médiane de buts encaissés par championnat", "champ", "against", "median"),
]

# Titres courts pour le menu (le titre complet s'affiche en haut de la page)
COURTS = {
    4: "BTTS · championnats", 5: "BTTS · équipes",
    6: "Over 1.5 · championnats", 7: "Over 1.5 · équipes",
    8: "Over 2.5 · championnats", 9: "Over 2.5 · équipes",
    10: "Over 3.5 · championnats", 11: "Over 3.5 · équipes",
    12: "Victoires (saison)", 13: "Défaites (saison)", 14: "Matchs nuls (saison)",
    15: "2e > 1re période · champ.", 16: "2e > 1re période · équipes",
    17: "1re > 2e période · champ.", 18: "1re > 2e période · équipes",
    19: "Périodes égales · champ.", 20: "Périodes égales · équipes",
    21: "Marquent au moins 1 but", 22: "Marquent au moins 2 buts",
    23: "Marquent au moins 3 buts", 24: "Marquent au moins 4 buts",
    25: "Marquent moins de 2 buts", 26: "Ne marquent pas",
    27: "Victoires (5 derniers)", 28: "Défaites (5 derniers)", 41: "Matchs nuls (5 derniers)",
    29: "Clean sheet (n'encaissent pas)",
    30: "Encaissent au moins 1 but", 31: "Encaissent au moins 2 buts", 32: "Encaissent au moins 3 buts",
    33: "Moyenne buts marqués · équipes", 34: "Moyenne buts marqués · champ.",
    35: "Médiane buts marqués · équipes", 36: "Médiane buts marqués · champ.",
    37: "Moyenne buts encaissés · équipes", 38: "Moyenne buts encaissés · champ.",
    39: "Médiane buts encaissés · équipes", 40: "Médiane buts encaissés · champ.",
}


# =========================================================
# CHARGEMENT (mis en cache)
# =========================================================
@st.cache_data(ttl=3 * 3600, show_spinner=False)
def _charger(saison, codes_main, codes_extra):
    return sc.charger_tout(list(codes_main), list(codes_extra), saison)


def charger(saison, codes_main, codes_extra):
    with st.spinner(T("⚽ Mise à jour des matchs et calcul des statistiques… quelques instants")):
        return _charger(saison, codes_main, codes_extra)


@st.cache_data(ttl=3600, show_spinner=False)          # programme rechargé toutes les heures
def _charger_fixtures():
    return sc.charger_prochains_matchs()


@st.cache_data(ttl=3600, show_spinner=False)
def _charger_openfootball(saison):
    return sc.charger_openfootball(saison)


def charger_fixtures():
    """Programme de la source principale, complété par le calendrier openfootball (matchs manquants)."""
    with st.spinner(T("📅 Récupération des prochains matchs…")):
        fx = _charger_fixtures()
        try:
            autres = sc.prochains_matchs_openfootball(_charger_openfootball(saison), M, aujourdhui())
            autres = autres[autres["div"].isin(M["div"].unique())] if not autres.empty else autres
            return sc.completer_programme(fx, autres)
        except Exception:
            return fx


# =========================================================
# OUTILS D'AFFICHAGE
# =========================================================
JOURS_SEMAINE = ["Lun.", "Mar.", "Mer.", "Jeu.", "Ven.", "Sam.", "Dim."]


def aujourdhui():
    """Date du jour à Brazzaville (le serveur Streamlit Cloud est en heure UTC)."""
    return pd.Timestamp.now(tz="Africa/Brazzaville").normalize().tz_localize(None)


def matchs_a_venir(fixtures):
    """Ne garde que les matchs d'aujourd'hui et des jours suivants."""
    if fixtures.empty:
        return fixtures
    return fixtures[fixtures["date"].notna() & (fixtures["date"] >= aujourdhui())]


def libelle_date(d, nb=None):
    j = aujourdhui()
    jour = T("Aujourd'hui" if d == j else "Demain" if d == j + pd.Timedelta(days=1) else JOURS_SEMAINE[d.weekday()])
    txt = f"{jour} {d.strftime('%d/%m/%Y')}"
    return txt + " " + T("({n} matchs)", n=nb) if nb is not None else txt


def libelle(code):
    return f"{sc.noms.get(code, code)} ({code})"


def col_pct(label):
    return st.column_config.ProgressColumn(label, min_value=0, max_value=100, format="%d%%")


def tableau(df, column_config=None, **kw):
    """st.dataframe avec les noms de colonnes traduits."""
    cols = {c: T(c) for c in df.columns}
    cfg = {cols.get(k, T(k)): v for k, v in (column_config or {}).items()}
    st.dataframe(df.rename(columns=cols), column_config=cfg or None, **kw)


def bouton_csv(df, nom, key):
    df = df.rename(columns={c: T(c) for c in df.columns})
    st.download_button(T("⬇️ Télécharger en CSV"), df.to_csv(index=False).encode("utf-8-sig"),
                       file_name=nom, mime="text/csv", key=key)


def graphique_barres(d, categorie, valeur, titre_valeur, n_max=25, domaine=(0, 105), fmt=".0f"):
    titre_valeur = T(titre_valeur)
    # noms internes sans point ni espace : Altair lit "a.b" comme un sous-champ (graphique vide)
    d = d.head(n_max)[[categorie, valeur]].rename(columns={categorie: "cat", valeur: "val"})
    base = alt.Chart(d).encode(
        x=alt.X("val:Q", title=titre_valeur, axis=alt.Axis(tickCount=8),
                scale=alt.Scale(domain=list(domaine)) if domaine else alt.Scale(zero=True)),
        y=alt.Y("cat:N", sort="-x", title=None, axis=alt.Axis(labelLimit=260)),
        tooltip=[alt.Tooltip("cat:N", title=T("Nom")), alt.Tooltip("val:Q", title=titre_valeur, format=fmt)],
    )
    chart = ((base.mark_bar(color=BLEU, cornerRadiusEnd=4, height=16)
              + base.mark_text(align="left", dx=4, color=TEXTE_GRAPH, fontSize=11)
                    .encode(text=alt.Text("val:Q", format=fmt)))
             .properties(height=max(160, 26 * len(d)))
             .configure_axis(grid=False, labelColor=TEXTE_GRAPH, titleColor=TEXTE_GRAPH, domainColor="#3a4a60", tickColor="#3a4a60")
             .configure_view(strokeWidth=0))
    st.altair_chart(chart, use_container_width=True)


def filtre_championnat(long, key):
    ligues = ["Tous les championnats"] + sorted(long["div"].unique(), key=lambda c: sc.noms.get(c, c))
    choix = st.selectbox(T("Championnat"), ligues, key=key,
                         format_func=lambda c: T(c) if c.startswith("Tous") else libelle(c))
    return long if choix.startswith("Tous") else long[long["div"] == choix]


def note_mi_temps(indicateur):
    if sc.besoin_mi_temps(indicateur):
        st.info(T("Cet état utilise le score à la mi-temps : les championnats extra "
                "(USA, ARG, BRA, SWE, JPN, NOR) n'ont pas cette donnée et sont exclus."))


def afficher(vue, stat, pct, nom_csv, key, label_graph):
    """Graphique + tableau + export d'une vue déjà renommée."""
    if vue.empty:
        st.warning(T("Aucune donnée ne remplit les conditions (essaie de baisser le minimum de matchs)."))
        return
    graphique_barres(vue, label_graph, pct, pct, n_max=25)
    cfg = {pct: col_pct(T(pct))}
    tableau(vue, hide_index=True, use_container_width=True, height=min(38 + 35 * len(vue), 760),
                 column_config=cfg)
    bouton_csv(vue, nom_csv, key)


# =========================================================
# PAGES
# =========================================================
def page_etat(etat):
    num, titre, typ, ind, stat, pct, aide = etat
    st.header(T(titre))
    if aide:
        st.caption(T(aide))

    if typ == "champ":
        note_mi_temps(ind)
        t = sc.tableau_championnats(M, ind)
        if t.empty:
            st.warning(T("Pas de données pour cet état."))
            return
        vue = t.rename(columns={"top": "Rang", "league": "Championnat", "total_matches": "Matchs joués",
                                "yes_matches": stat, "%_yes_matches": pct})[
            ["Rang", "Championnat", "Matchs joués", stat, pct]]
        moyenne = round(t["yes_matches"].sum() / t["total_matches"].sum() * 100)
        c1, c2, c3 = st.columns(3)
        c1.metric(T("1er : {x}", x=vue.iloc[0]['Championnat']), f"{vue.iloc[0][pct]} %")
        c2.metric(T("Dernier : {x}", x=vue.iloc[-1]['Championnat']), f"{vue.iloc[-1][pct]} %")
        c3.metric(T("Moyenne tous championnats"), f"{moyenne} %")
        afficher(vue, stat, pct, f"etat_{num}.csv", f"csv_{num}", "Championnat")
        return

    # Filtres de la page : championnat + nombre d'équipes (+ derniers matchs pour la forme)
    if typ == "forme":
        f1, f2, f3 = st.columns([3, 1, 1])
        with f3:
            n_last = st.number_input(T("Derniers matchs"), 3, 10, 5, key=f"n_{num}")
    else:
        f1, f2 = st.columns([3, 1])
    with f1:
        base = filtre_championnat(LONG, f"lig_{num}")
    nb = f2.selectbox(T("Nombre d'équipes"), NB_EQUIPES, index=NB_EQUIPES.index(20), key=f"nb_{num}",
                      format_func=lambda x: T("Toutes") if x == 0 else str(x))

    if typ == "equipe":
        note_mi_temps(ind)
        t = sc.tableau_equipes(base, ind, MIN_MATCHES, None)
        if t.empty:
            st.warning(T("Aucune équipe ne remplit les conditions (essaie de baisser le minimum de matchs)."))
            return
        vue = t.rename(columns={"top": "Rang", "team": "Équipe", "league": "Championnat",
                                "total_matches": "Matchs joués", "yes_matches": stat, "%_yes_matches": pct})[
            ["Rang", "Équipe", "Championnat", "Matchs joués", stat, pct]]

    elif typ == "resultats":
        t = sc.tableau_resultats(base, ind, MIN_MATCHES, None)
        if t.empty:
            st.warning(T("Aucune équipe ne remplit les conditions (essaie de baisser le minimum de matchs)."))
            return
        ordre = {"W": ["Victoires", "Nuls", "Défaites"], "L": ["Défaites", "Nuls", "Victoires"],
                 "D": ["Nuls", "Victoires", "Défaites"]}[ind]
        vue = t.rename(columns={"top": "Rang", "team": "Équipe", "league": "Championnat",
                                "total_matches": "Matchs joués", "win_matches": "Victoires",
                                "draw_matches": "Nuls", "loss_matches": "Défaites", "pct": pct})[
            ["Rang", "Équipe", "Championnat", "Matchs joués"] + ordre + [pct]]

    else:  # forme
        t = sc.tableau_forme(base, int(n_last), ind, None)
        st.caption(T("Forme : du match le plus ancien (à gauche) au plus récent (à droite). "
                   "W = victoire, D = nul, L = défaite. Vérifie la date du dernier match : "
                   "une série ancienne pèse moins qu'une série en cours."))
        if t.empty:
            st.warning(T("Pas assez de matchs."))
            return
        ordre = {"W": ["Victoires", "Nuls", "Défaites"], "L": ["Défaites", "Nuls", "Victoires"],
                 "D": ["Nuls", "Victoires", "Défaites"]}[ind]
        vue = t.rename(columns={"top": "Rang", "team": "Équipe", "league": "Championnat",
                                "last_matches": "Derniers matchs", "win_matches": "Victoires",
                                "draw_matches": "Nuls", "loss_matches": "Défaites", "form": "Forme",
                                "last_match_date": "Dernier match"})[
            ["Rang", "Équipe", "Championnat", "Derniers matchs"] + ordre + ["Forme", "Dernier match"]]
        total = len(vue)
        vue = vue.head(nb) if nb else vue
        st.caption(T("{n} équipes affichées sur {total} classées", n=len(vue), total=total))
        tableau(vue, hide_index=True, use_container_width=True, height=min(38 + 35 * len(vue), 760))
        bouton_csv(vue, f"etat_{num}.csv", f"csv_{num}")
        return

    total = len(vue)
    vue = vue.head(nb) if nb else vue
    st.caption(T("{n} équipes affichées sur {total} classées · minimum {m} matchs joués",
                 n=len(vue), total=total, m=MIN_MATCHES))
    graph = vue.assign(_label=vue["Équipe"] + " · " + vue["Championnat"])
    if vue.empty:
        st.warning(T("Aucune équipe."))
        return
    graphique_barres(graph, "_label", pct, pct, n_max=min(nb or 30, 30))
    tableau(vue, hide_index=True, use_container_width=True, height=min(38 + 35 * len(vue), 760),
                 column_config={pct: col_pct(T(pct))})
    bouton_csv(vue, f"etat_{num}.csv", f"csv_{num}")


def page_stats(etat):
    num, titre, niveau, sens, mesure = etat
    st.header(T(titre))
    mot = "marqués" if sens == "for" else "encaissés"
    nom_mesure = "Moyenne" if mesure == "mean" else "Médiane"
    st.caption(T(f"{nom_mesure} des buts {mot} par match")
               + (T(" et par équipe, sur tous les matchs du championnat.") if niveau == "champ" else ".")
               + (T(" La médiane est la valeur du milieu : la moitié des matchs sont au-dessus, la moitié en dessous.")
                  if mesure == "median" else ""))
    if niveau == "champ":
        t = sc.stats_buts_championnats(LONG, sens)
        if sens == "against":
            st.info(T("Au total, la moyenne de buts encaissés d'un championnat est égale à sa moyenne de buts marqués "
                    "(chaque but marqué est encaissé par l'adversaire). La différence se voit à domicile / à l'extérieur."))
        ordre = st.radio(T("Ordre"), ["Plus élevé d'abord", "Plus bas d'abord"], horizontal=True, key=f"o_{num}",
                         format_func=T)
        t = t.sort_values([mesure, "mean", "league"], ascending=[ordre != "Plus élevé d'abord",
                                                                 ordre != "Plus élevé d'abord", True])
        t.insert(0, "Rang", range(1, len(t) + 1))
        lab = f"{nom_mesure} buts {mot}"
        vue = t.rename(columns={"league": "Championnat", "total_matches": "Matchs joués",
                                "total_goals": f"Buts {mot} (total)", mesure: lab,
                                f"{mesure}_home": f"{nom_mesure} à domicile",
                                f"{mesure}_away": f"{nom_mesure} à l'extérieur"})[
            ["Rang", "Championnat", "Matchs joués", f"Buts {mot} (total)", lab,
             f"{nom_mesure} à domicile", f"{nom_mesure} à l'extérieur"]]
        graphique_barres(vue, "Championnat", lab, lab, n_max=30, domaine=None, fmt=".2f")
    else:
        f1, f2, f3 = st.columns([3, 1, 1])
        with f1:
            base = filtre_championnat(LONG, f"lig_{num}")
        nb = f2.selectbox(T("Nombre d'équipes"), NB_EQUIPES, index=NB_EQUIPES.index(20), key=f"nb_{num}",
                          format_func=lambda x: T("Toutes") if x == 0 else str(x))
        ordre = f3.selectbox(T("Ordre"), ["Plus élevé d'abord", "Plus bas d'abord"], key=f"o_{num}", format_func=T)
        t = sc.stats_buts_equipes(base, sens, MIN_MATCHES)
        if t.empty:
            st.warning(T("Aucune équipe ne remplit les conditions (essaie de baisser le minimum de matchs)."))
            return
        haut = ordre == "Plus élevé d'abord"
        t = t.sort_values([mesure, "mean", "total_matches", "team"], ascending=[not haut, not haut, False, True])
        t.insert(0, "Rang", range(1, len(t) + 1))
        lab = f"{nom_mesure} buts {mot}"
        vue = t.rename(columns={"team": "Équipe", "league": "Championnat", "total_matches": "Matchs joués",
                                "total_goals": f"Buts {mot} (total)", mesure: lab,
                                f"{mesure}_home": f"{nom_mesure} à domicile",
                                f"{mesure}_away": f"{nom_mesure} à l'extérieur"})[
            ["Rang", "Équipe", "Championnat", "Matchs joués", f"Buts {mot} (total)", lab,
             f"{nom_mesure} à domicile", f"{nom_mesure} à l'extérieur"]]
        total = len(vue)
        vue = vue.head(nb) if nb else vue
        st.caption(T("{n} équipes affichées sur {total} classées · minimum {m} matchs joués",
                     n=len(vue), total=total, m=MIN_MATCHES))
        graphique_barres(vue.assign(_label=vue["Équipe"] + " · " + vue["Championnat"]), "_label", lab, lab,
                         n_max=min(nb or 30, 30), domaine=None, fmt=".2f")
    tableau(vue, hide_index=True, use_container_width=True, height=min(38 + 35 * len(vue), 760),
                 column_config={c: st.column_config.NumberColumn(T(c), format="%.2f")
                                for c in vue.columns if c.startswith(("Moyenne", "Médiane"))})
    bouton_csv(vue, f"etat_{num}.csv", f"csv_{num}")


def page_classement():
    st.header(T("🏆 Classement des championnats"))
    st.caption(T("Classement calculé à partir des résultats chargés : 3 points la victoire, 1 le nul. "
               "Départage : points, différence de buts, buts marqués."))
    divs = sorted(LONG["div"].unique(), key=lambda c: sc.noms.get(c, c))
    defaut = divs.index("F1") if "F1" in divs else 0
    a, b = st.columns([3, 2])
    div = a.selectbox(T("Championnat"), divs, index=defaut, format_func=libelle, key="lig_classement")
    vue_lieu = b.radio(T("Matchs pris en compte"), ["Tous", "Domicile", "Extérieur"], horizontal=True, format_func=T,
                       key="lieu_classement")
    base = LONG if vue_lieu == "Tous" else LONG[LONG["venue"] == ("H" if vue_lieu == "Domicile" else "A")]
    t = sc.classement(base, div)
    if t.empty:
        st.warning(T("Pas de match joué pour ce championnat."))
        return
    saison = M.loc[M["div"] == div, "season"].iloc[0]
    st.caption(T("Saison {s} · {e} équipes · {m} matchs · ", s=saison, e=len(t),
                 m=int(t['J'].sum() / (1 if vue_lieu != 'Tous' else 2)))
               + T("Forme : 5 derniers matchs, du plus ancien au plus récent (W = victoire, D = nul, L = défaite)."))
    tableau(
        t, hide_index=True, use_container_width=True, height=min(38 + 35 * len(t), 900),
        column_config={
            "Rang": st.column_config.NumberColumn(T("Rang"), width="small"),
            "J": st.column_config.NumberColumn(T("J"), help=T("Matchs joués")),
            "G": st.column_config.NumberColumn(T("G"), help=T("Victoires")),
            "N": st.column_config.NumberColumn(T("N"), help=T("Matchs nuls")),
            "P": st.column_config.NumberColumn(T("P"), help=T("Défaites")),
            "BP": st.column_config.NumberColumn(T("BP"), help=T("Buts marqués")),
            "BC": st.column_config.NumberColumn(T("BC"), help=T("Buts encaissés")),
            "Diff": st.column_config.NumberColumn(T("Diff"), help=T("Différence de buts"), format="%+d"),
            "Pts": st.column_config.NumberColumn(T("Pts"), help=T("Points")),
        })
    st.caption(T("Ce classement peut différer du classement officiel : pénalités de points, départage par "
               "confrontations directes, ou formats particuliers (play-offs en Belgique et en Écosse, "
               "conférences en MLS, groupes en Argentine)."))
    bouton_csv(t, f"classement_{div}.csv", "csv_classement")


# =========================================================
# ABONNEMENT (pawaPay + Supabase)
# =========================================================
CFG_AB = ab.config()
MOTIFS_ECHEC = {
    "PAYER_NOT_FOUND": "ce numéro n'a pas de compte Mobile Money actif",
    "PAYMENT_NOT_APPROVED": "le paiement n'a pas été validé sur le téléphone (code PIN non saisi ou refusé)",
    "INSUFFICIENT_BALANCE": "le solde Mobile Money est insuffisant",
    "PAYER_LIMIT_REACHED": "le plafond de transactions du compte est atteint",
    "WALLET_LIMIT_REACHED": "le plafond du portefeuille est atteint",
    "NOT_FOUND": "la demande n'est pas parvenue à l'opérateur",
}


def date_fr(d):
    d = d.astimezone(ab.timezone(ab.timedelta(hours=1)))
    return T("{date} à {heure}", date=d.strftime("%d/%m/%Y"), heure=d.strftime("%H:%M"))


def acces_premium():
    if not CFG_AB["actif"]:
        return True                                   # abonnement non configuré : tout reste gratuit
    a = st.session_state.get("abonne")
    return bool(a and (a.get("admin") or a["fin"] > ab.maintenant()))


def formulaire_connexion(key):
    with st.form(f"connexion_{key}"):
        st.markdown(T("**Déjà abonné ? Connecte-toi**"))
        numero = st.text_input(T("Numéro Mobile Money"), placeholder=T("242 06 123 45 67"), key=f"num_{key}")
        code = st.text_input(T("Code d'accès (6 chiffres)"), type="password", key=f"code_{key}")
        ok = st.form_submit_button(T("Se connecter"), use_container_width=True)
    if ok:
        essais = st.session_state.get("essais_connexion", 0)
        if essais >= 5:
            st.error(T("Trop de tentatives. Recharge la page dans quelques minutes."))
            return
        st.session_state["essais_connexion"] = essais + 1
        if CFG_AB["code_admin"] and code.strip() == CFG_AB["code_admin"]:
            st.session_state["abonne"] = {"msisdn": "admin", "fin": ab.maintenant(), "admin": True}
            st.rerun()
        try:
            res = ab.connexion(CFG_AB, numero, code)
        except Exception:
            res = None
            st.error(T("Service d'abonnement momentanément indisponible. Réessaie dans un instant."))
            return
        if res:
            st.session_state["abonne"] = {"msisdn": res[0], "fin": res[1], "code": code.strip()}
            st.session_state["essais_connexion"] = 0
            st.rerun()
        else:
            st.error(T("Numéro ou code incorrect, ou abonnement expiré."))


def verrou(titre):
    """À appeler en tête d'une page payante : affiche le paywall et renvoie False si pas d'accès."""
    if acces_premium():
        return True
    st.header(titre)
    st.info(T("🔒 **Contenu réservé aux abonnés** : pronostics des prochains matchs et tickets, "
              "pour **environ 1 € les {j} jours**, payables par Mobile Money "
              "dans de nombreux pays d'Afrique (MTN, Airtel, Orange, Moov, M-Pesa, Wave…).", j=CFG_AB['duree']))
    a, b = st.columns(2)
    with a:
        st.markdown(T("**Pas encore abonné ?**"))
        st.write(T("L'abonnement se fait en une minute depuis ton téléphone."))
        st.page_link(PAGE_ABONNEMENT, label=T("S'abonner maintenant"), use_container_width=True)
    with b:
        formulaire_connexion(titre)
    return False


def page_abonnement():
    st.header(T("💳 Abonnement"))
    if not CFG_AB["actif"]:
        st.info(T("Les abonnements ne sont pas encore activés : toutes les pages sont gratuites pour le moment."))
        return
    if CFG_AB["sandbox"]:
        st.warning(T("Mode test (sandbox) : aucun argent réel n'est prélevé."))
    a = st.session_state.get("abonne")
    if a and a.get("admin"):
        st.success(T("Accès administrateur actif."))
        return
    if a and a["fin"] > ab.maintenant():
        st.success(T("✅ Ton abonnement est actif jusqu'au **{d}**.", d=date_fr(a['fin'])))
        if a.get("code"):
            st.markdown(T("Ton code d'accès : **{c}**. Garde-le : il te sert à te reconnecter.", c=a['code']))
        st.markdown(T("Tu peux prolonger dès maintenant : {j} jours de plus seront ajoutés "
                      "à la fin de ton abonnement actuel.", j=CFG_AB['duree']))

    st.subheader(T("S'abonner : environ 1 € pour {j} jours", j=CFG_AB['duree']))
    st.markdown(T("1. Choisis ton pays et saisis ton numéro Mobile Money.\n"
                "2. Une demande de paiement arrive sur ton téléphone : valide-la avec ton **code PIN**.\n"
                "3. Ton **code d'accès** s'affiche ici : garde-le pour te reconnecter."))

    paiement = st.session_state.get("paiement")
    if not paiement:
        try:
            pays = ab.pays_disponibles(CFG_AB)
        except Exception as e:
            st.error(T("Service de paiement momentanément indisponible. Réessaie dans un instant."))
            if CFG_AB["sandbox"]:
                st.caption(T("Détail technique (visible en mode test seulement) : {e}", e=e))
            return
        if not pays:
            st.error(T("Aucun pays n'est ouvert aux paiements sur ce compte pawaPay pour le moment."))
            return
        codes = list(pays)
        c1, c2 = st.columns(2)
        code_pays = c1.selectbox(T("Pays"), codes, format_func=lambda c: f"{pays[c]['nom']} (+{pays[c]['prefixe']})",
                                 index=codes.index(ab.PAYS_DEFAUT) if ab.PAYS_DEFAUT in codes else 0)
        p = pays[code_pays]
        ops = {o["provider"]: o for o in p["operateurs"]}
        choix = c2.selectbox(T("Opérateur"), ["auto"] + list(ops),
                             format_func=lambda x: "Détection automatique" if x == "auto" else ops[x]["nom"])
        devises = {o["devise"] for o in p["operateurs"]}
        if choix != "auto":
            prix_txt = ab.format_montant(ab.montant(CFG_AB, ops[choix]), ops[choix]["devise"])
        elif len(devises) == 1:
            prix_txt = ab.format_montant(ab.montant(CFG_AB, p["operateurs"][0]), p["operateurs"][0]["devise"])
        else:
            prix_txt = T("environ 1 €")
        st.markdown(T("Prix : **{prix}** pour {j} jours · opérateurs : {ops}", prix=prix_txt, j=CFG_AB['duree'],
                      ops=", ".join(o['nom'] for o in p['operateurs'])))
        with st.form("payer"):
            numero = st.text_input(T("Numéro Mobile Money"), placeholder=f"+{p['prefixe']} …")
            go = st.form_submit_button(f"Payer {prix_txt}", type="primary", use_container_width=True)
        if go:
            try:
                msisdn, devine = ab.normaliser_numero(CFG_AB, code_pays, p["prefixe"], numero)
                provider = devine if choix == "auto" else choix
                if provider not in ops:
                    raise ValueError("Cet opérateur n'est pas encore accepté dans ce pays. "
                                     "Choisis un autre opérateur dans la liste.")
                op = ops[provider]
                somme = ab.montant(CFG_AB, op)
                deposit_id = ab.nouveau_deposit_id()
                ab.enregistrer_demande(CFG_AB, deposit_id, msisdn, provider, somme, op["devise"], code_pays)
                statut, raison = ab.demander_paiement(CFG_AB, msisdn, provider, deposit_id, somme, op["devise"])
            except ValueError as e:
                st.error(T(str(e)))
                return
            except Exception as e:
                st.error(T("Service de paiement momentanément indisponible. Réessaie dans un instant."))
                if CFG_AB["sandbox"]:
                    st.caption(T("Détail technique (visible en mode test seulement) : {e}", e=e))
                return
            if statut == "REJECTED":
                st.error(T("Paiement refusé : {r}", r=raison))
                return
            st.session_state["paiement"] = {"id": deposit_id, "msisdn": msisdn, "op": op["nom"],
                                            "prix": ab.format_montant(somme, op["devise"])}
            st.rerun()
        formulaire_connexion("abonnement")
        return

    # Paiement en cours : on interroge pawaPay jusqu'au résultat (environ 2 minutes maximum)
    st.info(T("📱 Une demande de paiement {op} de **{prix}** a été envoyée au **+{num}**. "
              "Valide-la sur ton téléphone avec ton code PIN.", op=paiement['op'], prix=paiement['prix'],
              num=paiement['msisdn']))
    etat, info = "EN_ATTENTE", None
    with st.spinner(T("En attente de ta validation…")):
        for _ in range(24):
            try:
                etat, info = ab.finaliser(CFG_AB, paiement["id"], paiement["msisdn"])
            except Exception:
                etat = "EN_ATTENTE"
            if etat != "EN_ATTENTE":
                break
            time.sleep(5)
    if etat == "PAYE":
        fin, code = info
        st.session_state["abonne"] = {"msisdn": paiement["msisdn"], "fin": fin, "code": code}
        st.session_state.pop("paiement", None)
        st.balloons()
        st.success(T("✅ Paiement reçu ! Abonnement actif jusqu'au **{d}**.", d=date_fr(fin)))
        st.markdown(T("### Ton code d'accès : `{c}`", c=code))
        st.caption(T("Note-le bien : avec ton numéro, il te permet de te reconnecter sur n'importe quel appareil."))
        st.page_link(PAGE_TICKETS_DEFAUT, label=T("🎟️ Voir les tickets"), use_container_width=True)
    elif etat == "ECHEC":
        st.session_state.pop("paiement", None)
        st.error(T("❌ Paiement non abouti : {m}. Aucun montant n'a été débité. Tu peux réessayer.",
                   m=T(MOTIFS_ECHEC.get(info, "le paiement a échoué"))))
        if st.button(T("Réessayer")):
            st.rerun()
    else:
        st.warning(T("Toujours en attente de validation. Si tu as déjà validé, clique sur « Vérifier » ; "
                   "sinon, valide la demande sur ton téléphone."))
        c1, c2 = st.columns(2)
        if c1.button(T("🔄 Vérifier"), use_container_width=True):
            st.rerun()
        if c2.button(T("Annuler"), use_container_width=True):
            st.session_state.pop("paiement", None)
            st.rerun()


def page_tickets(nom):
    entete = T("🎟️ Ticket : {t}", t=T(TITRES_TICKETS.get(nom, nom)))
    if not verrou(entete):
        return
    st.header(entete)
    modeles = sc.modeles_par_championnat(M)
    parts = sc.parts_1re_periode(M)
    fixtures = charger_fixtures()
    if fixtures.empty:
        st.info(T("Aucun prochain match disponible pour le moment."))
        return
    aujourd_hui = aujourdhui()
    fixtures = matchs_a_venir(fixtures)
    if fixtures.empty:
        st.info(T("Aucun match à venir (aujourd'hui ou les jours suivants) pour le moment."))
        return
    divs_dispo = sorted(set(fixtures["div"]) & set(M["div"]), key=lambda x: sc.noms.get(x, x))
    ss = st.session_state                     # réglages mémorisés d'un ticket à l'autre
    ss.setdefault("t_n", 10)
    ss.setdefault("t_periode", "toutes")
    ss.setdefault("t_divs", divs_dispo)
    a, b, c = st.columns([1, 1, 2])
    n = a.number_input(T("Nombre de matchs"), min_value=1, max_value=30, value=ss["t_n"], step=1,
                       help=T("10 par défaut ; tu peux en ajouter jusqu'à 30 (dans la limite des matchs à venir disponibles)."), key=f"w_n_{nom}")
    dates_dispo = sorted(fixtures["date"].dropna().unique())
    periodes = ["j1", "j3", "j7", "j14", "toutes"] + [pd.Timestamp(d).strftime("%Y-%m-%d") for d in dates_dispo]
    noms_periodes = {"j1": "Aujourd'hui et demain", "j3": "3 prochains jours", "j7": "7 prochains jours",
                     "j14": "14 prochains jours", "toutes": "Tous les matchs à venir"}
    if ss["t_periode"] not in periodes:
        ss["t_periode"] = "toutes"
    periode = b.selectbox(T("Période ou date"), periodes, index=periodes.index(ss["t_periode"]), key=f"w_j_{nom}",
                          format_func=lambda x: T(noms_periodes[x]) if x in noms_periodes else libelle_date(pd.Timestamp(x)))
    divs = c.multiselect(T("Championnats"), divs_dispo, default=[d for d in ss["t_divs"] if d in divs_dispo],
                         format_func=libelle, key=f"w_d_{nom}")
    ss["t_n"], ss["t_periode"], ss["t_divs"] = n, periode, divs

    # Probabilité minimale : un match n'entre dans le ticket que si sa probabilité dépasse ce seuil
    seuils = {k: ss.get(f"seuil_{k}", v) for k, v in sc.SEUILS_DEFAUT.items()}
    if nom != "Combiné":
        seuil = st.slider(T("Probabilité minimale de réussite (%)"), 5, 95, int(seuils[nom]), step=5, key=f"w_s_{nom}",
                          help=T("Seuls les matchs dont la probabilité atteint ce niveau entrent dans le ticket. "
                               "Le seuil par défaut est adapté à l'événement (un nul ou un score exact n'atteint "
                               "jamais le niveau d'une victoire nette)."))
        ss[f"seuil_{nom}"] = seuil

    fx = fixtures[fixtures["div"].isin(divs)]
    if periode.startswith("j"):                                   # fenêtre glissante à partir d'aujourd'hui
        fx = fx[fx["date"] <= aujourd_hui + pd.Timedelta(days=int(periode[1:]))]
    elif periode != "toutes":                                     # une date précise
        fx = fx[fx["date"] == pd.Timestamp(periode)]
    pred = sc.predictions_detaillees(fx, modeles, parts, MIN_MATCHES)
    if pred.empty:
        st.info(T("Aucun match à venir pour ces critères (période, championnats, minimum de matchs joués)."))
        return
    st.caption(T("{n} matchs à venir analysés · équipes ayant joué au moins {m} matchs.", n=len(pred), m=MIN_MATCHES))

    if nom == "Combiné":
        t = sc.ticket_combine(pred, int(n), seuils)
        st.caption(T("Le meilleur pronostic de chaque type de ticket (un match n'est utilisé qu'une fois), "
                   "complété par les pronostics les plus probables restants. Chaque pronostic doit atteindre "
                   "la probabilité minimale réglée dans son propre ticket."))
    else:
        t = sc.construire_ticket(pred, nom, int(n), seuil)
        st.caption(T("Les matchs où cet événement est le plus probable selon le modèle, à partir de {s} %.", s=seuil))
    if len(t) < int(n):
        st.info(T("Seulement **{n} match(s)** sur les {total} à venir atteignent la probabilité minimale : "
                  "le ticket est volontairement plus court que demandé. Pour en avoir plus, baisse le seuil "
                  "(au risque d'un ticket moins sûr), élargis la période ou ajoute des championnats.",
                  n=len(t), total=len(pred)))
    if nom != "Combiné":
        if nom == "Défaites":
            st.caption(T("« Défaite X » : l'équipe X perd le match (son adversaire gagne)."))
        if nom.startswith("12 Yes"):
            st.caption(T("« 12 Yes » : l'équipe la plus forte du match gagne ET les deux équipes marquent "
                       "(ex. 2-1, 3-1, 1-2). Plus exigeant qu'une simple victoire, donc probabilités plus basses."))
        if nom == "Matchs nuls":
            st.caption(T("Les matchs les plus équilibrés selon le modèle. Un nul dépasse rarement 30 à 35 % de probabilité."))
        if nom == "Scores exacts":
            st.caption(T("Un score exact reste un pari très incertain : même le plus probable dépasse "
                       "rarement 15 à 20 %."))
    afficher_ticket(t, nom, combine=(nom == "Combiné"))
    st.warning(T("Les probabilités d'un ticket se multiplient : plus il y a de matchs, plus la probabilité que "
               "tout passe est faible. Ce sont des estimations statistiques, pas des certitudes."))


def afficher_ticket(t, nom, combine=False):
    if t.empty:
        st.info(T("Pas de match disponible pour ce ticket."))
        return
    vue = pd.DataFrame({"N°": range(1, len(t) + 1),
                        "Date": t["date"].dt.strftime("%d/%m/%Y"), "Heure": t["time"],
                        "Championnat": t["league"], "Match": t["match"]})
    if combine:
        vue["Type"] = [T(TITRES_TICKETS.get(x, x)) for x in t["ticket_type"]]
    vue["Pronostic"] = [T(m, e=e) for m, e in zip(t["pick_modele"], t["pick_e"])]
    vue["Probabilité"] = (t["proba"] * 100).round(0).astype(int).values
    vue["Cote juste"] = (1 / t["proba"]).round(2).values
    cotes = pd.to_numeric(t["market_odds"], errors="coerce")
    if cotes.notna().any():
        vue["Cote marché"] = cotes.values
    p_tout = float(np.prod(t["proba"]))
    k1, k2, k3 = st.columns(3)
    k1.metric(T("Matchs"), len(t))
    k2.metric(T("Probabilité que tout passe"), f"{p_tout * 100:.1f} %" if p_tout >= 0.001 else "< 0,1 %")
    k3.metric(T("Cote juste du ticket"), f"{1 / p_tout:,.2f}".replace(",", " ") if p_tout > 0 else "-")
    tableau(vue, hide_index=True, use_container_width=True, height=min(38 + 35 * len(vue), 760),
            column_config={"Probabilité": col_pct(T("Probabilité"))})
    bouton_csv(vue, f"ticket_{nom.lower().replace(' ', '_')}.csv", f"csv_t_{nom}")


def page_donnees():
    st.header(T("🏠 Accueil"))
    st.caption(T("Championnats chargés et ensemble des matchs joués."))
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(T("Championnats"), M["div"].nunique())
    c2.metric(T("Matchs joués"), f"{len(M):,}".replace(",", " "))
    c3.metric(T("Équipes"), LONG[["team", "div"]].drop_duplicates().shape[0])
    c4.metric(T("Dernier match"), M["date"].max().strftime("%d/%m/%Y") if M["date"].notna().any() else "-")

    st.subheader(T("Journal de chargement"))
    j = pd.DataFrame(JOURNAL, columns=["Code", "Statut", "Matchs"])
    j["Statut"] = j["Statut"].map(lambda x: T("✅ Chargé") if x == "OK" else T("❌ Indisponible"))
    j["Championnat"] = j["Code"].map(sc.noms)
    tableau(j[["Championnat", "Code", "Statut", "Matchs"]], hide_index=True, use_container_width=True)

    try:
        _, corr = sc.correspondance_equipes(_charger_openfootball(saison), M, details=True)
    except Exception:
        corr = pd.DataFrame()
    if not corr.empty:
        manquants = int((corr["methode"] == "Non trouvé").sum())
        titre = T("🔗 Noms d'équipes : calendrier → résultats") + (T(" ({n} non trouvé(s))", n=manquants) if manquants else " ✅")
        with st.expander(titre):
            st.caption(T("Le second calendrier écrit parfois les noms autrement. Ordre de recherche : le fichier "
                         "correspondances.json (modifiable), puis les matchs déjà joués (même date et même score), "
                         "puis l'orthographe la plus proche."))
            vue_c = pd.DataFrame({"Championnat": corr["league"], "Nom dans le calendrier": corr["calendrier"],
                                  "Nom dans les résultats": corr["resultats"],
                                  "Méthode": [T(x) for x in corr["methode"]]})
            tableau(vue_c, hide_index=True, use_container_width=True, height=min(38 + 35 * len(vue_c), 500))

    st.subheader(T("Tous les matchs"))
    a, b = st.columns(2)
    with a:
        d = filtre_championnat(M.rename(columns={}), "lig_data")
    recherche = b.text_input(T("Rechercher une équipe"))
    if recherche:
        d = d[d["home_team"].str.contains(recherche, case=False) | d["away_team"].str.contains(recherche, case=False)]
    d = d.sort_values("date", ascending=False)
    vue = pd.DataFrame({
        "Date": d["date"].dt.strftime("%d/%m/%Y"), "Championnat": d["league"], "Saison": d["season"],
        "Domicile": d["home_team"], "Extérieur": d["away_team"],
        "Buts dom.": d["fthg"].astype("Int64"), "Buts ext.": d["ftag"].astype("Int64"),
        "Mi-temps dom.": d["hthg"].astype("Int64"), "Mi-temps ext.": d["htag"].astype("Int64"),
        "Cote 1": d["odds_h"], "Cote N": d["odds_d"], "Cote 2": d["odds_a"]})
    st.caption(T("{n} matchs", n=len(vue)))
    tableau(vue, hide_index=True, use_container_width=True, height=500)
    bouton_csv(vue, "matchs.csv", "csv_data")


def afficher_matchs_ecartes(fixtures, modeles):
    """Matchs du programme sans prédiction, avec la raison (repliés par défaut)."""
    if fixtures.empty:
        return
    ecartes = sc.matchs_sans_prediction(fixtures, modeles)
    if ecartes.empty:
        return
    with st.expander(T("ℹ️ {n} match(s) du programme sans prédiction", n=len(ecartes))):
        st.caption(T("Le modèle a besoin des résultats de la saison de chaque équipe. Les matchs d'un championnat "
                     "non chargé (voir ⚙️ Paramètres) ou d'une équipe sans match joué ne peuvent pas être prédits."))
        vue = pd.DataFrame({"Date": ecartes["date"].dt.strftime("%d/%m/%Y"), "Heure": ecartes["time"],
                            "Championnat": ecartes["league"], "Match": ecartes["match"],
                            "Raison": [T(x) for x in ecartes["raison"]]})
        tableau(vue, hide_index=True, use_container_width=True)


def page_predictions():
    if not verrou(T("🔮 Prédictions")):
        return
    st.header(T("🔮 Prédictions"))
    modeles = sc.modeles_par_championnat(M)
    st.markdown(T("Modèle de **Poisson** : pour chaque équipe, forces d'attaque et de défense à domicile et à "
                "l'extérieur par rapport à la moyenne de son championnat (lissées en début de saison), d'où les "
                "buts attendus puis les probabilités de chaque score."))
    st.warning(T("Ce sont des estimations statistiques, pas des certitudes : blessures, rotations, météo ou enjeu "
               "ne sont pas pris en compte. À utiliser avec prudence."))
    sous = st.tabs([T("📅 Prochains matchs"), T("🎯 Match au choix")])

    with sous[0]:
        fixtures = matchs_a_venir(charger_fixtures())          # uniquement aujourd'hui et les jours suivants
        pred = (sc.predire_prochains_matchs(fixtures[fixtures["div"].isin(M["div"].unique())], modeles)
                if not fixtures.empty else pd.DataFrame())
        if pred.empty:
            st.info(T("Aucun match à venir (aujourd'hui ou les jours suivants) pour les championnats chargés. "
                    "Utilise « Match au choix »."))
            afficher_matchs_ecartes(fixtures, modeles)
        else:
            a, b, c = st.columns([2, 2, 1.5])
            nb_par_date = pred.groupby("date").size()
            dates = ["toutes"] + list(nb_par_date.index)
            choix_date = a.selectbox(
                T("Date"), dates, key="date_pred",
                format_func=lambda d: T("Toutes les dates à venir ({n} matchs)", n=len(pred)) if isinstance(d, str)
                else libelle_date(d, int(nb_par_date[d])))
            p = pred if isinstance(choix_date, str) else pred[pred["date"] == choix_date]
            lig = b.selectbox(T("Championnat"), ["Tous les championnats"] + sorted(p["div"].unique()),
                              format_func=lambda x: T(x) if x.startswith("Tous") else libelle(x), key="lig_pred")
            tris = {"Date et heure": "date", "Victoire domicile": "%_home", "Victoire extérieur": "%_away",
                    "BTTS": "%_btts", "Over 2.5": "%_over_2_5", "Over 1.5": "%_over_1_5"}
            tri = tris[c.selectbox(T("Trier par"), list(tris), key="tri_pred", format_func=T)]
            p = p if lig.startswith("Tous") else p[p["div"] == lig]
            p = (p.sort_values(["date", "time"]) if tri == "date" else p.sort_values(tri, ascending=False))
            if len(p) == 0:
                st.caption(T("Aucun match pour ce filtre."))
            elif p["date"].min() == p["date"].max():
                st.caption(T("{n} matchs", n=len(p)) + f" · {libelle_date(p['date'].min())}")
            else:
                st.caption(T("{n} matchs · du {d1} au {d2}", n=len(p), d1=libelle_date(p['date'].min()),
                             d2=libelle_date(p['date'].max())))
            vue = pd.DataFrame({
                "Date": p["date"].dt.strftime("%d/%m/%Y"), "Heure": p["time"], "Championnat": p["league"],
                "Domicile": p["home_team"], "Extérieur": p["away_team"], "Score probable": p["likely_score"],
                "% victoire dom.": p["%_home"], "% nul": p["%_draw"], "% victoire ext.": p["%_away"],
                "% BTTS": p["%_btts"], "% over 1.5": p["%_over_1_5"], "% over 2.5": p["%_over_2_5"],
                "% over 3.5": p["%_over_3_5"],
                "Buts attendus": p["xg_home"].round(1).astype(str) + " - " + p["xg_away"].round(1).astype(str),
                "Cote 1": p["odds_h"], "Cote N": p["odds_d"], "Cote 2": p["odds_a"]})
            cfg = {c: col_pct(T(c)) for c in vue.columns if c.startswith("%")}
            tableau(vue, hide_index=True, use_container_width=True, height=500, column_config=cfg)
            st.caption(T("Cotes 1 / N / 2 : cotes moyennes du marché. "
                       "Cote « juste » selon le modèle = 100 / pourcentage."))
            bouton_csv(vue, "predictions.csv", "csv_pred")
        afficher_matchs_ecartes(fixtures, modeles)

    with sous[1]:
        a, b, c = st.columns(3)
        divs = sorted(modeles, key=lambda x: sc.noms.get(x, x))
        lig = a.selectbox(T("Championnat"), divs, format_func=libelle, key="lig_match")
        equipes = list(modeles[lig]["forces"].index)
        dom = b.selectbox(T("Domicile"), equipes, index=0, key="dom")
        ext = c.selectbox(T("Extérieur"), equipes, index=min(1, len(equipes) - 1), key="ext")
        if dom == ext:
            st.warning(T("Choisis deux équipes différentes."))
            return
        p = sc.predire(modeles[lig], dom, ext)
        st.subheader(f"{dom}  vs  {ext}")
        k1, k2, k3 = st.columns(3)
        for col, lab, pr in [(k1, T("Victoire {e}", e=dom), p["p_home"]), (k2, T("Match nul"), p["p_draw"]),
                             (k3, T("Victoire {e}", e=ext), p["p_away"])]:
            col.metric(lab, f"{pr * 100:.0f} %")
            col.caption(T("Cote « juste » : {c}", c=f"{1 / pr:.2f}"))
        nul = T("Nul")
        d1x2 = pd.DataFrame({"issue": [dom, nul, ext],
                             "proba": [p["p_home"] * 100, p["p_draw"] * 100, p["p_away"] * 100]})
        chart = (alt.Chart(d1x2).mark_bar(cornerRadiusEnd=4)
                 .encode(x=alt.X("proba:Q", title=T("Probabilité (%)"), scale=alt.Scale(domain=[0, 100])),
                         y=alt.Y("issue:N", sort=None, title=None, scale=alt.Scale(paddingInner=0.35),
                                 axis=alt.Axis(labelLimit=220)),
                         color=alt.Color("issue:N", scale=alt.Scale(domain=[dom, nul, ext], range=COULEURS_1X2),
                                         legend=None),
                         tooltip=[alt.Tooltip("issue:N", title=T("Issue")), alt.Tooltip("proba:Q", title=T("%"), format=".0f")])
                 .properties(height=140)
                 .configure_axis(grid=False, labelColor=TEXTE_GRAPH, titleColor=TEXTE_GRAPH, domainColor="#3a4a60", tickColor="#3a4a60")
                 .configure_view(strokeWidth=0))
        st.altair_chart(chart, use_container_width=True)
        k4, k5, k6, k7, k8 = st.columns(5)
        k4.metric(T("Buts attendus"), f"{p['xg_home']:.2f} - {p['xg_away']:.2f}")
        k5.metric(T("BTTS"), f"{p['p_btts'] * 100:.0f} %")
        k6.metric(T("Over 1.5"), f"{p['p_over15'] * 100:.0f} %")
        k7.metric(T("Over 2.5"), f"{p['p_over25'] * 100:.0f} %")
        k8.metric(T("Over 3.5"), f"{p['p_over35'] * 100:.0f} %")
        s1, s2 = st.columns([1, 2])
        with s1:
            st.markdown(T("**Scores les plus probables**"))
            tableau(pd.DataFrame([{"Score": s, "Probabilité": f"{pr * 100:.1f} %"} for pr, s in p["top_scores"]]),
                         hide_index=True)
        with s2:
            st.markdown(T("**{e} marque** : {p} %", e=dom, p=f"{p['p_home_scores'] * 100:.0f}") + "  ·  "
                        + T("**{e} marque** : {p} %", e=ext, p=f"{p['p_away_scores'] * 100:.0f}"))
            f = modeles[lig]["forces"]
            dm, ex = T("(dom.)"), T("(ext.)")
            tableau(pd.DataFrame({
                "Équipe": [dom, ext],
                "Force d'attaque": [f"{f.at[dom, 'home_att']:.2f} {dm}", f"{f.at[ext, 'away_att']:.2f} {ex}"],
                "Force de défense": [f"{f.at[dom, 'home_def']:.2f} {dm}", f"{f.at[ext, 'away_def']:.2f} {ex}"],
                "Matchs joués": [int(f.at[dom, "matches"]), int(f.at[ext, "matches"])]}), hide_index=True)
            st.caption(T("Attaque > 1 : marque plus que la moyenne du championnat. "
                       "Défense > 1 : encaisse plus que la moyenne."))


# =========================================================
# EN-TÊTE COMMUN : TITRE + PARAMÈTRES
# =========================================================
st.markdown("""
<style>
.block-container {padding-top: 4.2rem;}
div[data-testid="stMetricValue"] {font-size: 1.9rem;}
</style>""", unsafe_allow_html=True)

h1, h3, h4, h2 = st.columns([4, 1.4, 1.1, 1], vertical_alignment="center")
i18n.selecteur(h4)
h1.markdown(T("### ⚽ Stats & Prédictions Foot"))
if CFG_AB["actif"]:
    _a = st.session_state.get("abonne")
    if _a and (_a.get("admin") or _a["fin"] > ab.maintenant()):
        h3.caption(T("👤 Administrateur") if _a.get("admin")
                   else T("✅ Abonné jusqu'au {d}", d=_a['fin'].strftime('%d/%m/%Y')))
    else:
        h3.caption(T("🔒 Non abonné"))
with h2.popover(T("⚙️ Paramètres"), use_container_width=True):
    saison = st.text_input(T("Saison européenne"), value=sc.SAISON, help=T("2627 = 2026-27, 2526 = 2025-26"))
    codes_main = st.multiselect(T("Championnats européens"), sc.MAIN_CODES, default=sc.MAIN_CODES, format_func=libelle)
    codes_extra = st.multiselect(T("Championnats extra"), sc.extra_leagues, default=sc.extra_leagues,
                                 format_func=libelle)
    MIN_MATCHES = st.slider(T("Minimum de matchs joués"), 1, 15, 5)
    if st.button(T("🔄 Actualiser les données"), use_container_width=True):
        st.cache_data.clear()

MATCHES, JOURNAL = charger(saison, tuple(codes_main), tuple(codes_extra))
if MATCHES.empty:
    st.error(T("Aucune donnée n'a pu être chargée. Vérifie ta connexion internet, la saison et les championnats choisis."))
    st.stop()
M = sc.matchs_joues(MATCHES)
LONG = sc.vue_equipes(M)


# =========================================================
# MENU : LES 28 ÉTATS DU NOTEBOOK
# =========================================================
def creer_page(etat):
    def page():
        page_etat(etat)
    page.__name__ = f"etat_{etat[0]}"
    return st.Page(page, title=T(COURTS[etat[0]]), url_path=f"etat-{etat[0]}")


def creer_page_stats(etat):
    def page():
        page_stats(etat)
    page.__name__ = f"stats_{etat[0]}"
    return st.Page(page, title=T(COURTS[etat[0]]), url_path=f"etat-{etat[0]}")


def creer_page_ticket(nom):
    def page():
        page_tickets(nom)
    slug = "btts" if nom.startswith("BTTS") else "12-yes" if nom.startswith("12 Yes") else (
        nom.lower().replace(" ", "-").replace(".", "").replace("é", "e").replace("è", "e"))
    page.__name__ = f"ticket_{slug.replace('-', '_')}"
    titre = ("⭐ " if nom == "Combiné" else "") + T(TITRES_TICKETS.get(nom, nom))
    return st.Page(page, title=titre, url_path=f"ticket-{slug}")


def section(nums):
    return [creer_page(e) for e in ETATS if e[0] in nums]


PAGE_ABONNEMENT = st.Page(page_abonnement, title=T("Abonnement"), icon="💳", url_path="abonnement")
PAGES_TICKETS = [creer_page_ticket(x) for x in ["Combiné"] + list(sc.TICKETS)]
PAGE_TICKETS_DEFAUT = PAGES_TICKETS[0]
menu = {
    "": [st.Page(page_donnees, title=T("Accueil"), icon="🏠", url_path="donnees", default=True)],
    T("🎯 Buts du match"): section(range(4, 12)),
    T("⏱️ Mi-temps"): section(range(15, 21)),
    T("⚽ Marqués"): section(range(21, 27)),
    # Forme : saison complète, 5 derniers matchs, puis les états « encaissés » (clean sheet, buts encaissés)
    T("📈 Forme"): section([12, 13, 14, 27, 28, 41]) + [creer_page(e) for e in BONUS],
    T("📊 Stats"): [st.Page(page_classement, title=T("Classement des championnats"), icon="🏆",
                         url_path="classement")] + [creer_page_stats(e) for e in ETATS_STATS],
    # Les 3 derniers onglets : Prédictions, Tickets, Abonnement (Streamlit place toujours les pages
    # isolées en premier : ces onglets sont donc des sections d'une seule page)
    T("🔮 Prédictions"): [st.Page(page_predictions, title=T("Prédictions"), icon="🔮", url_path="predictions")],
    T("🎟️ Tickets"): PAGES_TICKETS,
    T("💳 Abonnement"): [PAGE_ABONNEMENT],
}

st.navigation(menu, position="top").run()
st.divider()
st.caption(T("Pourcentages arrondis à l'entier · Rang : 1, 2, 3… (à égalité, départage par nombre de matchs puis ordre alphabétique) · "
           "Données mises à jour automatiquement toutes les 3 heures."))
