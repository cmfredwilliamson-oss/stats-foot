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

import stats_core as sc

st.set_page_config(page_title="Stats & Prédictions Foot", page_icon="⚽", layout="wide",
                   initial_sidebar_state="collapsed")

BLEU = "#2a78d6"                                   # série unique
COULEURS_1X2 = ["#2a78d6", "#eb6834", "#1baf7a"]   # domicile / nul / extérieur

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
    12: "Plus de victoires", 13: "Plus de défaites", 14: "Plus de matchs nuls",
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
@st.cache_data(ttl=3 * 3600, show_spinner="⚽ Mise à jour des matchs et calcul des statistiques… quelques instants")
def charger(saison, codes_main, codes_extra):
    return sc.charger_tout(list(codes_main), list(codes_extra), saison)


@st.cache_data(ttl=3 * 3600, show_spinner="📅 Récupération des prochains matchs…")
def charger_fixtures():
    return sc.charger_prochains_matchs()


# =========================================================
# OUTILS D'AFFICHAGE
# =========================================================
def libelle(code):
    return f"{sc.noms.get(code, code)} ({code})"


def col_pct(label):
    return st.column_config.ProgressColumn(label, min_value=0, max_value=100, format="%d%%")


def bouton_csv(df, nom, key):
    st.download_button("⬇️ Télécharger en CSV", df.to_csv(index=False).encode("utf-8-sig"),
                       file_name=nom, mime="text/csv", key=key)


def graphique_barres(d, categorie, valeur, titre_valeur, n_max=25, domaine=(0, 105), fmt=".0f"):
    # noms internes sans point ni espace : Altair lit "a.b" comme un sous-champ (graphique vide)
    d = d.head(n_max)[[categorie, valeur]].rename(columns={categorie: "cat", valeur: "val"})
    base = alt.Chart(d).encode(
        x=alt.X("val:Q", title=titre_valeur, axis=alt.Axis(tickCount=8),
                scale=alt.Scale(domain=list(domaine)) if domaine else alt.Scale(zero=True)),
        y=alt.Y("cat:N", sort="-x", title=None, axis=alt.Axis(labelLimit=260)),
        tooltip=[alt.Tooltip("cat:N", title="Nom"), alt.Tooltip("val:Q", title=titre_valeur, format=fmt)],
    )
    chart = ((base.mark_bar(color=BLEU, cornerRadiusEnd=4, height=16)
              + base.mark_text(align="left", dx=4, color="#52514e", fontSize=11)
                    .encode(text=alt.Text("val:Q", format=fmt)))
             .properties(height=max(160, 26 * len(d)))
             .configure_axis(grid=False, labelColor="#52514e", titleColor="#52514e")
             .configure_view(strokeWidth=0))
    st.altair_chart(chart, use_container_width=True)


def filtre_championnat(long, key):
    ligues = ["Tous les championnats"] + sorted(long["div"].unique(), key=lambda c: sc.noms.get(c, c))
    choix = st.selectbox("Championnat", ligues, key=key,
                         format_func=lambda c: c if c.startswith("Tous") else libelle(c))
    return long if choix.startswith("Tous") else long[long["div"] == choix]


def note_mi_temps(indicateur):
    if sc.besoin_mi_temps(indicateur):
        st.info("Cet état utilise le score à la mi-temps : les championnats extra "
                "(USA, ARG, BRA, SWE, JPN, NOR) n'ont pas cette donnée et sont exclus.")


def afficher(vue, stat, pct, nom_csv, key, label_graph):
    """Graphique + tableau + export d'une vue déjà renommée."""
    if vue.empty:
        st.warning("Aucune donnée ne remplit les conditions (essaie de baisser le minimum de matchs).")
        return
    graphique_barres(vue, label_graph, pct, pct, n_max=25)
    cfg = {pct: col_pct(pct)}
    st.dataframe(vue, hide_index=True, use_container_width=True, height=min(38 + 35 * len(vue), 760),
                 column_config=cfg)
    bouton_csv(vue, nom_csv, key)


