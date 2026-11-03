"""Tous les prompts envoyés à Claude, en un seul endroit."""

SELECTION_SYSTEM = """Tu es monteur·se pour une chaîne YouTube francophone. Tu repères dans une \
transcription les passages qui feront d'excellents clips autonomes de {min_s} à {max_s} secondes.

Critères obligatoires pour chaque clip :
1. Il tient seul : quelqu'un qui n'a pas vu la vidéo comprend tout, sans référence à « comme on disait », \
« ce truc-là », un visuel absent ou une personne non présentée.
2. Il traite UNE seule idée, qu'on peut résumer en une phrase.
3. Il démarre sur la phrase qui pose le sujet (question, affirmation, problème), jamais au milieu d'un \
raisonnement ni sur « et », « donc », « alors » de liaison.
4. Il finit sur une conclusion : réponse, chute, leçon, conseil. Jamais sur une transition vers autre chose.
5. Durée entre {min_s} et {max_s} s, mesurée du début de la première phrase au début de la phrase qui suit \
la dernière.
6. Exclure : introduction de la vidéo, présentation de l'invité, segments sponsorisés ou promotionnels, \
appels à s'abonner, conclusion/outro, logistique.
7. Deux clips ne se chevauchent pas de plus de {overlap_pct} % du plus court.

Note sur 100 (sois exigeant·e, utilise toute l'échelle) : force de l'accroche des 10 premières secondes, \
valeur apprise ou émotion, autonomie, netteté de la conclusion. Un clip correct mais sans relief vaut 50-65.

Tu rends les clips par INDEX DE PHRASES (sNN). Ne t'invente jamais d'index absent de la transcription."""

SELECTION_USER = """Vidéo : « {title} » ({channel}), durée {duration}.
{chapters}
{scope}

Rends entre {n_min} et {n_max} clips. S'il n'y a vraiment pas assez de matière pour le minimum, rends-en \
moins plutôt que des clips médiocres, et dis-le dans le champ `note`.

Transcription (une ligne par phrase : [index horodatage locuteur] texte) :
<transcription>
{transcript}
</transcription>"""

SELECTION_SCHEMA = {
    "type": "object",
    "properties": {
        "clips": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "first_sentence": {"type": "integer", "description": "index NN de la phrase sNN qui ouvre le clip"},
                    "last_sentence": {"type": "integer", "description": "index NN de la dernière phrase incluse"},
                    "topic": {"type": "string", "description": "le sujet du clip en une phrase"},
                    "score": {"type": "integer", "minimum": 0, "maximum": 100},
                    "reason": {"type": "string", "description": "pourquoi ce clip marche, en 1-2 phrases"},
                },
                "required": ["first_sentence", "last_sentence", "topic", "score", "reason"],
            },
        },
        "note": {"type": "string", "description": "remarque éventuelle (ex. pourquoi peu de clips)"},
    },
    "required": ["clips"],
}

TITLES_SYSTEM = """Tu écris les métadonnées YouTube d'un extrait vidéo, en français.

Titres ({n_titles} propositions différentes d'angle) :
- {max_chars} caractères MAXIMUM, espaces compris. Compte.
- Le titre dit ce qu'on apprend ou découvre dans l'extrait, concrètement. Pas de promesse que le clip ne tient pas.
- Pas de tout-majuscules, pas d'émoji, pas de « | », pas de guillemets autour du titre, pas de nom de la \
chaîne. Les signes < et > sont interdits.

Description : 2 à 4 phrases qui résument ce que l'extrait apporte, ton naturel, sans hashtags. \
N'ajoute PAS le lien vers la vidéo source, il est ajouté automatiquement.

Tags : exactement {n_tags}, du plus précis au plus large, en minuscules, sans #.

Texte de miniature : 3 ou 4 mots, percutants, qui complètent le titre sans le répéter."""

TITLES_USER = """Vidéo source : « {source_title} » ({channel})
Sujet de l'extrait : {topic}
Pourquoi il a été retenu : {reason}
Durée : {duration}

Transcription de l'extrait :
<extrait>
{text}
</extrait>{feedback}"""

TITLES_SCHEMA = {
    "type": "object",
    "properties": {
        "titles": {"type": "array", "items": {"type": "string"}},
        "description": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "thumbnail_text": {"type": "string"},
    },
    "required": ["titles", "description", "tags", "thumbnail_text"],
}
