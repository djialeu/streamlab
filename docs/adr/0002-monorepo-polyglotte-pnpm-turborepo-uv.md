# ADR 0002 — Monorepo polyglotte : pnpm + Turborepo pour orchestrer, uv pour Python

- **Statut** : accepté
- **Date** : 2026-11-27
- **TD concerné** : TD1

## Contexte

Tout le code (interface, services, bibliothèques partagées, infrastructure, documentation) vit dans **un seul dépôt**, pour que les groupes partagent les contrats d'événements sans publier de paquets.

Le cahier des charges imposait pnpm + Turborepo. Les services backend sont finalement écrits en **Python** ([ADR 0005](0005-fastapi-pour-les-services.md)), alors que l'interface sera en **Next.js** (TD2). Il faut donc gérer deux écosystèmes, avec des commandes communes simples (`pnpm dev`, `pnpm test`).

## Options envisagées

### Option A — Deux outillages séparés, sans orchestrateur commun
- Inconvénients : deux jeux de commandes ; la CI et les étudiants doivent savoir quoi lancer où.

### Option B — Tout orchestrer avec un outil Python (Make, nox, poethepoet)
- Inconvénients : Make est absent sous Windows ; Next.js reste dans l'écosystème JS ; on perd le cache de turbo.

### Option C — pnpm + Turborepo comme orchestrateur, uv pour Python (retenue)
- pnpm + Turborepo gèrent les projets JS **et** lancent les tâches de chaque projet, quel que soit son langage : chaque projet Python a un petit `package.json` dont les scripts appellent `uv run …`.
- **uv** gère le workspace Python : un `pyproject.toml` racine, des membres `packages/*` et `services/*`, **un seul `uv.lock`** et un seul `.venv`.

## Décision

**Option C.**

- `pnpm-workspace.yaml` : `apps/*`, `packages/*`, `services/*`.
- `turbo.json` : tâches `dev` (persistante, sans cache), `typecheck`, `lint`, `test` (avec dépendances `^`).
- Les dépendances `"@streamlab/contracts": "workspace:*"` des `package.json` Python ne servent **qu'à turbo** : il connaît ainsi le graphe et relance les tests des dépendants quand `contracts` change.
- `pyproject.toml` racine : workspace uv, outils de dev partagés (pytest, mypy, ruff, httpx2) et leur configuration.
- Commandes : `pnpm setup` (`uv sync --all-packages`), `pnpm dev`, `pnpm typecheck`, `pnpm lint`, `pnpm test`.
- Versions : pnpm figé par `packageManager` (installé par corepack), Node ≥ 24 (`.nvmrc`), Python ≥ 3.12.

## Conséquences

- **Positives** : une seule façon de travailler pour tout le dépôt ; cache turbo ; un seul lockfile par écosystème, donc des versions identiques chez tous ; uv est très rapide et réutilise son cache (économie de données).
- **Négatives** : deux outils à installer (pnpm via corepack, uv) ; un `package.json` « adaptateur » dans chaque projet Python, qui peut surprendre.
- **Pièges Windows rencontrés** : `corepack enable` échoue en EPERM si Node est dans `Program Files` (solution : `--install-directory` vers un dossier utilisateur) ; la sortie console n'est pas en UTF-8 par défaut (les services forcent l'UTF-8).
