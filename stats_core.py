"""
stats_core.py - Moteur de calcul de l'application "Stats & Prédictions Foot".

Reprend les analyses du notebook STAT_DES_MATCHS sous forme de fonctions :
  - chargement des championnats football-data.co.uk (européens + extra)
  - tableaux par championnat et par équipe (BTTS, over, victoires, mi-temps...)
  - forme sur les N derniers matchs
  - modèle de prédiction de Poisson (1X2, BTTS, over, scores probables)

Source des données : https://www.football-data.co.uk
Pour travailler hors ligne, définir la variable d'environnement FOOT_DATA_DIR :
les fichiers sont alors lus dans <FOOT_DATA_DIR>/<saison>/<code>.csv,
<FOOT_DATA_DIR>/new/<code>.csv et <FOOT_DATA_DIR>/fixtures.csv.
"""

import math
import os

import numpy as np
import pandas as pd

# =========================================================
# 1. PARAMÈTRES
# =========================================================
SAISON = "2627"

_DATA_DIR = os.environ.get("FOOT_DATA_DIR")
if _DATA_DIR:
    URL_MAIN = os.path.join(_DATA_DIR, "{saison}", "{code}.csv")
    URL_EXTRA = os.path.join(_DATA_DIR, "new", "{code}.csv")
    URL_FIXTURES = os.path.join(_DATA_DIR, "fixtures.csv")
    URL_FIXTURES_EXTRA = os.path.join(_DATA_DIR, "new_league_fixtures.csv")
else:
    URL_MAIN = "https://www.football-data.co.uk/mmz4281/{saison}/{code}.csv"
    URL_EXTRA = "https://www.football-data.co.uk/new/{code}.csv"
    URL_FIXTURES = "https://www.football-data.co.uk/fixtures.csv"
    URL_FIXTURES_EXTRA = "https://www.football-data.co.uk/new_league_fixtures.csv"

championnats = {
    'E': list(range(4)),    # england
    'D': list(range(1, 3)), # germany
    'I': list(range(1, 3)), # italy
    'F': list(range(1, 3)), # france
    'SP': list(range(1, 3)),# spain
    'P': [1],               # portugal
    'N': [1],               # netherlands
    'SC': list(range(4)),   # scotland
    'B': [1],               # belgium
    'T': [1]                # turkey
}
MAIN_CODES = [f"{p}{d}" for p, divs in championnats.items() for d in divs]

extra_leagues = ["USA", "ARG", "BRA", "SWE", "JPN", "NOR"]

noms = {
    "E0": "Premier League", "E1": "Championship", "E2": "League One", "E3": "League Two",
    "D1": "Bundesliga", "D2": "2. Bundesliga", "I1": "Serie A", "I2": "Serie B",
    "F1": "Ligue 1", "F2": "Ligue 2", "SP1": "La Liga", "SP2": "La Liga 2",
    "P1": "Liga Portugal", "N1": "Eredivisie", "SC0": "Scottish Premiership",
    "SC1": "Scottish Championship", "SC2": "Scottish League One", "SC3": "Scottish League Two",
    "B1": "Pro League (Belgium)", "T1": "Süper Lig (Turkey)",
    "USA": "MLS (USA)", "ARG": "Liga Profesional (Argentina)", "BRA": "Série A (Brazil)",
    "SWE": "Allsvenskan (Sweden)", "JPN": "J1 League (Japan)", "NOR": "Eliteserien (Norway)",
}

# Pays des fichiers "extra" -> code championnat (pour les prochains matchs)
PAYS_EXTRA = {"USA": "USA", "Argentina": "ARG", "Brazil": "BRA",
              "Sweden": "SWE", "Japan": "JPN", "Norway": "NOR"}

RENOMMAGE_EXTRA = {"Home": "HomeTeam", "Away": "AwayTeam",
                   "HG": "FTHG", "AG": "FTAG", "Res": "FTR"}

# Colonnes standard du tableau des matchs
COLONNES = ["div", "league", "season", "date", "time", "home_team", "away_team",
            "fthg", "ftag", "hthg", "htag", "odds_h", "odds_d", "odds_a"]


# =========================================================
# 2. CHARGEMENT
# =========================================================
def lire_csv(url):
    try:
        return pd.read_csv(url, encoding="utf-8-sig", on_bad_lines="skip")
    except UnicodeDecodeError:
        return pd.read_csv(url, encoding="latin-1", on_bad_lines="skip")


def nettoyer(df):
    # supprime le BOM et les espaces dans les noms de colonnes
    df.columns = df.columns.str.replace("﻿", "").str.replace("ï»¿", "").str.strip()
    return df.loc[:, ~df.columns.str.startswith("Unnamed")].dropna(how="all")


def _premiere_colonne(df, candidats):
    for c in candidats:
        if c in df.columns:
            return pd.to_numeric(df[c], errors="coerce")
    return pd.Series(np.nan, index=df.index)