# =========================================================
# PAGES
# =========================================================
def page_etat(etat):
    num, titre, typ, ind, stat, pct, aide = etat
    st.header(f"{num}. {titre}")
    if aide:
        st.caption(aide)

    if typ == "champ":
        note_mi_temps(ind)
        t = sc.tableau_championnats(M, ind)
        if t.empty:
            st.warning("Pas de données pour cet état.")
            return
        vue = t.rename(columns={"top": "Rang", "league": "Championnat", "total_matches": "Matchs joués",
                                "yes_matches": stat, "%_yes_matches": pct})[
            ["Rang", "Championnat", "Matchs joués", stat, pct]]
        moyenne = round(t["yes_matches"].sum() / t["total_matches"].sum() * 100)
        c1, c2, c3 = st.columns(3)
        c1.metric(f"1er : {vue.iloc[0]['Championnat']}", f"{vue.iloc[0][pct]} %")
        c2.metric(f"Dernier : {vue.iloc[-1]['Championnat']}", f"{vue.iloc[-1][pct]} %")
        c3.metric("Moyenne tous championnats", f"{moyenne} %")
        afficher(vue, stat, pct, f"etat_{num}.csv", f"csv_{num}", "Championnat")
        return

    # Filtres de la page : championnat + nombre d'équipes (+ derniers matchs pour la forme)
    if typ == "forme":
        f1, f2, f3 = st.columns([3, 1, 1])
        with f3:
            n_last = st.number_input("Derniers matchs", 3, 10, 5, key=f"n_{num}")
    else:
        f1, f2 = st.columns([3, 1])
    with f1:
        base = filtre_championnat(LONG, f"lig_{num}")
    nb = f2.selectbox("Nombre d'équipes", NB_EQUIPES, index=NB_EQUIPES.index(20), key=f"nb_{num}",
                      format_func=lambda x: "Toutes" if x == 0 else str(x))

    if typ == "equipe":
        note_mi_temps(ind)
        t = sc.tableau_equipes(base, ind, MIN_MATCHES, None)
        if t.empty:
            st.warning("Aucune équipe ne remplit les conditions (essaie de baisser le minimum de matchs).")
            return
        vue = t.rename(columns={"top": "Rang", "team": "Équipe", "league": "Championnat",
                                "total_matches": "Matchs joués", "yes_matches": stat, "%_yes_matches": pct})[
            ["Rang", "Équipe", "Championnat", "Matchs joués", stat, pct]]

    elif typ == "resultats":
        t = sc.tableau_resultats(base, ind, MIN_MATCHES, None)
        if t.empty:
            st.warning("Aucune équipe ne remplit les conditions (essaie de baisser le minimum de matchs).")
            return
        ordre = {"W": ["Victoires", "Nuls", "Défaites"], "L": ["Défaites", "Nuls", "Victoires"],
                 "D": ["Nuls", "Victoires", "Défaites"]}[ind]
        vue = t.rename(columns={"top": "Rang", "team": "Équipe", "league": "Championnat",
                                "total_matches": "Matchs joués", "win_matches": "Victoires",
                                "draw_matches": "Nuls", "loss_matches": "Défaites", "pct": pct})[
            ["Rang", "Équipe", "Championnat", "Matchs joués"] + ordre + [pct]]

    else:  # forme
        t = sc.tableau_forme(base, int(n_last), ind, None)
        st.caption("Forme : du match le plus ancien (à gauche) au plus récent (à droite). "
                   "W = victoire, D = nul, L = défaite. Vérifie la date du dernier match : "
                   "une série ancienne pèse moins qu'une série en cours.")
        if t.empty:
            st.warning("Pas assez de matchs.")
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
        st.caption(f"{len(vue)} équipes affichées sur {total} classées")
        st.dataframe(vue, hide_index=True, use_container_width=True, height=min(38 + 35 * len(vue), 760))
        bouton_csv(vue, f"etat_{num}.csv", f"csv_{num}")
        return

    total = len(vue)
    vue = vue.head(nb) if nb else vue
    st.caption(f"{len(vue)} équipes affichées sur {total} classées · "
               f"minimum {MIN_MATCHES} matchs joués")
    graph = vue.assign(_label=vue["Équipe"] + " · " + vue["Championnat"])
    if vue.empty:
        st.warning("Aucune équipe.")
        return
    graphique_barres(graph, "_label", pct, pct, n_max=min(nb or 30, 30))
    st.dataframe(vue, hide_index=True, use_container_width=True, height=min(38 + 35 * len(vue), 760),
                 column_config={pct: col_pct(pct)})
    bouton_csv(vue, f"etat_{num}.csv", f"csv_{num}")


