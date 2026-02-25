import re
import unicodedata

# =============================================================================
# VOCABULAIRE CENTRALISÉ
# =============================================================================

VERBS_EMPILER = {
    "met", "mets", "mettre", "mettez", "metter",
    "empile", "empiles", "empiler", "empilez"
}

VERBS_DESEMPILER = {
    "depile", "depiles", "depiler", "depilez",
    "desempile", "desempiles", "desempiler", "desempilez",
    "dempiles", "enleve", "enleves", "enlevez", "enlever"
}

VERBS_DEPOSER = {
    "depose", "deposes", "deposer", "pose", "poses", "poser", "posez"
}

VERBS_PRENDRE = {
    "ramasse", "ramasses", "ramasser", "ramassez",
    "prend", "prends", "prendre", "prenez", "pends",
    "attrape", "attrapes", "attraper", "attrapez"
}

VERBS_LIBERER = {
    "libere", "liberes", "liberer", "liberez",
    "libre", "librer"
}

ALL_TWO_ARG_VERBS = VERBS_EMPILER | VERBS_DESEMPILER
ALL_ONE_ARG_VERBS = VERBS_DEPOSER | VERBS_PRENDRE | VERBS_LIBERER
VERBS_AMBIGUS = {"enleve", "enleves", "enlevez", "enlever"}
ALL_ONE_ARG_VERBS = ALL_ONE_ARG_VERBS | VERBS_AMBIGUS
ALL_VERBS = ALL_TWO_ARG_VERBS | ALL_ONE_ARG_VERBS

DETERMINANTS = {"le", "la", "un", "une", "l"}
ADJECTIFS_BLOC = {"bloc", "block", "blok", "cube", "cub", "boc"}
PREPOSITIONS = {"sur", "de", "du", "dessus", "dessu", "desus", "desu"}
NOMS_BLOCS = {"a", "b", "c", "d", "e", "f", "g"}

# Mots-clés spéciaux (pré-processés avant le parsing normal)
ENTRE_KEYWORDS = {"entre"}
ENTRE_ET_PLACEHOLDER = "§ENTRE_ET§"

# Rôles
ROLE_VERB = "VERB"
ROLE_NAME = "NAME"
ROLE_PREP = "PREP"
ROLE_DET = "DET"
ROLE_ADJ = "ADJ"
ROLE_UNKNOWN = "?"


# =============================================================================
# PREPROCESSING
# =============================================================================

def normalize_text(phrase, keep_commas=False):
    """Supprime accents, ponctuation, tirets, normalise espaces, minuscule.
    Si keep_commas=True, préserve les virgules (pour le split en commandes)."""
    nfkd = unicodedata.normalize('NFKD', phrase)
    sans_accents = ''.join(c for c in nfkd if not unicodedata.combining(c))
    sans_tirets = sans_accents.replace('-', ' ')
    if keep_commas:
        sans_ponctuation = re.sub(r'[^\w\s,]', ' ', sans_tirets)
    else:
        sans_ponctuation = re.sub(r'[^\w\s]', ' ', sans_tirets)
    return re.sub(r'\s+', ' ', sans_ponctuation).strip().lower()


def split_into_commands(texte):
    """Sépare une demande en commandes individuelles (virgule ou 'et')."""
    parties = texte.split(',')
    commandes = []
    for partie in parties:
        sous_parties = partie.split(' et ')
        for sp in sous_parties:
            sp = sp.strip()
            if sp:
                commandes.append(sp)
    return commandes


# =============================================================================
# PRÉ-TRAITEMENT "ENTRE X ET Y"
# =============================================================================

def protect_entre_et(text):
    """
    Protège le 'et' à l'intérieur de 'entre X et Y' pour qu'il ne soit pas
    utilisé comme séparateur de commandes.
    
    'mets c entre a et b et met d sur la table'
    → 'mets c entre a §ENTRE_ET§ b et met d sur la table'
    
    Seul le 'et' immédiatement après 'entre BLOC' est protégé.
    """
    # Pattern: "entre" + bloc + "et" + bloc (les blocs sont des lettres a-g)
    noms_pattern = '|'.join(sorted(NOMS_BLOCS))
    pattern = rf'\bentre\s+({noms_pattern})\s+et\s+({noms_pattern})\b'
    return re.sub(pattern, rf'entre \1 {ENTRE_ET_PLACEHOLDER} \2', text, flags=re.IGNORECASE)


