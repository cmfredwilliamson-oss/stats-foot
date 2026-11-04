# ⚽ Stats & Prédictions Foot

Application web (Streamlit) qui reprend les 28 analyses du notebook **STAT_DES_MATCHS** et ajoute des prédictions de matchs.

Données : [football-data.co.uk](https://www.football-data.co.uk). Elles sont rechargées automatiquement toutes les 3 heures, ou à la demande avec le bouton « Actualiser les données ».

## Contenu

| Fichier | Rôle |
|---|---|
| `app.py` | L'interface web (onglets, filtres, graphiques) |
| `stats_core.py` | Le moteur de calcul : chargement, tableaux, forme, modèle de prédiction |
| `requirements.txt` | Les librairies Python nécessaires |

## Le menu

Les onglets en haut de l'écran (avec menus déroulants) reprennent les **28 états du notebook**, avec la même numérotation :

| Section | États |
|---|---|
| Accueil | 1-3. Données chargées (journal + tous les matchs) · Prédictions |
| Buts dans le match | 4-11. BTTS, over 1.5 / 2.5 / 3.5 (par championnat et par équipe) |
| Mi-temps | 15-20. Plus de buts en 2e / en 1re période, périodes égales (championnats et équipes) |
| Buts marqués | 21-26. L'équipe marque au moins 1 / 2 / 3 / 4 buts, moins de 2, ne marque pas |
| Forme | Victoires, défaites et matchs nuls sur la saison, puis sur les 5 derniers matchs |
| Stats | 33-40. Moyennes et médianes de buts marqués et encaissés, par équipe et par championnat (total, domicile, extérieur) |
| Tickets | Combiné, Victoires, Défaites, Buts marqués, BTTS (les 2 équipes marquent), Plus de buts en 1re / 2e période, Scores exacts, Over 1.5, Over 2.5 |
| Buts encaissés | 29. Clean sheet (n'encaissent pas) · 30-32. Encaissent au moins 1 / 2 / 3 buts |

Chaque état affiche les colonnes utiles : **Rang, Équipe, Championnat, Matchs joués, la stat de l'état et son pourcentage**. Les états 12 à 14 montrent en plus victoires, nuls et défaites côte à côte. Chaque tableau s'exporte en CSV. Sur les états par équipe, un filtre « Nombre d'équipes » (20 par défaut) choisit combien d'équipes afficher. Le rang est continu (1, 2, 3…), sans ex aequo : à pourcentage égal, l'équipe avec le plus de matchs passe devant, puis l'ordre alphabétique départage.

Les paramètres (saison, championnats, minimum de matchs) sont dans le bouton « ⚙️ Paramètres », en haut à droite.

Le dossier `.streamlit` (couleurs de l'application) doit rester à côté de `app.py`.

**Tickets** : sélections de 10 matchs par défaut (jusqu'à 30) sur les prochains jours. Pour chaque ticket : pronostic, probabilité, cote juste, cote du marché, probabilité que tout passe et cote juste du ticket. Le ticket combiné reprend le meilleur pronostic de chaque type, puis complète avec les plus probables. Les probabilités de 1re / 2e période utilisent la part des buts marqués en 1re période dans chaque championnat.

**Prédictions** : probabilités 1X2, BTTS, over et score le plus probable pour les prochains matchs, avec les cotes du marché, et un mode « match au choix ».

## Lancer l'application sur ton ordinateur

Dans un terminal ouvert dans le dossier `foot_app` :

```bash
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

L'application s'ouvre dans le navigateur à l'adresse http://localhost:8501.

## Mettre l'application en ligne (gratuit)

1. Crée un dépôt GitHub et mets-y les 3 fichiers (`app.py`, `stats_core.py`, `requirements.txt`).
2. Va sur https://share.streamlit.io et connecte-toi avec GitHub.
3. Clique sur **Create app**, choisis le dépôt, la branche et le fichier `app.py`, puis **Deploy**.
4. Tu obtiens une adresse publique en `https://<nom>.streamlit.app` que tu peux partager.

## Le modèle de prédiction

Modèle de **Poisson**, calculé championnat par championnat :

- Pour chaque équipe : force d'attaque et de défense **à domicile** et **à l'extérieur**, rapportées à la moyenne de buts du championnat.
- En début de saison, chaque équipe démarre avec 3 matchs « fictifs » à la moyenne. Cela évite qu'une équipe avec 2 matchs ait des forces extrêmes (paramètre `PRIOR` dans `stats_core.py`).
- Buts attendus : `xG domicile = attaque_dom(A) × défense_ext(B) × moyenne buts domicile`, et inversement pour l'extérieur.
- Une loi de Poisson donne la probabilité de chaque score (0-0, 1-0, 2-1…). On en déduit 1X2, BTTS, over 1.5 / 2.5 / 3.5 et les scores les plus probables.
- Cote « juste » = 1 / probabilité. Si la cote du marché est nettement plus haute, le modèle juge l'issue sous-cotée.

**Limites** : le modèle ne connaît que les scores. Blessures, suspensions, rotations, transferts, météo et enjeu ne sont pas pris en compte. Les pourcentages sont des estimations, pas des certitudes.

## Remarques sur les données

- Les championnats extra (USA, ARG, BRA, SWE, JPN, NOR) n'ont pas de score à la mi-temps. Ils sont exclus des indicateurs 1re / 2e période.
- Ces championnats se jouent sur une année civile, alors que les européens vont d'août à mai. Comparer les pourcentages reste possible, mais le nombre de matchs joués diffère.
- Mode hors ligne (tests) : définir la variable `FOOT_DATA_DIR` vers un dossier contenant `<saison>/<code>.csv`, `new/<code>.csv`, `fixtures.csv` et `new_league_fixtures.csv`.

## Notification par e-mail à chaque visite

L'application peut t'envoyer un e-mail à chaque nouvelle visite : date et heure (Brazzaville), type d'appareil, navigateur et langue. Un même visiteur ne déclenche qu'un e-mail toutes les 30 minutes, même s'il recharge la page.

1. **Créer un mot de passe d'application Gmail** : sur https://myaccount.google.com, va dans « Sécurité », active la « Validation en deux étapes », puis ouvre « Mots de passe des applications » (https://myaccount.google.com/apppasswords). Crée un mot de passe nommé « Streamlit » et copie le code de 16 lettres.
2. **Le donner à Streamlit Cloud** : sur share.streamlit.io, ouvre ton application, puis « ⋮ » → « Settings » → « Secrets ». Colle ces lignes en remplaçant le code, puis « Save » :

```toml
[email]
expediteur   = "cmfredwilliamson@gmail.com"
mot_de_passe = "abcd efgh ijkl mnop"
destinataire = "cmfredwilliamson@gmail.com"
```

Ne mets jamais ce mot de passe dans un fichier envoyé sur GitHub : seuls les « Secrets » de Streamlit le gardent en sécurité. Sans ces secrets (par exemple quand l'application tourne sur ton ordinateur), aucun e-mail n'est envoyé.