def page_stats(etat):
    num, titre, niveau, sens, mesure = etat
    st.header(f"{num}. {titre}")
    mot = "marqués" if sens == "for" else "encaissés"
    nom_mesure = "Moyenne" if mesure == "mean" else "Médiane"
    st.caption(f"{nom_mesure} des buts {mot} par match"
               + (" et par équipe, sur tous les matchs du championnat." if niveau == "champ" else ".")
               + (" La médiane est la valeur du milieu : la moitié des matchs sont au-dessus, la moitié en dessous."
                  if mesure == "median" else ""))
    if niveau == "champ":
        t = sc.stats_buts_championnats(LONG, sens)
        if sens == "against":
            st.info("Au total, la moyenne de buts encaissés d'un championnat est égale à sa moyenne de buts marqués "
                    "(chaque but marqué est encaissé par l'adversaire). La différence se voit à domicile / à l'extérieur.")
        ordre = st.radio("Ordre", ["Plus élevé d'abord", "Plus bas d'abord"], horizontal=True, key=f"o_{num}")
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
        nb = f2.selectbox("Nombre d'équipes", NB_EQUIPES, index=NB_EQUIPES.index(20), key=f"nb_{num}",
                          format_func=lambda x: "Toutes" if x == 0 else str(x))
        ordre = f3.selectbox("Ordre", ["Plus élevé d'abord", "Plus bas d'abord"], key=f"o_{num}")
        t = sc.stats_buts_equipes(base, sens, MIN_MATCHES)
        if t.empty:
            st.warning("Aucune équipe ne remplit les conditions (essaie de baisser le minimum de matchs).")
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
        st.caption(f"{len(vue)} équipes affichées sur {total} classées · minimum {MIN_MATCHES} matchs joués")
        graphique_barres(vue.assign(_label=vue["Équipe"] + " · " + vue["Championnat"]), "_label", lab, lab,
                         n_max=min(nb or 30, 30), domaine=None, fmt=".2f")
    st.dataframe(vue, hide_index=True, use_container_width=True, height=min(38 + 35 * len(vue), 760),
                 column_config={c: st.column_config.NumberColumn(c, format="%.2f")
                                for c in vue.columns if c.startswith(("Moyenne", "Médiane"))})
    bouton_csv(vue, f"etat_{num}.csv", f"csv_{num}")