def standardiser(df, code, season):
    """Ramène un fichier football-data.co.uk au format standard COLONNES."""
    out = pd.DataFrame(index=df.index)
    out["div"] = code
    out["league"] = noms.get(code, code)
    out["season"] = season
    out["date"] = pd.to_datetime(df.get("Date"), dayfirst=True, errors="coerce")
    out["time"] = df.get("Time", pd.Series("", index=df.index)).fillna("").astype(str)
    out["home_team"] = df.get("HomeTeam").astype(str).str.strip()
    out["away_team"] = df.get("AwayTeam").astype(str).str.strip()
    out["fthg"] = _premiere_colonne(df, ["FTHG"])
    out["ftag"] = _premiere_colonne(df, ["FTAG"])
    out["hthg"] = _premiere_colonne(df, ["HTHG"])     # absent des fichiers extra -> NaN
    out["htag"] = _premiere_colonne(df, ["HTAG"])
    # cotes moyennes du marché (avant-match si dispo, sinon clôture)
    out["odds_h"] = _premiere_colonne(df, ["AvgH", "AvgCH", "B365H", "B365CH"])
    out["odds_d"] = _premiere_colonne(df, ["AvgD", "AvgCD", "B365D", "B365CD"])
    out["odds_a"] = _premiere_colonne(df, ["AvgA", "AvgCA", "B365A", "B365CA"])
    return out[COLONNES]


def charger_main(code, saison=SAISON):
    df = nettoyer(lire_csv(URL_MAIN.format(saison=saison, code=code)))
    return standardiser(df, code, f"20{saison[:2]}-{saison[2:]}")


def charger_extra(code, saison_extra=None):
    df = nettoyer(lire_csv(URL_EXTRA.format(code=code)))
    df = df.rename(columns=RENOMMAGE_EXTRA)
    # le fichier contient toutes les saisons : on garde la plus récente (ou celle demandée)
    df["Season"] = df["Season"].astype(str).str.strip()
    saison = str(saison_extra) if saison_extra else df["Season"].max()
    df = df[df["Season"] == saison].copy()
    return standardiser(df, code, saison)


def charger_tout(codes_main=MAIN_CODES, codes_extra=extra_leagues, saison=SAISON, saison_extra=None):
    """Charge tous les championnats demandés. Renvoie (matches, journal)."""
    frames, journal = [], []
    for code in codes_main:
        try:
            df = charger_main(code, saison)
            frames.append(df)
            journal.append((code, "OK", len(df)))
        except Exception as e:                     # fichier absent, réseau...
            journal.append((code, f"ERREUR : {e}", 0))
    for code in codes_extra:
        try:
            df = charger_extra(code, saison_extra)
            frames.append(df)
            journal.append((code, "OK", len(df)))
        except Exception as e:
            journal.append((code, f"ERREUR : {e}", 0))
    if not frames:
        return pd.DataFrame(columns=COLONNES), journal
    matches = pd.concat(frames, ignore_index=True)
    return matches, journal


def matchs_joues(matches):
    """Matchs avec un score final, enrichis des indicateurs utilisés partout."""
    m = matches.dropna(subset=["fthg", "ftag"]).copy()
    m["total_goals"] = m["fthg"] + m["ftag"]
    m["first_half_goals"] = m["hthg"] + m["htag"]                     # NaN sans mi-temps
    m["second_half_goals"] = m["total_goals"] - m["first_half_goals"]
    return m


def vue_equipes(m):
    """Une ligne par équipe et par match (domicile + extérieur)."""
    base = ["div", "league", "season", "date", "total_goals", "first_half_goals", "second_half_goals"]
    dom = m[base + ["home_team", "away_team", "fthg", "ftag"]].rename(columns={
        "home_team": "team", "away_team": "opponent", "fthg": "goals_for", "ftag": "goals_against"})
    dom["venue"] = "H"
    ext = m[base + ["away_team", "home_team", "ftag", "fthg"]].rename(columns={
        "away_team": "team", "home_team": "opponent", "ftag": "goals_for", "fthg": "goals_against"})
    ext["venue"] = "A"
    long = pd.concat([dom, ext], ignore_index=True)
    long["result"] = np.select(
        [long["goals_for"] > long["goals_against"], long["goals_for"] < long["goals_against"]],
        ["W", "L"], default="D")
    return long


