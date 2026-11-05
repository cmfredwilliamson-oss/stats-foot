"""
abonnement.py - Abonnements payants par Mobile Money via pawaPay, abonnés enregistrés dans Supabase.

Fonctionnement
--------------
1. L'utilisateur choisit son pays et saisit son numéro Mobile Money. La liste des pays et
   opérateurs vient de pawaPay (GET /v2/active-conf) ; pawaPay devine l'opérateur (predict-provider).
2. L'application crée un dépôt (POST /v2/deposits) : le client reçoit une demande de paiement
   sur son téléphone et la valide avec son code PIN.
3. Streamlit ne peut pas recevoir les « callbacks » de pawaPay : l'application interroge donc
   le statut du dépôt (GET /v2/deposits/{depositId}) jusqu'au résultat final.
4. Paiement COMPLETED -> l'abonnement est prolongé de DUREE_JOURS jours et un code d'accès
   à 6 chiffres est remis au client. Il se reconnecte ensuite avec son numéro + ce code.

Configuration (Streamlit Cloud > ⋮ > Settings > Secrets), à côté de la section [email] :

    [pawapay]
    token = "eyJ..."            # jeton d'API pawaPay (tableau de bord pawaPay > API tokens)
    environnement = "sandbox"   # "sandbox" pour les tests, "production" pour les vrais paiements

    [supabase]
    url = "https://xxxx.supabase.co"
    cle = "eyJ..."              # clé « service_role » (Project Settings > API) - ne jamais la publier

    [abonnement]
    duree_jours = 30
    # facultatif : changer le prix d'une monnaie (sinon environ 1 € par monnaie, voir PRIX_DEFAUT)
    # [abonnement.prix]
    # XAF = 656
    # NGN = 1800
    code_admin = "un-code-secret-a-toi"   # facultatif : accès permanent pour toi

Sans section [pawapay] ET [supabase], l'abonnement est désactivé et tout reste gratuit.
"""

import secrets as _secrets
import uuid
from datetime import datetime, timedelta, timezone

import requests
import streamlit as st

API = {"sandbox": "https://api.sandbox.pawapay.io", "production": "https://api.pawapay.io"}
DUREE_DEFAUT = 30
# Prix d'un mois, environ 1 €, par monnaie (arrondi). Modifiable dans les Secrets : [abonnement.prix]
PRIX_DEFAUT = {
    "XAF": 656, "XOF": 656, "CDF": 3000, "USD": 1.2, "ETB": 170, "GHS": 13, "KES": 150,
    "LSL": 20, "MWK": 2000, "MZN": 75, "NGN": 1800, "RWF": 1700, "SLE": 27, "TZS": 3000,
    "UGX": 4300, "ZMW": 30, "ZAR": 20, "GNF": 10000, "LRD": 230, "GMD": 80,
}
PAYS_DEFAUT = "COG"
TABLE = "abonnements"


# =========================================================
# CONFIGURATION
# =========================================================
def _section(nom):
    try:
        return dict(st.secrets[nom]) if nom in st.secrets else {}
    except Exception:
        return {}


def config():
    p, s, a = _section("pawapay"), _section("supabase"), _section("abonnement")
    return {
        "actif": bool(p.get("token") and s.get("url") and s.get("cle")),
        "token": str(p.get("token", "")).strip(),
        "api": API.get(str(p.get("environnement", "sandbox")).lower(), API["sandbox"]),
        "sandbox": str(p.get("environnement", "sandbox")).lower() != "production",
        "sb_url": str(s.get("url", "")).strip().rstrip("/").removesuffix("/rest/v1"),
        "sb_cle": str(s.get("cle", "")).strip(),
        "prix": _prix_config(a),
        "duree": int(a.get("duree_jours", DUREE_DEFAUT)),
        "code_admin": str(a.get("code_admin", "")).strip(),
    }


def _prix_config(a):
    prix = dict(PRIX_DEFAUT)
    try:
        prix.update({str(k).upper(): float(v) for k, v in dict(a.get("prix", {})).items()})
    except Exception:
        pass
    if "prix_xaf" in a:                     # ancienne configuration
        prix["XAF"] = float(a["prix_xaf"])
    return prix


def maintenant():
    return datetime.now(timezone.utc)


# =========================================================
# PAWAPAY
# =========================================================
def _pp(cfg, methode, chemin, json=None):
    r = requests.request(methode, cfg["api"] + chemin, json=json, timeout=30,
                         headers={"Authorization": f"Bearer {cfg['token']}", "Content-Type": "application/json"})
    try:
        return r.status_code, r.json()
    except ValueError:
        return r.status_code, {}