def page_tickets(nom):
    titre = {"Combiné": "combiné", "BTTS - les deux équipes marquent": "BTTS : les deux équipes marquent"}
    st.header(f"🎟️ Ticket {titre.get(nom, nom.lower())}")
    modeles = sc.modeles_par_championnat(M)
    parts = sc.parts_1re_periode(M)
    fixtures = charger_fixtures()
    if fixtures.empty:
        st.info("Aucun prochain match disponible pour le moment.")
        return
    aujourd_hui = pd.Timestamp.today().normalize()
    divs_dispo = sorted(set(fixtures["div"]) & set(M["div"]), key=lambda x: sc.noms.get(x, x))
    ss = st.session_state                     # réglages mémorisés d'un ticket à l'autre
    ss.setdefault("t_n", 10)
    ss.setdefault("t_jours", 7)
    ss.setdefault("t_divs", divs_dispo)
    a, b, c = st.columns([1, 1, 2])
    n = a.number_input("Nombre de matchs", min_value=1, max_value=30, value=ss["t_n"], step=1,
                       help="10 par défaut ; tu peux en ajouter jusqu'à 30.", key=f"w_n_{nom}")
    jours = b.selectbox("Période", [3, 7, 14, 0], index=[3, 7, 14, 0].index(ss["t_jours"]), key=f"w_j_{nom}",
                        format_func=lambda x: "Tous les matchs à venir" if x == 0 else f"{x} prochains jours")
    divs = c.multiselect("Championnats", divs_dispo, default=[d for d in ss["t_divs"] if d in divs_dispo],
                         format_func=libelle, key=f"w_d_{nom}")
    ss["t_n"], ss["t_jours"], ss["t_divs"] = n, jours, divs

    fx = fixtures[fixtures["div"].isin(divs) & (fixtures["date"] >= aujourd_hui)]
    if jours:
        fx = fx[fx["date"] <= aujourd_hui + pd.Timedelta(days=jours)]
    pred = sc.predictions_detaillees(fx, modeles, parts, MIN_MATCHES)
    if pred.empty:
        st.info("Aucun match à venir pour ces critères (période, championnats, minimum de matchs joués).")
        return
    st.caption(f"{len(pred)} matchs à venir analysés · équipes ayant joué au moins {MIN_MATCHES} matchs.")

    if nom == "Combiné":
        t = sc.ticket_combine(pred, int(n))
        st.caption("Le meilleur pronostic de chaque type de ticket (un match n'est utilisé qu'une fois), "
                   "complété par les pronostics les plus probables restants.")
    else:
        t = sc.construire_ticket(pred, nom, int(n))
        st.caption("Les matchs où cet événement est le plus probable selon le modèle.")
        if nom == "Défaites":
            st.caption("« Défaite X » : l'équipe X perd le match (son adversaire gagne).")
        if nom == "Scores exacts":
            st.caption("Un score exact reste un pari très incertain : même le plus probable dépasse "
                       "rarement 15 à 20 %.")
    afficher_ticket(t, nom, combine=(nom == "Combiné"))
    st.warning("Les probabilités d'un ticket se multiplient : plus il y a de matchs, plus la probabilité que "
               "tout passe est faible. Ce sont des estimations statistiques, pas des certitudes.")


def afficher_ticket(t, nom, combine=False):
    if t.empty:
        st.info("Pas de match disponible pour ce ticket.")
        return
    vue = pd.DataFrame({"N°": range(1, len(t) + 1),
                        "Date": t["date"].dt.strftime("%d/%m/%Y"), "Heure": t["time"],
                        "Championnat": t["league"], "Match": t["match"]})
    if combine:
        vue["Type"] = t["ticket_type"].values
    vue["Pronostic"] = t["pick"].values
    vue["Probabilité"] = (t["proba"] * 100).round(0).astype(int).values
    vue["Cote juste"] = (1 / t["proba"]).round(2).values
    cotes = pd.to_numeric(t["market_odds"], errors="coerce")
    if cotes.notna().any():
        vue["Cote marché"] = cotes.values
    p_tout = float(np.prod(t["proba"]))
    k1, k2, k3 = st.columns(3)
    k1.metric("Matchs", len(t))
    k2.metric("Probabilité que tout passe", f"{p_tout * 100:.1f} %" if p_tout >= 0.001 else "< 0,1 %")
    k3.metric("Cote juste du ticket", f"{1 / p_tout:,.2f}".replace(",", " ") if p_tout > 0 else "-")
    st.dataframe(vue, hide_index=True, use_container_width=True, height=min(38 + 35 * len(vue), 760),
                 column_config={"Probabilité": col_pct("Probabilité")})
    bouton_csv(vue, f"ticket_{nom.lower().replace(' ', '_')}.csv", f"csv_t_{nom}")