# =========================================================
# 3. INDICATEURS (une condition "yes" par match ou par équipe)
# =========================================================
# Indicateurs calculables au niveau du match (championnat ET équipe)
INDICATEURS_MATCH = {
    "BTTS - les deux équipes marquent": (lambda d: (d["fthg"] > 0) & (d["ftag"] > 0), False),
    "Au moins 2 buts dans le match (over 1.5)": (lambda d: d["total_goals"] >= 2, False),
    "Au moins 3 buts dans le match (over 2.5)": (lambda d: d["total_goals"] >= 3, False),
    "Au moins 4 buts dans le match (over 3.5)": (lambda d: d["total_goals"] >= 4, False),
    "Plus de buts en 1re qu'en 2e période": (lambda d: d["first_half_goals"] > d["second_half_goals"], True),
    "Plus de buts en 2e qu'en 1re période": (lambda d: d["second_half_goals"] > d["first_half_goals"], True),
    "Autant de buts dans les deux périodes": (lambda d: d["first_half_goals"] == d["second_half_goals"], True),
}
# Indicateurs propres à l'équipe (calculés sur la vue_equipes)
INDICATEURS_EQUIPE = {
    "Victoires": (lambda d: d["result"] == "W", False),
    "Matchs nuls": (lambda d: d["result"] == "D", False),
    "Défaites": (lambda d: d["result"] == "L", False),
    "L'équipe marque au moins 1 but": (lambda d: d["goals_for"] >= 1, False),
    "L'équipe marque au moins 2 buts": (lambda d: d["goals_for"] >= 2, False),
    "L'équipe marque au moins 3 buts": (lambda d: d["goals_for"] >= 3, False),
    "L'équipe marque au moins 4 buts": (lambda d: d["goals_for"] >= 4, False),
    "L'équipe marque moins de 2 buts": (lambda d: d["goals_for"] < 2, False),
    "L'équipe ne marque pas (moins de 1 but)": (lambda d: d["goals_for"] < 1, False),
    "L'équipe n'encaisse pas (clean sheet)": (lambda d: d["goals_against"] < 1, False),
    "L'équipe encaisse au moins 1 but": (lambda d: d["goals_against"] >= 1, False),
    "L'équipe encaisse au moins 2 buts": (lambda d: d["goals_against"] >= 2, False),
    "L'équipe encaisse au moins 3 buts": (lambda d: d["goals_against"] >= 3, False),
}
# Pour les équipes : on reprend la vue_equipes, où les colonnes de match sont renommées
def _btts_equipe(d):
    return (d["goals_for"] > 0) & (d["goals_against"] > 0)


def condition_equipe(nom, long):
    if nom in INDICATEURS_EQUIPE:
        return INDICATEURS_EQUIPE[nom][0](long)
    if nom.startswith("BTTS"):
        return _btts_equipe(long)
    return INDICATEURS_MATCH[nom][0](long)


def besoin_mi_temps(nom):
    if nom in INDICATEURS_MATCH:
        return INDICATEURS_MATCH[nom][1]
    return False


def _finaliser(t, cles, top_n=None):
    t["no_yes_matches"] = t["total_matches"] - t["yes_matches"]
    t["%_yes_matches"] = (t["yes_matches"] / t["total_matches"] * 100).round(0).astype(int)
    # rang continu 1, 2, 3... (pas d'ex aequo) : % puis nombre de matchs puis ordre alphabétique
    t = t.sort_values(["%_yes_matches", "total_matches"] + cles, ascending=[False, False] + [True] * len(cles))
    t.insert(0, "top", range(1, len(t) + 1))
    t = t[["top"] + cles + ["league", "season", "total_matches",
                             "yes_matches", "no_yes_matches", "%_yes_matches"]]
    t = t.reset_index(drop=True)
    if top_n:
        t = t[t["top"] <= top_n]
    return t


def tableau_championnats(m, nom):
    """Tableau par championnat pour un indicateur de INDICATEURS_MATCH."""
    fn, mi_temps = INDICATEURS_MATCH[nom]
    d = m.dropna(subset=["first_half_goals"]) if mi_temps else m
    if d.empty:
        return pd.DataFrame()
    d = d.assign(yes=fn(d))
    t = (d.groupby("div")
          .agg(league=("league", "first"), season=("season", "first"),
               total_matches=("yes", "size"), yes_matches=("yes", "sum"))
          .reset_index())
    return _finaliser(t, ["div"])


def tableau_equipes(long, nom, min_matches=5, top_n=50):
    """Tableau par équipe pour n'importe quel indicateur."""
    d = long.dropna(subset=["first_half_goals"]) if besoin_mi_temps(nom) else long
    if d.empty:
        return pd.DataFrame()
    d = d.assign(yes=condition_equipe(nom, d))
    t = (d.groupby(["team", "div"])
          .agg(league=("league", "first"), season=("season", "first"),
               total_matches=("yes", "size"), yes_matches=("yes", "sum"))
          .reset_index())
    t = t[t["total_matches"] >= min_matches].copy()
    if t.empty:
        return pd.DataFrame()
    return _finaliser(t, ["team", "div"], top_n)