def expand_entre_command(cmd):
    """
    Si une commande contient 'entre X §ENTRE_ET§ Y', l'expanse en deux commandes
    standard que le parseur existant sait traiter.
    
    'mets c entre a §ENTRE_ET§ b'
    → ['mets c sur a', 'mets b sur c']
    
    Sémantique: "mets C entre A et B" signifie que C va sur A, et B va sur C.
    Résultat: pile A-C-B (de bas en haut).
    """
    if ENTRE_ET_PLACEHOLDER not in cmd:
        return [cmd]

    # Restaurer le 'et' pour le regex
    cmd_restored = cmd.replace(ENTRE_ET_PLACEHOLDER, 'et')

    # Trouver le pattern "entre X et Y"
    noms_pattern = '|'.join(sorted(NOMS_BLOCS))
    match = re.search(rf'\bentre\s+({noms_pattern})\s+et\s+({noms_pattern})\b', cmd_restored)
    if not match:
        return [cmd_restored]

    bottom = match.group(1)  # bloc du dessous
    top = match.group(2)     # bloc du dessus

    # Retirer "entre X et Y" de la commande pour trouver le verbe et l'objet
    remaining = cmd_restored[:match.start()] + cmd_restored[match.end():]
    remaining = re.sub(r'\s+', ' ', remaining).strip()

    # Tagger ce qui reste pour trouver verbe + objet
    words = remaining.split()
    if not words:
        return [cmd_restored]

    tagged = tag_sentence(words)
    roles = extract_roles(tagged)

    if roles['verb'] is None or len(roles['names']) != 1:
        # Impossible de décomposer → renvoyer tel quel (sera rejeté par le parseur)
        return [cmd_restored]

    verb = roles['verb']
    obj = roles['names'][0][0]

    # "mets C entre A et B" → C sur A (objet sur le bas), B sur C (haut sur objet)
    return [f"{verb} {obj} sur {bottom}", f"{verb} {top} sur {obj}"]


# =============================================================================
# TAGGING PAR RÔLE
# =============================================================================

def tag_word(word):
    """Attribue un rôle à un mot, indépendamment de sa position."""
    w = word.lower()
    if w in ALL_VERBS:
        return ROLE_VERB
    if w in NOMS_BLOCS:
        return ROLE_NAME
    if w in PREPOSITIONS:
        return ROLE_PREP
    if w in ADJECTIFS_BLOC:
        return ROLE_ADJ
    if w in DETERMINANTS:
        return ROLE_DET
    return ROLE_UNKNOWN


def tag_sentence(words):
    """Retourne une liste de tuples (mot, rôle)."""
    return [(w, tag_word(w)) for w in words]


# =============================================================================
# EXTRACTION DES RÔLES
# =============================================================================

def extract_roles(tagged):
    """
    Extrait verbe, noms, préposition d'une phrase taguée,
    indépendamment de leur position.
    """
    verb = None
    names = []
    prep_index = None
    unknown_words = []

    for i, (word, role) in enumerate(tagged):
        if role == ROLE_VERB and verb is None:
            verb = word
        elif role == ROLE_NAME:
            names.append((word, i))
        elif role == ROLE_PREP and prep_index is None:
            prep_index = i
        elif role == ROLE_UNKNOWN:
            unknown_words.append(word)
        # DET et ADJ sont du bruit syntaxique → ignorés

    return {
        'verb': verb,
        'names': names,
        'prep_index': prep_index,
        'has_prep': prep_index is not None,
        'valid_structure': len(unknown_words) == 0
    }


# =============================================================================
# CATÉGORISATION DES VERBES
# =============================================================================

def get_verb_category_one_arg(verb):
    if verb in VERBS_DEPOSER:
        return 'deposer'
    elif verb in VERBS_PRENDRE:
        return 'prendre'
    elif verb in VERBS_LIBERER or verb in VERBS_AMBIGUS:
        return 'liberer'
    return None


def get_verb_category_two_args(verb):
    if verb in VERBS_EMPILER:
        return 'empiler'
    elif verb in VERBS_DESEMPILER:
        return 'desempiler'
    return None


# =============================================================================
# RÉSOLUTION DES NOMS (qui est l'objet, qui est la destination)
# =============================================================================

def resolve_two_names(names, prep_index):
    """
    Détermine name1 (objet déplacé) et name2 (destination).
    
    Règle: le nom le plus proche APRÈS la préposition = destination (name2).
    L'autre = objet déplacé (name1).
    
    "mets A sur B"   → prep=sur(idx 2), A(idx 1) avant, B(idx 3) après → name1=A, name2=B
    "sur B mets A"   → prep=sur(idx 0), B(idx 1) après, A(idx 3) après mais plus loin → name1=A, name2=B
    "A sur B empile"  → prep=sur(idx 1), A(idx 0) avant, B(idx 2) après → name1=A, name2=B
    """
    if len(names) != 2:
        return None, None

    (word_a, idx_a), (word_b, idx_b) = names

    if prep_index is not None:
        a_after_prep = idx_a > prep_index
        b_after_prep = idx_b > prep_index

        if a_after_prep and not b_after_prep:
            # A après prep → A = destination
            return word_b, word_a
        elif b_after_prep and not a_after_prep:
            # B après prep → B = destination
            return word_a, word_b
        elif a_after_prep and b_after_prep:
            # Les deux après: le plus proche de prep = destination
            if abs(idx_a - prep_index) < abs(idx_b - prep_index):
                return word_b, word_a
            else:
                return word_a, word_b
        else:
            # Les deux avant prep: premier = objet, second = destination
            if idx_a < idx_b:
                return word_a, word_b
            else:
                return word_b, word_a
    else:
        # Pas de préposition: ordre d'apparition
        if idx_a < idx_b:
            return word_a, word_b
        else:
            return word_b, word_a


