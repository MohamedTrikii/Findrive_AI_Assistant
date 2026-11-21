# Politique de sécurité

## Versions prises en charge

| Version | Prise en charge |
|---|---|
| 1.1.x | ✅ |
| < 1.1 | ❌ |

## Signaler une vulnérabilité

Merci de **ne pas ouvrir d'issue publique** pour une faille de sécurité.
Utilisez le [signalement privé de GitHub](https://github.com/MohamedTrikii/Findrive_AI_Assistant/security/advisories/new) en décrivant le problème, les étapes pour le reproduire et son impact potentiel.

Un premier retour est donné sous 7 jours.

## Périmètre

L'application fonctionne hors ligne, sans clé d'API ni donnée personnelle : les annonces sont fictives. Les points les plus sensibles sont l'injection HTML dans l'interface (tout contenu dynamique est échappé) et le chargement de fichiers JSON.