def page_donnees():
    st.header("Accueil · données chargées (états 1 à 3)")
    st.caption("Paramètres, chargement et combinaison des championnats (cellules 1 à 3 du notebook).")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Championnats", M["div"].nunique())
    c2.metric("Matchs joués", f"{len(M):,}".replace(",", " "))
    c3.metric("Équipes", LONG[["team", "div"]].drop_duplicates().shape[0])
    c4.metric("Dernier match", M["date"].max().strftime("%d/%m/%Y") if M["date"].notna().any() else "-")

    st.subheader("Journal de chargement")
    j = pd.DataFrame(JOURNAL, columns=["Code", "Statut", "Matchs"])
    j["Statut"] = j["Statut"].map(lambda x: "✅ Chargé" if x == "OK" else "❌ Indisponible")
    j["Championnat"] = j["Code"].map(sc.noms)
    st.dataframe(j[["Championnat", "Code", "Statut", "Matchs"]], hide_index=True, use_container_width=True)

    st.subheader("Tous les matchs")
    a, b = st.columns(2)
    with a:
        d = filtre_championnat(M.rename(columns={}), "lig_data")
    recherche = b.text_input("Rechercher une équipe")
    if recherche:
        d = d[d["home_team"].str.contains(recherche, case=False) | d["away_team"].str.contains(recherche, case=False)]
    d = d.sort_values("date", ascending=False)
    vue = pd.DataFrame({
        "Date": d["date"].dt.strftime("%d/%m/%Y"), "Championnat": d["league"], "Saison": d["season"],
        "Domicile": d["home_team"], "Extérieur": d["away_team"],
        "Buts dom.": d["fthg"].astype("Int64"), "Buts ext.": d["ftag"].astype("Int64"),
        "Mi-temps dom.": d["hthg"].astype("Int64"), "Mi-temps ext.": d["htag"].astype("Int64"),
        "Cote 1": d["odds_h"], "Cote N": d["odds_d"], "Cote 2": d["odds_a"]})
    st.caption(f"{len(vue)} matchs")
    st.dataframe(vue, hide_index=True, use_container_width=True, height=500)
    bouton_csv(vue, "matchs.csv", "csv_data")