# =============================================================================
# PARSING PAR RÔLES
# =============================================================================

def parse_one_arg(tagged):
    """
    Parse une commande à 1 argument.
    Accepte verbe + nom dans n'importe quel ordre.
    
    OK: "prends A", "A prends", "le bloc A prends", "prends le bloc A"
    """
    roles = extract_roles(tagged)

    if roles['verb'] is None or len(roles['names']) != 1:
        return None, False
    if not roles['valid_structure']:
        return None, False

    verb = roles['verb']
    name = roles['names'][0][0].upper()
    category = get_verb_category_one_arg(verb)

    if category is None:
        return None, False

    if category == 'deposer':
        return f"ONTABLE('{name}')", True
    elif category == 'prendre':
        return f"HOLDING('{name}')", True
    elif category == 'liberer':
        return f"CLEAR('{name}')", True

    return None, False


def parse_two_args(tagged):
    """
    Parse une commande à 2 arguments.
    Accepte verbe + préposition + 2 noms dans n'importe quel ordre.
    
    OK: "mets A sur B", "sur B mets A", "empile sur B le bloc A",
        "le bloc A mets sur le cube B", "A sur B empile"
    """
    roles = extract_roles(tagged)

    if roles['verb'] is None or len(roles['names']) != 2 or not roles['has_prep']:
        return None, False
    if not roles['valid_structure']:
        return None, False

    verb = roles['verb']
    category = get_verb_category_two_args(verb)
    if category is None:
        return None, False

    name1, name2 = resolve_two_names(roles['names'], roles['prep_index'])
    if name1 is None:
        return None, False

    n1 = name1.upper()
    n2 = name2.upper()

    if category == 'empiler':
        return f"ON('{n1}','{n2}')", True
    elif category == 'desempiler':
        return f"CLEAR('{n2}')", True

    return None, False


# =============================================================================
# ROUTAGE AUTOMATIQUE
# =============================================================================

def parse_command(sentence):
    """
    Parse une commande en détectant automatiquement 1 ou 2 arguments.
    La décision se fait par le contenu (nombre de noms + préposition),
    pas par la structure positionnelle.
    """
    words = sentence.split()
    if not words:
        return None, False

    tagged = tag_sentence(words)
    roles = extract_roles(tagged)

    if len(roles['names']) == 2 and roles['has_prep']:
        return parse_two_args(tagged)
    elif len(roles['names']) == 1:
        return parse_one_arg(tagged)
    else:
        return None, False


# =============================================================================
# FONCTION PRINCIPALE (API externe inchangée)
# =============================================================================

def preprocess_sur_la_table(text):
    """
    Transforme 'VERB X sur la table' en 'depose X' pour que le parseur
    standard puisse l'interpréter comme ONTABLE(X).
    
    'met D sur la table' → 'depose D'
    """
    return re.sub(
        r'(\w+)\s+([a-g])\s+sur\s+la\s+table',
        r'depose \2',
        text, flags=re.IGNORECASE
    )


def ask_for_goal(phrase):
    """
    Transforme une phrase en langage naturel en une liste de buts STRIPS.
    
    Pipeline:
    1. Normaliser le texte (en préservant les virgules)
    2. Pré-traiter 'sur la table' → 'depose X'
    3. Protéger 'entre X et Y'
    4. Séparer en commandes individuelles
    5. Expander les commandes 'entre'
    6. Parser chaque commande avec le parseur par rôles
    
    Retourne: (but_string, succès_bool, message_erreur)
    """
    # 1. Normaliser en préservant les virgules
    phrase_norm = normalize_text(str(phrase), keep_commas=True)

    # 2. Pré-traiter 'sur la table'
    phrase_norm = preprocess_sur_la_table(phrase_norm)

    # 3. Protéger "entre X et Y"
    phrase_protected = protect_entre_et(phrase_norm)

    # 4. Séparer en commandes
    commandes_brutes = split_into_commands(phrase_protected)

    buts = []
    all_valid = True

    for cmd in commandes_brutes:
        cmd = cmd.strip()
        if not cmd:
            continue

        # 4. Expander les commandes "entre" en commandes standard
        expanded = expand_entre_command(cmd)

        for sub_cmd in expanded:
            # Nettoyer "au" isolé
            sub_cmd = re.sub(r'\bau\b', '', sub_cmd).strip()
            sub_cmd = re.sub(r'\s+', ' ', sub_cmd)

            if not sub_cmd:
                continue

            # 5. Parser
            goal, valid = parse_command(sub_cmd)

            if valid and goal is not None:
                buts.append(str(goal))
            else:
                all_valid = False

    if all_valid and buts:
        result = "[" + ", ".join(buts) + ", ]"
        return result, True, ""
    else:
        return None, False, f"La commande <<{phrase}>> ne respecte pas la syntaxe"