def tableau_resultats(long, critere="W", min_matches=5, top_n=50):
    """
    États 12 à 14 du notebook : équipes avec le plus de victoires ('W'), de défaites ('L')
    ou de matchs nuls ('D'). Classement au pourcentage ; à égalité, le plus grand nombre passe devant.
    """
    t = (long.groupby(["team", "div"])
             .agg(league=("league", "first"), season=("season", "first"),
                  total_matches=("result", "size"),
                  win_matches=("result", lambda s: (s == "W").sum()),
                  draw_matches=("result", lambda s: (s == "D").sum()),
                  loss_matches=("result", lambda s: (s == "L").sum()))
             .reset_index())
    t = t[t["total_matches"] >= min_matches].copy()
    if t.empty:
        return pd.DataFrame()
    cle = {"W": "win_matches", "L": "loss_matches", "D": "draw_matches"}[critere]
    t["pct"] = (t[cle] / t["total_matches"] * 100).round(0).astype(int)
    t = t.sort_values(["pct", cle, "total_matches", "team"], ascending=[False, False, False, True])
    t.insert(0, "top", range(1, len(t) + 1))       # rang continu, pas d'ex aequo
    t = t.reset_index(drop=True)
    return t[t["top"] <= top_n] if top_n else t


def tableau_forme(long, n_last=5, critere="W", top_n=50):
    """Forme sur les N derniers matchs : critere 'W' (victoires), 'L' (défaites) ou 'D' (nuls)."""
    last_n = long.sort_values("date", kind="stable").groupby(["team", "div"]).tail(n_last)
    t = (last_n.groupby(["team", "div"])
              .agg(league=("league", "first"), season=("season", "first"),
                   last_matches=("result", "size"),
                   win_matches=("result", lambda s: (s == "W").sum()),
                   draw_matches=("result", lambda s: (s == "D").sum()),
                   loss_matches=("result", lambda s: (s == "L").sum()),
                   form=("result", lambda s: "".join(s)),
                   last_match_date=("date", "max"))
              .reset_index())
    t = t[t["last_matches"] == n_last].copy()
    if t.empty:
        return pd.DataFrame()
    if critere == "D":     # matchs nuls : le plus de nuls, puis la série la plus récente
        t = t.sort_values(["draw_matches", "last_match_date", "team"], ascending=[False, False, True])
    else:
        cle = "win_matches" if critere == "W" else "loss_matches"
        t = t.sort_values([cle, "draw_matches", "last_match_date", "team"],
                          ascending=[False, critere != "W", False, True])
    t.insert(0, "top", range(1, len(t) + 1))       # rang continu, pas d'ex aequo
    t["last_match_date"] = t["last_match_date"].dt.strftime("%d/%m/%Y")
    t = t[["top", "team", "div", "league", "season", "last_matches", "win_matches",
           "draw_matches", "loss_matches", "form", "last_match_date"]].reset_index(drop=True)
    return t[t["top"] <= top_n] if top_n else t


# =========================================================
# 4. MODÈLE DE PRÉDICTION (POISSON)
# =========================================================
PRIOR = 3        # matchs "fictifs" de moyenne ajoutés pour lisser les petits échantillons
MAX_GOALS = 10


def forces_equipes(m_div, prior=PRIOR):
    """
    Forces d'attaque / de défense à domicile et à l'extérieur, relatives à la moyenne
    du championnat. Lissage : chaque équipe démarre avec `prior` matchs à la moyenne.
    """
    avg_h = m_div["fthg"].mean()
    avg_a = m_div["ftag"].mean()
    if not (avg_h > 0 and avg_a > 0):
        return None
    dom = m_div.groupby("home_team").agg(n=("fthg", "size"), gf=("fthg", "sum"), ga=("ftag", "sum"))
    ext = m_div.groupby("away_team").agg(n=("ftag", "size"), gf=("ftag", "sum"), ga=("fthg", "sum"))
    equipes = sorted(set(dom.index) | set(ext.index))
    f = pd.DataFrame(index=equipes)
    dom = dom.reindex(equipes).fillna(0)
    ext = ext.reindex(equipes).fillna(0)
    f["home_att"] = (dom["gf"] + prior * avg_h) / (dom["n"] + prior) / avg_h
    f["home_def"] = (dom["ga"] + prior * avg_a) / (dom["n"] + prior) / avg_a
    f["away_att"] = (ext["gf"] + prior * avg_a) / (ext["n"] + prior) / avg_a
    f["away_def"] = (ext["ga"] + prior * avg_h) / (ext["n"] + prior) / avg_h
    f["matches"] = dom["n"] + ext["n"]
    return {"forces": f, "avg_h": avg_h, "avg_a": avg_a, "n_matches": len(m_div)}


def _poisson_pmf(lmbda, k_max=MAX_GOALS):
    return np.array([math.exp(-lmbda) * lmbda ** k / math.factorial(k) for k in range(k_max + 1)])


