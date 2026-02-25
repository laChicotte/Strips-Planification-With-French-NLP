# Strips-Planification-With-French-NLP

## Description

Ce projet implémente un planificateur **STRIPS** (Stanford Research Institute Problem Solver) avec un système de traitement du **langage naturel français**. Il permet de planifier des actions pour manipuler des blocs selon des instructions données en français, avec une interface graphique interactive.

## Fonctionnalités

- **Planification STRIPS** : Algorithme de planification basé sur les actions et les états du monde
- **Traitement du langage naturel français** : Reconnaissance et parsing des commandes en français
- **Interface graphique Tkinter** : Visualisation interactive des blocs et animation des mouvements
- **Reconnaissance de verbes français** : Support de multiples variantes de verbes (empiler, dépiler, prendre, déposer, libérer, etc.)
- **Animation des actions** : Visualisation des mouvements des blocs et du bras robotique

## Architecture du Projet

```
├── main.py                  # Interface graphique (Tkinter)
├── strips.py               # Implémentation de l'algorithme STRIPS
├── langageNaturel.py       # Traitement du langage naturel français
├── initial.tx              # Configuration initiale
├── img/                    # Images des blocs
└── README.md              # Cette documentation
```

### Modules Principaux

**main.py** : 
- Interface graphique avec Tkinter
- Classes `Cube` et `RobotHand` pour la visualisation
- Gestion des événements et animations

**strips.py** :
- Prédicats : `ON`, `ONTABLE`, `CLEAR`, `HOLDING`, `ARMDEMPTY`
- Opérations : empiler, dépiler, prendre, déposer
- Algorithme de planification pour atteindre les objectifs

**langageNaturel.py** :
- Vocabulaire centralisé des verbes français
- Parser pour convertir le langage naturel en actions STRIPS
- Gestion des variantes et conjugaisons

## Dépendances

```
tkinter              # Interface graphique (inclus avec Python)
Pillow              # Traitement des images
```

## Installation

1. Cloner le projet
2. Installer les dépendances :
   ```bash
   pip install Pillow
   ```

## Utilisation

Lancer le programme :
```bash
python main.py
```

### Commandes Suportées

Le système reconnaît des commandes en français comme :
- "Empile A sur B" / "Mets A sur B"
- "Dépile A" / "Enlève A"
- "Prends A" / "Ramasse A"
- "Dépose A" / "Pose A"
- "Libère A"

## Exemples

Entrée : "Empile le bloc A sur le bloc B"
Sortie : Planification et animation de la séquence d'actions pour empiler A sur B

## Auteur

Projet de planification AI avec langage naturel français