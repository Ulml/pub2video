# pub2video

Flux agentique : une vidéo YouTube ou un PDF de publication devient un récit écrit + une vidéo muette calée.

Chaque agent reçoit un **contrat**. Un **juge** mesure la conformité. Sous le seuil (95 % par défaut, réglable par agent), l’agent retente puis le pipeline s’arrête.

## Source unique

- Pipeline : `app/ssot/pipeline.yaml`
- Contrats : un YAML par agent dans `app/contracts/`
- Édition : http://127.0.0.1:8765/contracts

1. Entrée (YouTube, PDF, ou démo)
2. Extraire la publication
3. Expliquer sans jargon
4. Découper en chapitres
5. Récit écrit (citations « Nom1, Nom2, année »)
6. Storyboard
7. Vidéo muette calée

## Lancer

```bash
cd pub2video
python3 -m pip install -r requirements.txt
PYTHONPATH=. python3 app/cli.py run --demo
PYTHONPATH=. python3 app/cli.py settings --threshold 0.95
PYTHONPATH=. python3 app/server.py
```

- App : http://127.0.0.1:8765
- Contrats : http://127.0.0.1:8765/contracts

Le mode démo rejoue Koushiappas 2026 (chapitre 1).
