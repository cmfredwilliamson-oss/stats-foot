"""
notifications.py - Envoie un e-mail à chaque nouvelle visite de l'application.

Fonctionne avec un compte Gmail et un « mot de passe d'application ».
Les identifiants ne sont JAMAIS écrits dans le code : ils sont lus dans les secrets Streamlit
(Streamlit Cloud > ⋮ > Settings > Secrets), au format :

    [email]
    expediteur   = "cmfredwilliamson@gmail.com"
    mot_de_passe = "abcd efgh ijkl mnop"
    destinataire = "cmfredwilliamson@gmail.com"

Sans ces secrets (par exemple quand l'application tourne sur ton ordinateur), rien n'est envoyé.

DIAGNOSTIC : ouvrir l'application avec  ?test_email=1  à la fin du lien
(ex. https://ton-app.streamlit.app/?test_email=1) : un e-mail de test part tout de suite
et le résultat (succès ou cause exacte de l'échec) s'affiche en haut de la page.
"""

import hashlib
import smtplib
import ssl
import threading
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

import streamlit as st

HEURE_BRAZZAVILLE = timezone(timedelta(hours=1))
DELAI_MEME_VISITEUR = timedelta(minutes=30)   # pas de 2e e-mail pour le même visiteur avant 30 min


@st.cache_resource
def _dernieres_visites():
    """Mémoire partagée entre toutes les sessions : empreinte du visiteur -> heure du dernier e-mail envoyé."""
    return {}


def _config_email():
    """Lit les secrets. Renvoie (config, None) ou (None, message d'erreur)."""
    try:
        secrets = st.secrets
        if "email" not in secrets:
            return None, ("Secrets absents : la section [email] n'existe pas dans "
                          "Settings > Secrets de Streamlit Cloud.")
        cfg = secrets["email"]
        manquants = [k for k in ("expediteur", "mot_de_passe") if not str(cfg.get(k, "")).strip()]
        if manquants:
            return None, f"Secrets incomplets : il manque {', '.join(manquants)} dans la section [email]."
        return {"expediteur": str(cfg["expediteur"]).strip(),
                "mot_de_passe": str(cfg["mot_de_passe"]).replace(" ", "").strip(),
                "destinataire": str(cfg.get("destinataire", cfg["expediteur"])).strip()}, None
    except Exception as e:
        if "NotFound" in type(e).__name__ or isinstance(e, FileNotFoundError):
            return None, ("Aucun secret configuré : ajoute la section [email] dans Settings > Secrets "
                          "de ton application sur share.streamlit.io (les secrets n'existent pas en local).")
        return None, f"Secrets illisibles ({type(e).__name__}) : vérifie le format (guillemets, crochets)."


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
    """Envoie l'e-mail (port 465, puis 587 en secours). Renvoie (True, None) ou (False, explication)."""
    msg = EmailMessage()
    msg["Subject"] = sujet
    msg["From"] = cfg["expediteur"]
    msg["To"] = cfg["destinataire"]
    msg.set_content(corps)
    erreurs = []
    for port in (465, 587):
        try:
            if port == 465:
                smtp = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20, context=ssl.create_default_context())
            else:
                smtp = smtplib.SMTP("smtp.gmail.com", 587, timeout=20)
                smtp.starttls(context=ssl.create_default_context())
            with smtp:
                smtp.login(cfg["expediteur"], cfg["mot_de_passe"])
                smtp.send_message(msg)
            print(f"[notification] e-mail envoyé à {cfg['destinataire']} (port {port})")
            return True, None
        except smtplib.SMTPAuthenticationError:
            return False, ("Gmail a refusé la connexion (identifiants). Vérifie que : 1) la validation en deux "
                           "étapes est activée sur le compte Google ; 2) mot_de_passe est bien un MOT DE PASSE "
                           "D'APPLICATION de 16 lettres (pas ton mot de passe Gmail) ; 3) expediteur est "
                           "exactement l'adresse Gmail qui a créé ce mot de passe.")
        except Exception as e:
            erreurs.append(f"port {port} : {type(e).__name__} {e}")
    detail = " | ".join(erreurs)
    print(f"[notification] envoi impossible : {detail}")
    return False, f"Connexion au serveur Gmail impossible ({detail})."