def predire(modele, home, away):
    """Probabilités d'un match à partir du modèle d'un championnat."""
    f = modele["forces"]
    if home not in f.index or away not in f.index:
        return None
    lam_h = f.at[home, "home_att"] * f.at[away, "away_def"] * modele["avg_h"]
    lam_a = f.at[away, "away_att"] * f.at[home, "home_def"] * modele["avg_a"]
    mat = np.outer(_poisson_pmf(lam_h), _poisson_pmf(lam_a))     # mat[i, j] = P(home=i, away=j)
    mat = mat / mat.sum()
    i, j = np.indices(mat.shape)
    tot = i + j
    scores = sorted(((mat[a, b], f"{a}-{b}") for a in range(5) for b in range(5)), reverse=True)[:5]
    return {
        "xg_home": lam_h, "xg_away": lam_a,
        "p_home": mat[i > j].sum(), "p_draw": mat[i == j].sum(), "p_away": mat[i < j].sum(),
        "p_btts": mat[(i > 0) & (j > 0)].sum(),
        "p_over15": mat[tot >= 2].sum(), "p_over25": mat[tot >= 3].sum(), "p_over35": mat[tot >= 4].sum(),
        "p_home_scores": mat[i >= 1].sum(), "p_away_scores": mat[:, 1:].sum(),
        "top_scores": scores, "matrix": mat,
    }


def modeles_par_championnat(m):
    return {div: mod for div, g in m.groupby("div")
            if (mod := forces_equipes(g)) is not None}


# =========================================================
# 5. PROCHAINS MATCHS
# =========================================================
def charger_prochains_matchs():
    """Prochains matchs publiés par football-data.co.uk (européens + extra)."""
    frames = []
    try:
        fx = nettoyer(lire_csv(URL_FIXTURES))
        fx = fx[fx["Div"].isin(MAIN_CODES)]
        frames.append(pd.DataFrame({
            "div": fx["Div"], "date": pd.to_datetime(fx["Date"], dayfirst=True, errors="coerce"),
            "time": fx.get("Time", ""), "home_team": fx["HomeTeam"].astype(str).str.strip(),
            "away_team": fx["AwayTeam"].astype(str).str.strip(),
            "odds_h": _premiere_colonne(fx, ["AvgH", "B365H"]),
            "odds_d": _premiere_colonne(fx, ["AvgD", "B365D"]),
            "odds_a": _premiere_colonne(fx, ["AvgA", "B365A"])}))
    except Exception:
        pass
    try:
        fe = nettoyer(lire_csv(URL_FIXTURES_EXTRA)).rename(columns=RENOMMAGE_EXTRA)
        code = fe["Country"].map(PAYS_EXTRA) if "Country" in fe.columns else fe.get("Div")
        frames.append(pd.DataFrame({
            "div": code, "date": pd.to_datetime(fe["Date"], dayfirst=True, errors="coerce"),
            "time": fe.get("Time", ""), "home_team": fe["HomeTeam"].astype(str).str.strip(),
            "away_team": fe["AwayTeam"].astype(str).str.strip(),
            "odds_h": _premiere_colonne(fe, ["AvgH", "AvgCH", "PSH", "B365H"]),
            "odds_d": _premiere_colonne(fe, ["AvgD", "AvgCD", "PSD", "B365D"]),
            "odds_a": _premiere_colonne(fe, ["AvgA", "AvgCA", "PSA", "B365A"])}))
    except Exception:
        pass
    if not frames:
        return pd.DataFrame()
    fx = pd.concat(frames, ignore_index=True).dropna(subset=["div"])
    fx["league"] = fx["div"].map(noms)
    return fx.sort_values(["date", "time"]).reset_index(drop=True)


def _cle_nom(nom):
    """Nom simplifié pour comparer : minuscules, sans accents, ponctuation ni FC / CF / AC…"""
    import unicodedata, re
    n = unicodedata.normalize("NFKD", str(nom)).encode("ascii", "ignore").decode().lower()
    n = re.sub(r"[^a-z0-9 ]", " ", n)
    mots = [m for m in n.split() if m not in {"fc", "cf", "ac", "sc", "afc", "cd", "ca", "club", "de", "the"}]
    return " ".join(mots)


def _trouver_equipe(nom, equipes):
    """Nom exact s'il existe, sinon l'équipe du championnat au nom le plus proche (ou None)."""
    import difflib
    if nom in equipes:
        return nom
    cles = {_cle_nom(e): e for e in equipes}
    c = _cle_nom(nom)
    if c in cles:
        return cles[c]
    proche = difflib.get_close_matches(c, list(cles), n=1, cutoff=0.8)
    return cles[proche[0]] if proche else None


def aligner_equipes(fixtures, modeles):
    """
    Remplace les noms d'équipes des prochains matchs par ceux des résultats quand ils diffèrent
    légèrement (ex. « Paris SG » / « Paris Saint Germain »), pour ne pas perdre de matchs.
    """
    if fixtures.empty:
        return fixtures
    fx = fixtures.copy()
    for i, r in fx.iterrows():
        mod = modeles.get(r["div"])
        if not mod:
            continue
        equipes = mod["forces"].index
        for col in ("home_team", "away_team"):
            trouve = _trouver_equipe(r[col], equipes)
            if trouve:
                fx.at[i, col] = trouve
    return fx


