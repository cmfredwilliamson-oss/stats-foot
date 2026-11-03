"""
notifications.py - Envoie un e-mail à chaque nouvelle visite de l'application.

Fonctionne avec un compte Gmail et un « mot de passe d'application ».
Les identifiants ne sont JAMAIS écrits dans le code : ils sont lus dans les secrets Streamlit
(Streamlit Cloud > Manage app > Settings > Secrets), au format :

    [email]
    expediteur   = "cmfredwilliamson@gmail.com"
    mot_de_passe = "abcd efgh ijkl mnop"
    destinataire = "cmfredwilliamson@gmail.com"

Sans ces secrets (par exemple quand l'application tourne sur ton ordinateur), rien n'est envoyé.
"""

import hashlib
import smtplib
import threading
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

import streamlit as st

HEURE_BRAZZAVILLE = timezone(timedelta(hours=1))
DELAI_MEME_VISITEUR = timedelta(minutes=30)   # pas de 2e e-mail pour le même visiteur avant 30 min


@st.cache_resource
def _dernieres_visites():
    """Mémoire partagée entre toutes les sessions : empreinte du visiteur -> heure du dernier e-mail."""
    return {}


def _config_email():
    try:
        cfg = st.secrets["email"]
        return {"expediteur": cfg["expediteur"], "mot_de_passe": cfg["mot_de_passe"],
                "destinataire": cfg.get("destinataire", cfg["expediteur"])}
    except Exception:
        return None


def _appareil(user_agent):
    ua = (user_agent or "").lower()
    if any(m in ua for m in ("iphone", "android", "mobile")):
        appareil = "📱 Téléphone"
    elif any(t in ua for t in ("ipad", "tablet")):
        appareil = "📱 Tablette"
    else:
        appareil = "💻 Ordinateur"
    for nav in ("Edg", "OPR", "Chrome", "Firefox", "Safari"):
        if nav.lower() in ua:
            return f"{appareil} · {'Edge' if nav == 'Edg' else 'Opera' if nav == 'OPR' else nav}"
    return appareil


def _envoyer(cfg, sujet, corps):
    try:
        msg = EmailMessage()
        msg["Subject"] = sujet
        msg["From"] = cfg["expediteur"]
        msg["To"] = cfg["destinataire"]
        msg.set_content(corps)
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as smtp:
            smtp.login(cfg["expediteur"], cfg["mot_de_passe"].replace(" ", ""))
            smtp.send_message(msg)
    except Exception as e:           # un e-mail raté ne doit jamais bloquer l'application
        print(f"[notification] envoi impossible : {e}")


def notifier_visite(nom_app="Stats & Prédictions Foot"):
    """À appeler une fois en haut de app.py : un e-mail par nouvelle visite (session)."""
    if st.session_state.get("_visite_notifiee"):
        return
    st.session_state["_visite_notifiee"] = True
    cfg = _config_email()
    if cfg is None:
        return
    try:
        headers = st.context.headers
        user_agent = headers.get("User-Agent", "")
        langue = headers.get("Accept-Language", "").split(",")[0] or "inconnue"
        ip = headers.get("X-Forwarded-For", "").split(",")[0].strip()
    except Exception:
        user_agent, langue, ip = "", "inconnue", ""

    # anti-doublon : un rechargement de page ne renvoie pas d'e-mail pendant 30 minutes
    # (l'adresse IP sert uniquement à reconnaître le visiteur ; elle n'est ni stockée en clair ni envoyée)
    empreinte = hashlib.sha256(f"{ip}|{user_agent}|{langue}".encode()).hexdigest()
    visites = _dernieres_visites()
    maintenant_utc = datetime.now(timezone.utc)
    derniere = visites.get(empreinte)
    if derniere and maintenant_utc - derniere < DELAI_MEME_VISITEUR:
        return
    visites[empreinte] = maintenant_utc
    maintenant = datetime.now(HEURE_BRAZZAVILLE).strftime("%d/%m/%Y à %H:%M")
    sujet = f"👀 Nouvelle visite sur {nom_app}"
    corps = (f"Quelqu'un vient d'ouvrir ton application « {nom_app} ».\n\n"
             f"Date : {maintenant} (heure de Brazzaville)\n"
             f"Appareil : {_appareil(user_agent)}\n"
             f"Langue du navigateur : {langue}\n\n"
             f"— Notification automatique de ton application Streamlit")
    # envoi en arrière-plan : la page s'affiche sans attendre l'e-mail
    threading.Thread(target=_envoyer, args=(cfg, sujet, corps), daemon=True).start()
