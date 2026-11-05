"""
abonnement.py - Abonnements payants par Mobile Money via pawaPay, abonnés enregistrés dans Supabase.

Fonctionnement
--------------
1. L'utilisateur saisit son numéro Mobile Money ; pawaPay devine l'opérateur (predict-provider).
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
    prix_xaf = 656              # 1 € = 655,957 XAF
    duree_jours = 30
    code_admin = "un-code-secret-a-toi"   # facultatif : accès permanent pour toi

Sans section [pawapay] ET [supabase], l'abonnement est désactivé et tout reste gratuit.
"""

import secrets as _secrets
import uuid
from datetime import datetime, timedelta, timezone

import requests
import streamlit as st

API = {"sandbox": "https://api.sandbox.pawapay.io", "production": "https://api.pawapay.io"}
PRIX_DEFAUT = 656
DUREE_DEFAUT = 30
OPERATEURS = {"MTN_MOMO_COG": "MTN Mobile Money", "AIRTEL_COG": "Airtel Money"}
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
        "token": p.get("token", ""),
        "api": API.get(str(p.get("environnement", "sandbox")).lower(), API["sandbox"]),
        "sandbox": str(p.get("environnement", "sandbox")).lower() != "production",
        "sb_url": str(s.get("url", "")).rstrip("/"),
        "sb_cle": s.get("cle", ""),
        "prix": int(a.get("prix_xaf", PRIX_DEFAUT)),
        "duree": int(a.get("duree_jours", DUREE_DEFAUT)),
        "code_admin": str(a.get("code_admin", "")).strip(),
    }


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


def predire_operateur(cfg, numero):
    """Nettoie le numéro et devine l'opérateur. Renvoie (msisdn, provider) ou lève ValueError."""
    code, rep = _pp(cfg, "POST", "/v2/predict-provider", {"phoneNumber": numero})
    if code != 200 or "provider" not in rep:
        raise ValueError("Numéro invalide ou opérateur non reconnu. Vérifie le numéro (ex. 242 06 123 45 67).")
    if rep["provider"] not in OPERATEURS:
        raise ValueError("Pour l'instant, seuls MTN Mobile Money et Airtel Money (Congo-Brazzaville) sont acceptés.")
    return rep["phoneNumber"], rep["provider"]


def demander_paiement(cfg, msisdn, provider, deposit_id):
    """Envoie la demande de paiement. Renvoie (statut, message)."""
    corps = {"depositId": deposit_id, "amount": str(cfg["prix"]), "currency": "XAF",
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
    h = {"apikey": cfg["sb_cle"], "Authorization": f"Bearer {cfg['sb_cle']}",
         "Content-Type": "application/json", "Prefer": "return=representation"}
    r = requests.request(methode, f"{cfg['sb_url']}/rest/v1/{TABLE}", params=params, json=json,
                         headers=h, timeout=20)
    r.raise_for_status()
    return r.json() if r.content else []


def enregistrer_demande(cfg, deposit_id, msisdn, provider):
    _sb(cfg, "POST", json={"deposit_id": deposit_id, "telephone": msisdn, "operateur": provider,
                           "montant": cfg["prix"], "devise": "XAF", "statut": "EN_ATTENTE",
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


def rattraper(cfg, msisdn):
    """Vérifie les paiements restés « en attente » (page fermée trop tôt...)."""
    for ligne in _sb(cfg, "GET", params={"telephone": f"eq.{msisdn}", "statut": "eq.EN_ATTENTE",
                                         "select": "deposit_id"}):
        try:
            finaliser(cfg, ligne["deposit_id"], msisdn)
        except Exception:
            pass


def connexion(cfg, numero, code):
    """Renvoie la date de fin si numéro + code donnent un abonnement actif, sinon None."""
    try:
        msisdn, _ = predire_operateur(cfg, numero)
    except ValueError:
        return None
    rattraper(cfg, msisdn)
    lignes = _sb(cfg, "GET", params={"telephone": f"eq.{msisdn}", "statut": "eq.PAYE",
                                     "code_acces": f"eq.{code.strip()}", "select": "expire_le",
                                     "order": "expire_le.desc", "limit": "1"})
    if not lignes:
        return None
    fin = datetime.fromisoformat(lignes[0]["expire_le"].replace("Z", "+00:00"))
    return (msisdn, fin) if fin > maintenant() else None


def nouveau_deposit_id():
    return str(uuid.uuid4())