def matchs_sans_prediction(fixtures, modeles):
    """Prochains matchs écartés, avec la raison (championnat non chargé ou équipe inconnue)."""
    lignes = []
    for _, r in aligner_equipes(fixtures, modeles).iterrows():
        mod = modeles.get(r["div"])
        if not mod:
            raison = "Championnat non chargé"
        elif r["home_team"] not in mod["forces"].index or r["away_team"] not in mod["forces"].index:
            raison = "Équipe sans match joué cette saison"
        else:
            continue
        lignes.append({"date": r["date"], "time": r["time"], "league": r["league"] if pd.notna(r["league"]) else r["div"],
                       "match": f"{r['home_team']} - {r['away_team']}", "raison": raison})
    return pd.DataFrame(lignes)


def predire_prochains_matchs(fixtures, modeles):
    fixtures = aligner_equipes(fixtures, modeles)
    lignes = []
    for _, r in fixtures.iterrows():
        mod = modeles.get(r["div"])
        p = predire(mod, r["home_team"], r["away_team"]) if mod else None
        if p is None:
            continue
        lignes.append({
            "date": r["date"], "time": r["time"], "div": r["div"], "league": r["league"],
            "home_team": r["home_team"], "away_team": r["away_team"],
            "xg_home": round(p["xg_home"], 2), "xg_away": round(p["xg_away"], 2),
            "%_home": round(p["p_home"] * 100), "%_draw": round(p["p_draw"] * 100),
            "%_away": round(p["p_away"] * 100), "%_btts": round(p["p_btts"] * 100),
            "%_over_1_5": round(p["p_over15"] * 100), "%_over_2_5": round(p["p_over25"] * 100),
            "%_over_3_5": round(p["p_over35"] * 100), "likely_score": p["top_scores"][0][1],
            "odds_h": r["odds_h"], "odds_d": r["odds_d"], "odds_a": r["odds_a"],
        })
    return pd.DataFrame(lignes)


# =========================================================
# 6. MOYENNES ET MÉDIANES DE BUTS
# =========================================================
def stats_buts_equipes(long, sens="for", min_matches=5):
    """
    Par équipe : buts marqués (sens='for') ou encaissés (sens='against') par match.
    Moyenne et médiane, au total, à domicile et à l'extérieur.
    """
    col = "goals_for" if sens == "for" else "goals_against"
    g = long.groupby(["team", "div"])
    t = g.agg(league=("league", "first"), total_matches=(col, "size"), total_goals=(col, "sum"),
              mean=(col, "mean"), median=(col, "median")).reset_index()
    dom = long[long["venue"] == "H"].groupby(["team", "div"])[col].agg(mean_home="mean", median_home="median")
    ext = long[long["venue"] == "A"].groupby(["team", "div"])[col].agg(mean_away="mean", median_away="median")
    t = t.join(dom, on=["team", "div"]).join(ext, on=["team", "div"])
    t = t[t["total_matches"] >= min_matches].copy()
    for c in ["mean", "mean_home", "mean_away", "median", "median_home", "median_away"]:
        t[c] = t[c].round(2)
    return t.reset_index(drop=True)


def stats_buts_championnats(long, sens="for"):
    """
    Par championnat : buts marqués / encaissés par équipe et par match.
    Au total, marqués = encaissés (chaque but marqué est encaissé par l'adversaire) ;
    la différence apparaît à domicile / à l'extérieur.
    """
    col = "goals_for" if sens == "for" else "goals_against"
    g = long.groupby("div")
    t = g.agg(league=("league", "first"), total_matches=("venue", lambda s: (s == "H").sum()),
              total_goals=(col, "sum"), mean=(col, "mean"), median=(col, "median")).reset_index()
    dom = long[long["venue"] == "H"].groupby("div")[col].agg(mean_home="mean", median_home="median")
    ext = long[long["venue"] == "A"].groupby("div")[col].agg(mean_away="mean", median_away="median")
    t = t.join(dom, on="div").join(ext, on="div")
    for c in ["mean", "mean_home", "mean_away", "median", "median_home", "median_away"]:
        t[c] = t[c].round(2)
    return t.reset_index(drop=True)


# =========================================================
# 7. PROBABILITÉS DÉTAILLÉES ET TICKETS
# =========================================================
PART_1RE_DEFAUT = 0.45   # part des buts marqués en 1re période (moyenne habituelle) si pas de mi-temps


def parts_1re_periode(m):
    """Part des buts marqués en 1re période, par championnat (défaut pour les championnats sans mi-temps)."""
    ht = m.dropna(subset=["first_half_goals"])
    parts = {}
    if not ht.empty and ht["total_goals"].sum() > 0:
        globale = ht["first_half_goals"].sum() / ht["total_goals"].sum()
    else:
        globale = PART_1RE_DEFAUT
    for div in m["div"].unique():
        d = ht[ht["div"] == div]
        parts[div] = (d["first_half_goals"].sum() / d["total_goals"].sum()
                      if len(d) >= 20 and d["total_goals"].sum() > 0 else globale)
    return parts


