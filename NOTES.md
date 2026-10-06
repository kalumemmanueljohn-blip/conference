# NOTES OFFICIELLES DU PROJET
## Bantondo's Génération ASBL — Plateforme de réservation

---

## ⚠️ ÉCARTS PAR RAPPORT AU CAHIER DES CHARGES INITIAL

### 1. Conférence désormais PAYANTE

**Cahier des charges initial (section 2)** :
> « La conférence est gratuite, mais les participants doivent obligatoirement
> effectuer une réservation afin de disposer d'une place. »

**Décision officielle du propriétaire (mise à jour)** :
- La conférence est **payante**.
- Prix unitaire : **5.70 USD par place**.
- Devise unique : **USD**.
- **Aucune exception** (pas de gratuité étudiant, VIP, membre ASBL).
- Maximum **5 places** par réservation.

**Date de la décision** : À compléter
**Décideur** : propriétaire du projet (Bantondo's Génération ASBL)

---

## 📌 DÉCISIONS TECHNIQUES VERROUILLÉES

| Élément | Décision |
|---|---|
| Devise | **USD uniquement** |
| Prix unitaire | **5.70 USD / place** |
| Places max / réservation | **5** |
| Unicité réservation | 1 active / user / conférence |
| Format PDF | **A5** |
| Moteur PDF | **WeasyPrint** |
| Langue | **Bilingue FR / EN** |
| Email | **Gmail SMTP** |
| Déploiement | **VPS AWS + Gunicorn + Nginx + PostgreSQL** |
| Logo | `static/images/logo.png` (ajout manuel propriétaire) |
| Numéro WhatsApp | `.env` uniquement |
| Notifications | Email uniquement |
| Export CSV | Oui (v1) |
| SASPAY | Documentation + compte disponibles |
| Tests | pytest-django, couverture flux critiques |

---

## 🚫 RÈGLES ABSOLUES (rappel du cahier des charges)

- Aucun **emoji** dans l'interface, les emails, les PDF.
- Aucune **information officielle inventée** → utiliser « À compléter ».
- Aucune **clé API, secret ou token** exposé dans le code ou les logs.
- Le **logo** n'est jamais inventé par l'IA.
- **SASPAY** : jamais d'endpoint ou paramètre inventé → documentation officielle uniquement.
- **WhatsApp** : confirmation uniquement après **validation manuelle admin**.
- **SASPAY** : confirmation uniquement après **vérification serveur réelle**.
- **Aucune confiance** aux données du navigateur.

---

## 🎨 IDENTITÉ VISUELLE

| Rôle | Code |
|---|---|
| Noir principal | `#000000` |
| Noir secondaire | `#111111` |
| Jaune principal | `#FFD000` |
| Jaune secondaire | `#FFC400` |
| Blanc | `#FFFFFF` |
| Gris clair | `#F5F5F5` |

---

## 🔒 VARIABLES D'ENVIRONNEMENT À COMPLÉTER

- `SECRET_KEY` — généré automatiquement
- `SASPAY_*` — depuis tableau de bord SASPAY
- `WHATSAPP_PAYMENT_NUMBER` — numéro officiel
- `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` — compte Gmail + mot de passe d'application
- `DATABASE_URL` — chaîne PostgreSQL AWS en production
- `ALLOWED_HOSTS` / `CSRF_TRUSTED_ORIGINS` — domaine de production