def _nombre(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


@st.cache_data(ttl=3600, show_spinner=False)
def _active_conf(api, token):
    r = requests.request("GET", api + "/v2/active-conf", params={"operationType": "DEPOSIT"}, timeout=30,
                     headers={"Authorization": f"Bearer {token}"})
    if r.status_code != 200:
        raise RuntimeError(f"pawaPay active-conf {r.status_code} : {r.text[:200]}")
    return r.json()


def pays_disponibles(cfg):
    """
    Pays et opérateurs ouverts aux dépôts pour ce compte pawaPay.
    Renvoie {code_pays: {"nom", "prefixe", "operateurs": [{"provider", "nom", "devise", "min", "max", "decimales"}]}}
    """
    conf = _active_conf(cfg["api"], cfg["token"])
    pays = {}
    for c in conf.get("countries", []):
        nom = c.get("displayName")
        nom = (nom.get("fr") or nom.get("en")) if isinstance(nom, dict) else (nom or c.get("country"))
        ops, vus = [], set()
        for p in c.get("providers", []):
            for cur in p.get("currencies", []):
                types = cur.get("operationTypes") or {}
                if isinstance(types, list):        # certains exemples de la doc donnent une liste
                    types = {t.get("operationType"): t for t in types if isinstance(t, dict)}
                dep = types.get("DEPOSIT")
                if not dep or dep.get("status", "OPERATIONAL") == "CLOSED":
                    continue
                if p["provider"] in vus:           # RDC : même opérateur en CDF et USD -> 1re monnaie
                    continue
                vus.add(p["provider"])
                ops.append({
                    "provider": p["provider"],
                    "nom": p.get("displayName") or p.get("nameDisplayedToCustomer") or p["provider"],
                    "devise": cur.get("currency"),
                    "min": _nombre(dep.get("minAmount", dep.get("minTransactionLimit"))),
                    "max": _nombre(dep.get("maxAmount", dep.get("maxTransactionLimit"))),
                    "decimales": dep.get("decimalsInAmount", "NONE") == "TWO_PLACES",
                })
        if ops:
            pays[c["country"]] = {"nom": nom, "prefixe": str(c.get("prefix", "")), "operateurs": ops}
    return dict(sorted(pays.items(), key=lambda kv: kv[1]["nom"]))


def montant(cfg, op):
    """Montant à payer (texte, format pawaPay) pour un opérateur."""
    m = float(cfg["prix"].get(op["devise"], 0)) or (op["min"] or 1)
    if op["min"] is not None:
        m = max(m, op["min"])
    if op["max"] is not None:
        m = min(m, op["max"])
    return f"{m:.2f}" if op["decimales"] else str(int(round(m)))


def format_montant(texte, devise):
    v = float(texte)
    return (f"{v:,.2f}" if v != int(v) else f"{int(v):,}").replace(",", " ") + f" {devise}"


def normaliser_numero(cfg, code_pays, prefixe, numero):
    """Renvoie (msisdn, provider deviné) pour un numéro du pays choisi, ou lève ValueError."""
    chiffres = "".join(ch for ch in str(numero) if ch.isdigit())
    if len(chiffres) < 6:
        raise ValueError("Numéro trop court. Saisis ton numéro Mobile Money complet.")
    if prefixe and chiffres.startswith(prefixe) and len(chiffres) > len(prefixe) + 6:
        essais = [chiffres]
    else:                                   # numéro local : on ajoute l'indicatif (avec puis sans le 0 initial)
        essais = [prefixe + chiffres]
        if chiffres.startswith("0"):
            essais.append(prefixe + chiffres.lstrip("0"))
    for n in essais:
        code, rep = _pp(cfg, "POST", "/v2/predict-provider", {"phoneNumber": n})
        if code == 200 and rep.get("provider") and rep.get("country") == code_pays:
            return rep["phoneNumber"], rep["provider"]
    raise ValueError("Numéro non reconnu pour ce pays. Vérifie le pays choisi et le numéro.")


def demander_paiement(cfg, msisdn, provider, deposit_id, somme, devise):
    """Envoie la demande de paiement. Renvoie (statut, message)."""
    corps = {"depositId": deposit_id, "amount": somme, "currency": devise,
             "payer": {"type": "MMO", "accountDetails": {"phoneNumber": msisdn, "provider": provider}}}
    code, rep = _pp(cfg, "POST", "/v2/deposits", corps)
    statut = rep.get("status")
    if statut in ("ACCEPTED", "DUPLICATE_IGNORED"):
        return "ACCEPTED", None
    if statut == "REJECTED":
        raison = (rep.get("failureReason") or {}).get("failureMessage", "paiement refusé")
        return "REJECTED", raison
    # erreur 500 / réponse inconnue : selon pawaPay, il ne faut PAS conclure à l'échec -> on vérifiera le statut
    return "UNKNOWN", None


def statut_paiement(cfg, deposit_id):
    """Statut final ou intermédiaire : COMPLETED, FAILED, NOT_FOUND, ACCEPTED, PROCESSING, IN_RECONCILIATION."""
    code, rep = _pp(cfg, "GET", f"/v2/deposits/{deposit_id}")
    if rep.get("status") == "NOT_FOUND":
        return "NOT_FOUND", None
    data = rep.get("data") or {}
    raison = (data.get("failureReason") or {}).get("failureCode")
    return data.get("status", "UNKNOWN"), raison


# =========================================================
# SUPABASE (API REST)
# =========================================================
def _sb(cfg, methode, params=None, json=None):
    cle = cfg["sb_cle"]
    h = {"apikey": cle, "Content-Type": "application/json", "Prefer": "return=representation"}
    if cle.startswith("eyJ"):                    # ancienne clé service_role (JWT) ; les nouvelles clés sb_secret_ passent seulement par apikey
        h["Authorization"] = f"Bearer {cle}"
    r = requests.request(methode, f"{cfg['sb_url']}/rest/v1/{TABLE}", params=params, json=json,
                         headers=h, timeout=20)
    if r.status_code >= 400:
        raise RuntimeError(f"Supabase {r.status_code} : {r.text[:300]}")
    return r.json() if r.content else []


def enregistrer_demande(cfg, deposit_id, msisdn, provider, somme, devise, pays):
    _sb(cfg, "POST", json={"deposit_id": deposit_id, "telephone": msisdn, "operateur": provider,
                           "montant": float(somme), "devise": devise, "pays": pays, "statut": "EN_ATTENTE",
                           "cree_le": maintenant().isoformat()})


def _maj(cfg, deposit_id, valeurs):
    return _sb(cfg, "PATCH", params={"deposit_id": f"eq.{deposit_id}"}, json=valeurs)


def fin_abonnement(cfg, msisdn):
    """Date de fin de l'abonnement actif le plus long, ou None."""
    lignes = _sb(cfg, "GET", params={"telephone": f"eq.{msisdn}", "statut": "eq.PAYE",
                                     "select": "expire_le", "order": "expire_le.desc", "limit": "1"})
    if not lignes or not lignes[0].get("expire_le"):
        return None
    fin = datetime.fromisoformat(lignes[0]["expire_le"].replace("Z", "+00:00"))
    return fin if fin > maintenant() else None


def code_actuel(cfg, msisdn):
    lignes = _sb(cfg, "GET", params={"telephone": f"eq.{msisdn}", "statut": "eq.PAYE",
                                     "select": "code_acces", "order": "expire_le.desc", "limit": "1"})
    return lignes[0]["code_acces"] if lignes else None


def finaliser(cfg, deposit_id, msisdn):
    """
    Interroge pawaPay et met à jour la base. Renvoie (etat, info) :
    ("PAYE", (fin, code)) · ("ECHEC", raison) · ("EN_ATTENTE", None).
    """
    statut, raison = statut_paiement(cfg, deposit_id)
    if statut == "COMPLETED":
        lignes = _sb(cfg, "GET", params={"deposit_id": f"eq.{deposit_id}", "select": "statut,expire_le,code_acces"})
        if lignes and lignes[0]["statut"] == "PAYE":            # déjà traité (double clic, rechargement)
            fin = datetime.fromisoformat(lignes[0]["expire_le"].replace("Z", "+00:00"))
            return "PAYE", (fin, lignes[0]["code_acces"])
        depart = fin_abonnement(cfg, msisdn) or maintenant()   # un réabonnement prolonge l'abonnement en cours
        fin = depart + timedelta(days=cfg["duree"])
        code = code_actuel(cfg, msisdn) or f"{_secrets.randbelow(10**6):06d}"   # même code pour un réabonné
        _maj(cfg, deposit_id, {"statut": "PAYE", "paye_le": maintenant().isoformat(),
                               "expire_le": fin.isoformat(), "code_acces": code})
        return "PAYE", (fin, code)
    if statut in ("FAILED", "NOT_FOUND"):
        _maj(cfg, deposit_id, {"statut": "ECHEC", "motif": raison or statut})
        return "ECHEC", raison or statut
    return "EN_ATTENTE", None


def _filtre_numero(numero):
    """Filtre Supabase sur les 8 derniers chiffres : marche avec ou sans indicatif / 0 initial."""
    chiffres = "".join(ch for ch in str(numero) if ch.isdigit()).lstrip("0")
    return f"like.*{chiffres[-8:]}" if len(chiffres) >= 8 else None


def rattraper(cfg, filtre):
    """Vérifie les paiements restés « en attente » (page fermée trop tôt...)."""
    for ligne in _sb(cfg, "GET", params={"telephone": filtre, "statut": "eq.EN_ATTENTE",
                                         "select": "deposit_id,telephone"}):
        try:
            finaliser(cfg, ligne["deposit_id"], ligne["telephone"])
        except Exception:
            pass


def connexion(cfg, numero, code):
    """Renvoie (msisdn, date de fin) si numéro + code donnent un abonnement actif, sinon None."""
    filtre, code = _filtre_numero(numero), str(code).strip()
    if not filtre or not (code.isdigit() and len(code) == 6):
        return None
    rattraper(cfg, filtre)
    lignes = _sb(cfg, "GET", params={"telephone": filtre, "statut": "eq.PAYE",
                                     "code_acces": f"eq.{code}", "select": "telephone,expire_le",
                                     "order": "expire_le.desc", "limit": "1"})
    if not lignes:
        return None
    fin = datetime.fromisoformat(lignes[0]["expire_le"].replace("Z", "+00:00"))
    return (lignes[0]["telephone"], fin) if fin > maintenant() else None


def nouveau_deposit_id():
    return str(uuid.uuid4())