def probas_periodes(lam_total, part_1re):
    """P(plus de buts en 1re), P(plus en 2e), P(égalité) : buts de chaque période ~ Poisson indépendantes."""
    p1 = _poisson_pmf(lam_total * part_1re)
    p2 = _poisson_pmf(lam_total * (1 - part_1re))
    mat = np.outer(p1, p2)
    mat = mat / mat.sum()
    i, j = np.indices(mat.shape)
    return mat[i > j].sum(), mat[i < j].sum(), mat[i == j].sum()


def predictions_detaillees(fixtures, modeles, parts, min_matches=0):
    """Toutes les probabilités utiles aux tickets, une ligne par prochain match."""
    fixtures = aligner_equipes(fixtures, modeles)
    lignes = []
    for _, r in fixtures.iterrows():
        mod = modeles.get(r["div"])
        p = predire(mod, r["home_team"], r["away_team"]) if mod else None
        if p is None:
            continue
        f = mod["forces"]
        n_min = int(min(f.at[r["home_team"], "matches"], f.at[r["away_team"], "matches"]))
        if n_min < min_matches:
            continue
        p1h, p2h, peq = probas_periodes(p["xg_home"] + p["xg_away"], parts.get(r["div"], PART_1RE_DEFAUT))
        mat = p["matrix"]
        i, j = np.indices(mat.shape)
        p_home_btts = mat[(i > j) & (j >= 1)].sum()      # domicile gagne ET les deux équipes marquent
        p_away_btts = mat[(j > i) & (i >= 1)].sum()      # extérieur gagne ET les deux équipes marquent
        lignes.append({
            "date": r["date"], "time": r["time"], "div": r["div"], "league": r["league"],
            "home_team": r["home_team"], "away_team": r["away_team"],
            "match": f"{r['home_team']} - {r['away_team']}",
            "p_home": p["p_home"], "p_draw": p["p_draw"], "p_away": p["p_away"],
            "p_home_scores": p["p_home_scores"], "p_away_scores": p["p_away_scores"],
            "p_over15": p["p_over15"], "p_over25": p["p_over25"], "p_btts": p["p_btts"],
            "p_1h": p1h, "p_2h": p2h, "p_eq": peq,
            "p_home_btts": p_home_btts, "p_away_btts": p_away_btts,
            "score": p["top_scores"][0][1], "p_score": p["top_scores"][0][0],
            "odds_h": r["odds_h"], "odds_d": r["odds_d"], "odds_a": r["odds_a"],
            "matches_min": n_min,
        })
    return pd.DataFrame(lignes)


def _selection(pred, fn_choix, n):
    """
    Applique fn_choix à chaque match -> (modèle de texte, équipe/score, proba, cote marché)
    puis garde les n meilleurs. Le modèle (« Victoire {e} ») permet la traduction dans l'application.
    """
    if pred.empty:
        return pd.DataFrame()
    rows = []
    for _, r in pred.iterrows():
        modele, e, proba, cote = fn_choix(r)
        rows.append({"date": r["date"], "time": r["time"], "league": r["league"], "match": r["match"],
                     "pick": modele.format(e=e), "pick_modele": modele, "pick_e": e,
                     "proba": proba, "market_odds": cote})
    t = pd.DataFrame(rows).sort_values("proba", ascending=False).head(n).reset_index(drop=True)
    return t


def _victoire(r):
    if r["p_home"] >= r["p_away"]:
        return "Victoire {e}", r["home_team"], r["p_home"], r["odds_h"]
    return "Victoire {e}", r["away_team"], r["p_away"], r["odds_a"]


def _defaite(r):
    # l'équipe la plus susceptible de perdre dans le match
    if r["p_away"] >= r["p_home"]:
        return "Défaite {e}", r["home_team"], r["p_away"], r["odds_a"]
    return "Défaite {e}", r["away_team"], r["p_home"], r["odds_h"]


def _victoire_btts(r):
    # « 12 Yes » : la meilleure équipe du match gagne ET les deux équipes marquent
    m = "Victoire {e} et les deux équipes marquent"
    if r["p_home"] >= r["p_away"]:
        return m, r["home_team"], r["p_home_btts"], np.nan
    return m, r["away_team"], r["p_away_btts"], np.nan


def _marque(r):
    if r["p_home_scores"] >= r["p_away_scores"]:
        return "{e} marque", r["home_team"], r["p_home_scores"], np.nan
    return "{e} marque", r["away_team"], r["p_away_scores"], np.nan