def _infos_visiteur():
    try:
        headers = st.context.headers
        user_agent = headers.get("User-Agent", "") or ""
        langue = (headers.get("Accept-Language", "") or "").split(",")[0] or "inconnue"
        ip = (headers.get("X-Forwarded-For", "") or "").split(",")[0].strip()
    except Exception:
        user_agent, langue, ip = "", "inconnue", ""
    return user_agent, langue, ip


def _message(nom_app, user_agent, langue, test=False):
    maintenant = datetime.now(HEURE_BRAZZAVILLE).strftime("%d/%m/%Y à %H:%M")
    sujet = (f"✅ Test de notification - {nom_app}" if test else f"👀 Nouvelle visite sur {nom_app}")
    corps = ((f"Ceci est un e-mail de TEST : les notifications de « {nom_app} » fonctionnent.\n\n" if test else
              f"Quelqu'un vient d'ouvrir ton application « {nom_app} ».\n\n")
             + f"Date : {maintenant} (heure de Brazzaville)\n"
             + f"Appareil : {_appareil(user_agent)}\n"
             + f"Langue du navigateur : {langue}\n\n"
             + "— Notification automatique de ton application Streamlit")
    return sujet, corps


def _envoi_visite(cfg, sujet, corps, empreinte):
    ok, _ = _envoyer(cfg, sujet, corps)
    if ok:                                   # on ne mémorise la visite que si l'e-mail est vraiment parti
        _dernieres_visites()[empreinte] = datetime.now(timezone.utc)


def notifier_visite(nom_app="Stats & Prédictions Foot"):
    """À appeler une fois en haut de app.py : un e-mail par nouvelle visite (session)."""
    # ---- mode diagnostic : ?test_email=1 ----
    if st.query_params.get("test_email") == "1":
        if not st.session_state.get("_test_email_fait"):
            st.session_state["_test_email_fait"] = True
            cfg, err = _config_email()
            if cfg is None:
                st.error(f"📧 Test e-mail : ÉCHEC. {err}")
            else:
                ua, langue, _ = _infos_visiteur()
                sujet, corps = _message(nom_app, ua, langue, test=True)
                with st.spinner("Envoi de l'e-mail de test…"):
                    ok, err = _envoyer(cfg, sujet, corps)
                if ok:
                    st.success(f"📧 Test e-mail : RÉUSSI. Un e-mail a été envoyé à {cfg['destinataire']} "
                               "(regarde aussi « Spam », « Promotions » et « Tous les messages »).")
                else:
                    st.error(f"📧 Test e-mail : ÉCHEC. {err}")
        return

    # ---- notification normale ----
    if st.session_state.get("_visite_notifiee"):
        return
    st.session_state["_visite_notifiee"] = True
    cfg, _ = _config_email()
    if cfg is None:
        return
    user_agent, langue, ip = _infos_visiteur()
    # anti-doublon : un rechargement de page ne renvoie pas d'e-mail pendant 30 minutes
    # (l'adresse IP sert uniquement à reconnaître le visiteur ; elle n'est ni stockée en clair ni envoyée)
    empreinte = hashlib.sha256(f"{ip}|{user_agent}|{langue}".encode()).hexdigest()
    derniere = _dernieres_visites().get(empreinte)
    if derniere and datetime.now(timezone.utc) - derniere < DELAI_MEME_VISITEUR:
        return
    sujet, corps = _message(nom_app, user_agent, langue)
    # envoi en arrière-plan : la page s'affiche sans attendre l'e-mail
    threading.Thread(target=_envoi_visite, args=(cfg, sujet, corps, empreinte), daemon=True).start()