def page_predictions():
    st.header("🔮 Prédictions")
    modeles = sc.modeles_par_championnat(M)
    st.markdown("Modèle de **Poisson** : pour chaque équipe, forces d'attaque et de défense à domicile et à "
                "l'extérieur par rapport à la moyenne de son championnat (lissées en début de saison), d'où les "
                "buts attendus puis les probabilités de chaque score.")
    st.warning("Ce sont des estimations statistiques, pas des certitudes : blessures, rotations, météo ou enjeu "
               "ne sont pas pris en compte. À utiliser avec prudence.")
    sous = st.tabs(["📅 Prochains matchs", "🎯 Match au choix"])

    with sous[0]:
        fixtures = charger_fixtures()
        pred = (sc.predire_prochains_matchs(fixtures[fixtures["div"].isin(M["div"].unique())], modeles)
                if not fixtures.empty else pd.DataFrame())
        if pred.empty:
            st.info("Aucun prochain match disponible pour les championnats chargés. Utilise « Match au choix ».")
        else:
            a, b = st.columns(2)
            lig = a.selectbox("Championnat", ["Tous les championnats"] + sorted(pred["div"].unique()),
                              format_func=lambda x: x if x.startswith("Tous") else libelle(x), key="lig_pred")
            tris = {"Date": "date", "Victoire domicile": "%_home", "Victoire extérieur": "%_away",
                    "BTTS": "%_btts", "Over 2.5": "%_over_2_5", "Over 1.5": "%_over_1_5"}
            tri = tris[b.selectbox("Trier par", list(tris), key="tri_pred")]
            p = pred if lig.startswith("Tous") else pred[pred["div"] == lig]
            p = p.sort_values(tri, ascending=(tri == "date"))
            vue = pd.DataFrame({
                "Date": p["date"].dt.strftime("%d/%m/%Y"), "Heure": p["time"], "Championnat": p["league"],
                "Domicile": p["home_team"], "Extérieur": p["away_team"],
                "% victoire dom.": p["%_home"], "% nul": p["%_draw"], "% victoire ext.": p["%_away"],
                "% BTTS": p["%_btts"], "% over 1.5": p["%_over_1_5"], "% over 2.5": p["%_over_2_5"],
                "% over 3.5": p["%_over_3_5"], "Score probable": p["likely_score"],
                "Buts attendus": p["xg_home"].round(1).astype(str) + " - " + p["xg_away"].round(1).astype(str),
                "Cote 1": p["odds_h"], "Cote N": p["odds_d"], "Cote 2": p["odds_a"]})
            cfg = {c: col_pct(c) for c in vue.columns if c.startswith("%")}
            st.dataframe(vue, hide_index=True, use_container_width=True, height=500, column_config=cfg)
            st.caption("Cotes 1 / N / 2 : cotes moyennes du marché. "
                       "Cote « juste » selon le modèle = 100 / pourcentage.")
            bouton_csv(vue, "predictions.csv", "csv_pred")

    with sous[1]:
        a, b, c = st.columns(3)
        divs = sorted(modeles, key=lambda x: sc.noms.get(x, x))
        lig = a.selectbox("Championnat", divs, format_func=libelle, key="lig_match")
        equipes = list(modeles[lig]["forces"].index)
        dom = b.selectbox("Domicile", equipes, index=0, key="dom")
        ext = c.selectbox("Extérieur", equipes, index=min(1, len(equipes) - 1), key="ext")
        if dom == ext:
            st.warning("Choisis deux équipes différentes.")
            return
        p = sc.predire(modeles[lig], dom, ext)
        st.subheader(f"{dom}  vs  {ext}")
        k1, k2, k3 = st.columns(3)
        for col, lab, pr in [(k1, f"Victoire {dom}", p["p_home"]), (k2, "Match nul", p["p_draw"]),
                             (k3, f"Victoire {ext}", p["p_away"])]:
            col.metric(lab, f"{pr * 100:.0f} %")
            col.caption(f"Cote « juste » : {1 / pr:.2f}")
        d1x2 = pd.DataFrame({"issue": [dom, "Nul", ext],
                             "proba": [p["p_home"] * 100, p["p_draw"] * 100, p["p_away"] * 100]})
        chart = (alt.Chart(d1x2).mark_bar(cornerRadiusEnd=4)
                 .encode(x=alt.X("proba:Q", title="Probabilité (%)", scale=alt.Scale(domain=[0, 100])),
                         y=alt.Y("issue:N", sort=None, title=None, scale=alt.Scale(paddingInner=0.35),
                                 axis=alt.Axis(labelLimit=220)),
                         color=alt.Color("issue:N", scale=alt.Scale(domain=[dom, "Nul", ext], range=COULEURS_1X2),
                                         legend=None),
                         tooltip=[alt.Tooltip("issue:N", title="Issue"), alt.Tooltip("proba:Q", title="%", format=".0f")])
                 .properties(height=140)
                 .configure_axis(grid=False, labelColor="#52514e", titleColor="#52514e")
                 .configure_view(strokeWidth=0))
        st.altair_chart(chart, use_container_width=True)
        k4, k5, k6, k7, k8 = st.columns(5)
        k4.metric("Buts attendus", f"{p['xg_home']:.2f} - {p['xg_away']:.2f}")
        k5.metric("BTTS", f"{p['p_btts'] * 100:.0f} %")
        k6.metric("Over 1.5", f"{p['p_over15'] * 100:.0f} %")
        k7.metric("Over 2.5", f"{p['p_over25'] * 100:.0f} %")
        k8.metric("Over 3.5", f"{p['p_over35'] * 100:.0f} %")
        s1, s2 = st.columns([1, 2])
        with s1:
            st.markdown("**Scores les plus probables**")
            st.dataframe(pd.DataFrame([{"Score": s, "Probabilité": f"{pr * 100:.1f} %"} for pr, s in p["top_scores"]]),
                         hide_index=True)
        with s2:
            st.markdown(f"**{dom} marque** : {p['p_home_scores'] * 100:.0f} %  ·  "
                        f"**{ext} marque** : {p['p_away_scores'] * 100:.0f} %")
            f = modeles[lig]["forces"]
            st.dataframe(pd.DataFrame({
                "Équipe": [dom, ext],
                "Force d'attaque": [f"{f.at[dom, 'home_att']:.2f} (dom.)", f"{f.at[ext, 'away_att']:.2f} (ext.)"],
                "Force de défense": [f"{f.at[dom, 'home_def']:.2f} (dom.)", f"{f.at[ext, 'away_def']:.2f} (ext.)"],
                "Matchs joués": [int(f.at[dom, "matches"]), int(f.at[ext, "matches"])]}), hide_index=True)
            st.caption("Attaque > 1 : marque plus que la moyenne du championnat. "
                       "Défense > 1 : encaisse plus que la moyenne.")