TICKETS = {
    "Victoires": _victoire,
    "Défaites": _defaite,
    "Matchs nuls": lambda r: ("Match nul", "", r["p_draw"], r["odds_d"]),
    "Buts marqués": _marque,
    "BTTS - les deux équipes marquent": lambda r: ("Les deux équipes marquent (Yes)", "", r["p_btts"], np.nan),
    "12 Yes - victoire et les deux équipes marquent": _victoire_btts,
    "Plus de buts en 1re période": lambda r: ("Plus de buts en 1re période", "", r["p_1h"], np.nan),
    "Plus de buts en 2e période": lambda r: ("Plus de buts en 2e période", "", r["p_2h"], np.nan),
    "Scores exacts": lambda r: ("Score exact {e}", r["score"], r["p_score"], np.nan),
    "Over 1.5 buts": lambda r: ("Plus de 1.5 buts", "", r["p_over15"], np.nan),
    "Over 2.5 buts": lambda r: ("Plus de 2.5 buts", "", r["p_over25"], np.nan),
}


# Probabilité minimale par défaut (en %) pour qu'un match entre dans un ticket.
# Adaptée à chaque événement : un nul ou un score exact n'atteint jamais les niveaux d'une victoire nette.
SEUILS_DEFAUT = {
    "Victoires": 60, "Défaites": 60, "Matchs nuls": 30, "Buts marqués": 75,
    "BTTS - les deux équipes marquent": 60, "12 Yes - victoire et les deux équipes marquent": 35,
    "Plus de buts en 1re période": 35, "Plus de buts en 2e période": 50, "Scores exacts": 12,
    "Over 1.5 buts": 75, "Over 2.5 buts": 60,
}


def construire_ticket(pred, type_ticket, n=10, seuil=None):
    """Les n matchs où l'événement est le plus probable, en ne gardant que ceux au-dessus du seuil (en %)."""
    t = _selection(pred, TICKETS[type_ticket], len(pred))
    if seuil is not None and not t.empty:
        t = t[t["proba"] * 100 >= seuil]
    return t.head(n).reset_index(drop=True)


def ticket_combine(pred, n=10, seuils=None):
    """
    Ticket combiné : le meilleur pronostic de chaque type de ticket (un match ne sert qu'une fois),
    complété par les pronostics restants les plus probables. Seuls les pronostics au-dessus
    du seuil de leur type sont retenus.
    """
    if pred.empty:
        return pd.DataFrame()
    seuils = seuils or SEUILS_DEFAUT
    candidats = []
    for nom, fn in TICKETS.items():
        t = _selection(pred, fn, len(pred))
        t = t[t["proba"] * 100 >= seuils.get(nom, 0)]
        t["ticket_type"] = nom
        candidats.append(t)
    cand = pd.concat(candidats, ignore_index=True)
    if cand.empty:
        return pd.DataFrame()
    choisis, matchs_utilises = [], set()
    for nom in TICKETS:                                     # 1) le top de chaque événement
        c = cand[(cand["ticket_type"] == nom) & (~cand["match"].isin(matchs_utilises))]
        if not c.empty and len(choisis) < n:
            choisis.append(c.iloc[0])
            matchs_utilises.add(c.iloc[0]["match"])
    reste = cand[~cand["match"].isin(matchs_utilises)].sort_values("proba", ascending=False)
    for _, r in reste.iterrows():                           # 2) compléter jusqu'à n matchs
        if len(choisis) >= n:
            break
        if r["match"] not in matchs_utilises:
            choisis.append(r)
            matchs_utilises.add(r["match"])
    return pd.DataFrame(choisis).reset_index(drop=True)


# =========================================================
# 8. CLASSEMENT D'UN CHAMPIONNAT
# =========================================================
def classement(long, div, n_forme=5):
    """
    Classement calculé à partir des résultats : 3 pts la victoire, 1 le nul.
    Départage : points, différence de buts, buts marqués, puis ordre alphabétique.
    """
    d = long[long["div"] == div]
    if d.empty:
        return pd.DataFrame()
    t = d.groupby("team").agg(
        J=("result", "size"),
        G=("result", lambda s: (s == "W").sum()),
        N=("result", lambda s: (s == "D").sum()),
        P=("result", lambda s: (s == "L").sum()),
        BP=("goals_for", "sum"),
        BC=("goals_against", "sum"),
    ).reset_index()
    t[["BP", "BC"]] = t[["BP", "BC"]].astype(int)
    t["Diff"] = t["BP"] - t["BC"]
    t["Pts"] = 3 * t["G"] + t["N"]
    forme = (d.sort_values("date", kind="stable").groupby("team")["result"]
              .apply(lambda s: "".join(s.tail(n_forme))))
    t["Forme"] = t["team"].map(forme)
    t = t.sort_values(["Pts", "Diff", "BP", "team"], ascending=[False, False, False, True])
    t.insert(0, "Rang", range(1, len(t) + 1))
    return t.rename(columns={"team": "Équipe"}).reset_index(drop=True)
