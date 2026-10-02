"""Supprime les phrases redondantes sans perdre leurs détails factuels."""
import re
import unicodedata

STOP = set('le la les de des du un une et ou a au aux en dans sur pour avec par qui que se sa son ses ce ces cette est sont ont il elle ils elles l d n'.split())
GENERIC_CAPITALS = STOP | set('selon apres avant depuis alors toutefois mais lorsque ainsi tandis ces cet cela une plus moins'.split())


def normalized(text):
    text = ''.join(c for c in unicodedata.normalize('NFD', text or '') if unicodedata.category(c) != 'Mn').lower()
    text = text.replace('’', "'")
    # Les variantes ne servent qu'à comparer : le texte affiché reste intact.
    text = re.sub(r"\b(?:l[' ]+)?union europeenne\b|\bue\b", 'unioneuropeenne', text)
    text = re.sub(r"\bn'envisage(?:nt)? pas de\b", 'refus', text)
    text = re.sub(r'\b(?:rejette|rejettent|rejetant|refuse|refusent|refusant)\b', 'refus', text)
    text = re.sub(r'\bexportations\b', 'exportation', text)
    text = re.sub(r'\bquotas\b', 'quota', text)
    text = re.sub(r'\b(?:augmente|augmentent|augmentation|hausses)\b', 'hausse', text)
    text = re.sub(r'\b(?:baisse|baissent|baisses|diminution)\b', 'baisse', text)
    text = re.sub(r'\btravailler\b', 'travail', text)
    text = re.sub(r'\b([a-z]{4,})s\b', lambda m: m[0] if m[0].endswith(('us','as','is','ss')) else m[1], text)
    return text


def tokens(text):
    return {w for w in re.findall(r'[a-z0-9]+', normalized(text)) if len(w) > 2 and w not in STOP}


def protected(text):
    """Chiffres, noms propres et qualifications à ne jamais perdre."""
    numbers = set(re.findall(r'(?<!\w)\d+(?:[.,]\d+)?', text))
    names = set()
    for name in re.findall(r'\b[A-ZÀ-Ý][A-Za-zÀ-ÿ-]+\b', text):
        if normalized(name) in {"union", "europeenne"} and "unioneuropeenne" in normalized(text):
            names.add("unioneuropeenne")
            continue
        words = tokens(name)
        names.update(w for w in words if w not in GENERIC_CAPITALS)
    qualifiers = set(re.findall(r'\b(?:pourrait|pourraient|probable|probablement|possible|propose|proposent|proposition|propositions|demande|demandent|confirme|confirment|annule|annulent|annonce|annoncent|suspecte|suspectes|accuse|accuses|condamne|condamnes)\b', normalized(text)))
    qualifiers.update(re.findall(r'\b(?:janvier|fevrier|mars|avril|mai|juin|juillet|aout|septembre|octobre|novembre|decembre|lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche|temporairement|provisoirement|definitivement)\b', normalized(text)))
    # « Rejette la proposition » et « n'envisage pas de » sont tous deux
    # un refus : le mot proposition ne doit pas rendre ce cas incomparable.
    if 'refus' in tokens(text):
        qualifiers -= {'proposition', 'propositions', 'demande', 'demandent'}
    return numbers, names, qualifiers


def covered_by(short, long):
    """Une phrase est redondante uniquement si la suivante conserve ses faits."""
    sw, lw = tokens(short), tokens(long)
    if len(sw) < 3 or len(long) < len(short):
        return False
    sn, sp, sq = protected(short)
    ln, _, lq = protected(long)
    if not sn <= ln or not sp <= lw or not sq <= lq:
        return False
    # Ne pas fusionner une décision, son démenti ou une évolution inverse.
    neg = r"\b(?:pas|jamais|aucun|aucune|sans|refus)\b"
    if bool(re.search(neg, normalized(short))) != bool(re.search(neg, normalized(long))):
        return False
    # Une proximité élevée ne suffit pas si le titre ajoute un fait absent
    # du contenu (ex. mois de l'élection ou thème d'une plainte).
    reporting = {'proposition', 'demande', 'declare', 'rapport', 'rapporte', 'affirme', 'dit', 'indique', 'precise', 'raison'}
    if (sw - lw) - reporting:
        return False
    overlap = len(sw & lw)
    return overlap / len(sw) >= .82 or overlap / max(1, len(sw | lw)) >= .68


def dedupe_sentences(text):
    # Protéger les abréviations et les domaines, même ceux que le flux
    # a mal espacés : America. Gov et Fokus. Mk ne finissent pas une phrase.
    safe = re.sub(r'(?<=\w)\.\s+(?=(?:com|org|net|gov|mk)\b)', lambda m: m[0].replace('.', '\ue000'), text or '', flags=re.I)
    safe = re.sub(r'\b(?:M|Mme|Dr|Pr)\.(?=\s+[A-ZÀ-Ý])', lambda m: m[0].replace('.', '\ue000'), safe)
    parts = [p.strip().replace('\ue000', '.') for p in re.split(r'(?<=[.!?])\s+', safe) if p.strip()]
    out = []
    for part in parts:
        exact = normalized(part).strip(' .!?')
        if any(normalized(prev).strip(' .!?') == exact for prev in out):
            continue
        if any(covered_by(part, prev) for prev in out):
            continue
        # Le titre court est remplacé par la phrase détaillée, pas l'inverse.
        redundant = [i for i, prev in enumerate(out) if covered_by(prev, part)]
        if redundant:
            first = redundant[0]
            out = [prev for i, prev in enumerate(out) if i not in redundant]
            out.insert(first, part)
        else:
            out.append(part)
    return ' '.join(out)