# =========================================================
# EN-TÊTE COMMUN : TITRE + PARAMÈTRES
# =========================================================
st.markdown("""
<style>
.block-container {padding-top: 4.2rem;}
div[data-testid="stMetricValue"] {font-size: 1.9rem;}
</style>""", unsafe_allow_html=True)

h1, h2 = st.columns([5, 1], vertical_alignment="center")
h1.markdown("### ⚽ Stats & Prédictions Foot")
with h2.popover("⚙️ Paramètres", use_container_width=True):
    saison = st.text_input("Saison européenne", value=sc.SAISON, help="2627 = 2026-27, 2526 = 2025-26")
    codes_main = st.multiselect("Championnats européens", sc.MAIN_CODES, default=sc.MAIN_CODES, format_func=libelle)
    codes_extra = st.multiselect("Championnats extra", sc.extra_leagues, default=sc.extra_leagues,
                                 format_func=libelle)
    MIN_MATCHES = st.slider("Minimum de matchs joués", 1, 15, 5)
    if st.button("🔄 Actualiser les données", use_container_width=True):
        st.cache_data.clear()

MATCHES, JOURNAL = charger(saison, tuple(codes_main), tuple(codes_extra))
if MATCHES.empty:
    st.error("Aucune donnée n'a pu être chargée. Vérifie ta connexion internet, la saison et les championnats choisis.")
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
    return st.Page(page, title=f"{etat[0]}. {COURTS[etat[0]]}", url_path=f"etat-{etat[0]}")


def creer_page_stats(etat):
    def page():
        page_stats(etat)
    page.__name__ = f"stats_{etat[0]}"
    return st.Page(page, title=f"{etat[0]}. {COURTS[etat[0]]}", url_path=f"etat-{etat[0]}")


def creer_page_ticket(nom):
    def page():
        page_tickets(nom)
    slug = "btts" if nom.startswith("BTTS") else (
        nom.lower().replace(" ", "-").replace(".", "").replace("é", "e").replace("è", "e"))
    page.__name__ = f"ticket_{slug.replace('-', '_')}"
    titre = {"Combiné": "⭐ Combiné", "BTTS - les deux équipes marquent": "BTTS (les 2 équipes marquent)"}.get(nom, nom)
    return st.Page(page, title=titre, url_path=f"ticket-{slug}")


def section(nums):
    return [creer_page(e) for e in ETATS if e[0] in nums]


menu = {
    "": [st.Page(page_donnees, title="Accueil", icon="🏠", url_path="donnees", default=True),
         st.Page(page_predictions, title="Prédictions", icon="🔮", url_path="predictions")],
    "🎯 Buts du match": section(range(4, 12)),
    "🏁 Résultats": section(range(12, 15)),
    "⏱️ Mi-temps": section(range(15, 21)),
    "⚽ Marqués": section(range(21, 27)),
    "🛡️ Encaissés": [creer_page(e) for e in BONUS],
    "📈 Forme": section([27, 28, 41]),
    "📊 Stats": [creer_page_stats(e) for e in ETATS_STATS],
    "🎟️ Tickets": [creer_page_ticket(x) for x in ["Combiné"] + list(sc.TICKETS)],   # dernier onglet
}

st.navigation(menu, position="top").run()
st.divider()
st.caption("Pourcentages arrondis à l'entier · Rang : 1, 2, 3… (à égalité, départage par nombre de matchs puis ordre alphabétique) · "
           "Données mises à jour automatiquement toutes les 3 heures.")
