"""
Pré-processeur de texte mathématique pour Piper TTS.
Convertit les symboles mathématiques, unités, notations géométriques et heures
en texte français fluide et parfaitement lisible à voix haute pour les enfants.
"""

import re


def preprocess_math_text(text: str) -> str:
    """
    Convertit les symboles, unités et expressions mathématiques en mots français.
    Exemples :
      - "3 × 4 = ?" -> "3 multiplié par 4 égale ?"
      - "Le segment [AB]" -> "Le segment A B"
      - "12h30" -> "12 heures 30"
      - "1,5 x 20" -> "1,5 multiplié par 20"
      - "1/2 de 7" -> "un demi de 7"
      - "20€" -> "20 euros"
    """

    # 1. Fractions courantes
    fractions = {
        r'\b1/2\b': 'un demi',
        r'\b1/3\b': 'un tiers',
        r'\b1/4\b': 'un quart',
        r'\b1/5\b': 'un cinquième',
        r'\b2/3\b': 'deux tiers',
        r'\b3/4\b': 'trois quarts',
    }
    for pattern, replacement in fractions.items():
        text = re.sub(pattern, replacement, text)

    # 2. Heures (ex: 12h30, 15h00, 1h15, 6h)
    def replace_hours(match):
        h = match.group(1).lstrip('0') or '0'
        m = match.group(2)
        h_word = "heure" if h == "1" else "heures"
        if m:
            m_clean = m.lstrip('0')
            if not m_clean:
                return f"{h} {h_word}"
            return f"{h} {h_word} {m_clean}"
        return f"{h} {h_word}"
    text = re.sub(r'\b(\d+)[hH](\d{2})?\b', replace_hours, text)

    # 3. Unités de mesure avec chiffres devant (ex: 5 cm, 1 kg, 2 m², 3 cm³)
    units = {
        'cm²': ('centimètre carré', 'centimètres carrés'),
        'cm³': ('centimètre cube', 'centimètres cubes'),
        'cm': ('centimètre', 'centimètres'),
        'dm': ('décimètre', 'décimètres'),
        'dam': ('décamètre', 'décamètres'),
        'hm': ('hectomètre', 'hectomètres'),
        'km': ('kilomètre', 'kilomètres'),
        'kg': ('kilogramme', 'kilogrammes'),
        'g': ('gramme', 'grammes'),
        'mg': ('milligramme', 'milligrammes'),
        'mL': ('millilitre', 'millilitres'),
        'cL': ('centilitre', 'centilitres'),
        'dL': ('décilitre', 'décilitres'),
        'hL': ('hectolitre', 'hectolitres'),
        'L': ('litre', 'litres'),
        'l': ('litre', 'litres'),
        'min': ('minute', 'minutes'),
        'sec': ('seconde', 'secondes'),
        'm²': ('mètre carré', 'mètres carrés'),
        'm³': ('mètre cube', 'mètres cubes'),
        'm': ('mètre', 'mètres'),
    }
    sorted_units = sorted(units.keys(), key=len, reverse=True)
    unit_pattern = r'\b(\d+(?:,\d+)?)\s*(' + '|'.join(re.escape(u) for u in sorted_units) + r')(?!\w)'
    
    def replace_units(match):
        val = match.group(1).replace(',', '.')
        unit = match.group(2)
        try:
            num = float(val)
            is_singular = num <= 1
        except ValueError:
            is_singular = False
        replacement = units[unit][0] if is_singular else units[unit][1]
        return f"{match.group(1)} {replacement}"
    text = re.sub(unit_pattern, replace_units, text)

    # 4. Euros et monnaies (ex: 20€, 1,50€, 12,50 €)
    def replace_euros(match):
        val = match.group(1).replace(',', '.')
        try:
            num = float(val)
            word = "euro" if num <= 1 else "euros"
        except ValueError:
            word = "euros"
        return f"{match.group(1)} {word}"
    text = re.sub(r'\b(\d+(?:,\d+)?)\s*€', replace_euros, text)
    text = re.sub(r'\bcts\b', 'centimes', text)

    # 5. Degrés d'angle ou de température (ex: 90°)
    def replace_degrees(match):
        val = match.group(1)
        word = "degré" if val == "1" else "degrés"
        return f"{val} {word}"
    text = re.sub(r'(\d+)\s*°', replace_degrees, text)

    # 6. Notations géométriques (ex: [AB] -> segment A B, (AB) -> droite A B)
    def format_points(points):
        return " ".join(list(points))
    text = re.sub(r'\[([A-Z]{2,})\]', lambda m: f" segment {format_points(m.group(1))} ", text)
    text = re.sub(r'\(([A-Z]{2,})\)', lambda m: f" droite {format_points(m.group(1))} ", text)
    text = re.sub(r'\[([A-Z]{2,})\)', lambda m: f" demi-droite {format_points(m.group(1))} ", text)
    
    # Éliminer les redondances comme "le segment segment A B" -> "le segment A B"
    text = re.sub(r'\b(segment|droite|demi-droite)\s+\1\b', r'\1', text, flags=re.IGNORECASE)

    # 6b. Unités de volume ou de surface autonomes (ex: "(m³)")
    standalone_units = {
        'cm²': 'centimètres carrés',
        'cm³': 'centimètres cubes',
        'm²': 'mètres carrés',
        'm³': 'mètres cubes',
        'km²': 'kilomètres carrés',
    }
    for u, replacement in standalone_units.items():
        text = re.sub(r'(?<!\w)' + re.escape(u) + r'(?!\w)', f' {replacement} ', text)

    # 7. Multiplication par la lettre x/X entre deux nombres (ex: 1,5 x 20, 3 x 4)
    text = re.sub(r'\b(\d+(?:,\d+)?)\s*[xX]\s*(\d+(?:,\d+)?)\b', r'\1 multiplié par \2', text)

    # 8. Division avec / entre chiffres ou lettres (ex: 36 / 5, D / 2)
    text = re.sub(r'\b(\w+)\s*/\s*(\w+)\b', r'\1 divisé par \2', text)

    # 9. Remplacements de symboles mathématiques classiques
    replacements = [
        # Symboles multi-caractères
        ('≠', ' différent de '),
        ('≤', ' inférieur ou égal à '),
        ('≥', ' supérieur ou égal à '),

        # Opérations et comparaisons
        ('×', ' multiplié par '),
        ('*', ' multiplié par '),
        ('÷', ' divisé par '),
        ('+', ' plus '),
        ('−', ' moins '),       # tiret mathématique (U+2212)
        ('<', ' inférieur à '),
        ('>', ' supérieur à '),
        ('=', ' égale '),

        # Puissances et racines
        ('²', ' au carré '),
        ('³', ' au cube '),
        ('√', ' racine carrée de '),
        ('%', ' pourcent '),
    ]

    for symbol, replacement in replacements:
        text = text.replace(symbol, replacement)

    # Traiter le tiret normal (-) uniquement s'il est entouré de chiffres (ex: 10-5)
    # pour éviter de couper des mots composés comme "peut-être".
    text = re.sub(r'(\d)\s*-\s*(\d)', r'\1 moins \2', text)

    # Nettoyer les espaces multiples
    text = re.sub(r'\s+', ' ', text).strip()

    return text
