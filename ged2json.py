#!/usr/bin/env python3
"""
ged2json.py — Convertisseur GEDCOM vers JSON pour le site de genealogie
=========================================================================
Usage:
    python ged2json.py chemin/vers/fichier.ged [-o data/individuals.json]

Produit un fichier JSON contenant tous les individus dedoublonnes avec :
  - Nom, prenom, sexe
  - Naissance (date, lieu, coordonnees GPS estimees)
  - Deces (date, lieu)
  - Metier(s)
  - Conjoint(s) avec date/lieu de mariage
  - Lignee et generation (calcul automatique depuis les enfants racines)
  - Couleur de branche

Le JSON est pret a etre charge par le site genealogy via fetch().
"""

import re
import json
import sys
import os
import argparse
from collections import defaultdict

# ─────────────────────────────────────────────
#  COORDONNEES GPS DES LIEUX CONNUS
#  Ajoute tes lieux ici au fur et a mesure
# ─────────────────────────────────────────────
GEOCACHE = {
    # Pays-Bas
    "utrecht": (52.0913, 5.1232),
    "ginneken": (51.5686, 4.7920),
    "breda": (51.5719, 4.7683),
    "roosendaal": (51.5308, 4.4651),
    "roosendaal-nispen": (51.5308, 4.4651),
    "nieuwpoort": (51.9414, 4.8622),
    # Pays basque
    "ahaxe-alciette-bascassan": (43.1446, -1.1610),
    "ahaxe": (43.1446, -1.1610),
    "saint-jean-pied-de-port": (43.1634, -1.2357),
    # Lorraine / Vosges
    "villacourt": (48.4571, 6.3486),
    "charmes": (48.3720, 6.2926),
    "saint-germain": (48.4313, 6.3412),
    "virecourt": (48.4600, 6.3700),
    "gest": (48.4400, 6.3500),
    "longlaville": (49.5339, 5.8008),
    "mont-saint-martin": (49.5465, 5.7870),
    # Dordogne
    "saint-innocence": (44.7250, 0.4100),
    "ribagnac": (44.7500, 0.4300),
    "pas de molle": (44.7032, 0.3792),
    "la roche-chalais": (45.1528, 0.0043),
    "eymet": (44.6686, 0.3960),
    # Touraine
    "sainte-maure-de-touraine": (47.1090, 0.6196),
    "sorigny": (47.2300, 0.6900),
    "villeperdue": (47.2100, 0.7100),
    "saint-epain": (47.1500, 0.5400),
    "sainte-catherine-de-fierbois": (47.1300, 0.6500),
    # Paris et region
    "paris": (48.8566, 2.3522),
    "paris (18e)": (48.8923, 2.3498),
    "paris (11e)": (48.8592, 2.3805),
    "paris (17e)": (48.8835, 2.3219),
    "paris, 17eme": (48.8835, 2.3219),
    "paris, 17e": (48.8835, 2.3219),
    "montreuil": (48.8618, 2.4460),
    "clamart": (48.8013, 2.2665),
    "clichy-sous-bois": (48.9110, 2.5466),
    "poissy": (48.9296, 2.0484),
    "pontoise": (49.0514, 2.1008),
    "cergy": (49.0365, 2.0639),
    # Haute-Saone / Bourgogne
    "lure": (47.6837, 6.4958),
    "lure(70)": (47.6837, 6.4958),
    "dijon": (47.3220, 5.0415),
    "auxonne": (47.1927, 5.3870),
    # Auvergne
    "saint-saturnin": (45.6611, 3.0718),
    "saint-remy": (46.7618, 4.8327),
    # Sarthe / Maine
    "le mans": (48.0007, 0.2028),
    # Charente
    "vindelle": (45.6700, 0.1100),
    "genouille": (45.9700, -0.0600),
    "corn": (44.8600, 1.8300),
    # Loire-Atlantique
    "saint-nazaire": (47.2743, -2.2114),
    "saint nazaire": (47.2743, -2.2114),
    # Belgique
    "montignies-sur-sambre": (50.4021, 4.4762),
    # Suisse
    "aarau": (47.3894, 8.0527),
    # Gironde
    "talence": (44.8027, -0.5870),
    # Bretagne
    "broons": (48.3200, -2.2600),
    "evran": (48.3600, -1.9700),
    "sille-le-guillaume": (48.1833, -0.1333),
    # Orleans / Loiret
    "orleans": (47.9036, 1.9091),
    "sury-aux-bois": (47.9500, 2.3500),
    # Montpellier
    "montpellier": (43.6108, 3.8767),
    # Draguignan
    "draguignan": (43.5371, 6.4646),
    # Deux-Sevres
    "couture-d'argenson": (45.9928, -0.0878),
    "couture-d\u2019argenson": (45.9928, -0.0878),
    # Lieux avec encodage variable
    "paris (vieme)": (48.8499, 2.3323),
    "paris (vie)": (48.8499, 2.3323),
    "paris (6e)": (48.8499, 2.3323),
    "paris (12e)": (48.8416, 2.3874),
    "niederbronn-les-bains": (48.9519, 7.6436),
    "pas de molle - dordogne": (44.7032, 0.3792),
    "maille": (47.0400, 0.5800),
    "maill\u00e9": (47.0400, 0.5800),
    "saint-\u00e9pain": (47.1500, 0.5400),
    "calais": (50.9513, 1.8587),
    "br\u00e9da": (51.5719, 4.7683),
    "orl\u00e9ans": (47.9036, 1.9091),
    "saint-r\u00e9my": (46.7618, 4.8327),
    "auxonne": (47.1927, 5.3870),
    "auxonne (c\u00f4te d'or)": (47.1927, 5.3870),
    # Ciboure
    "ciboure": (43.3850, -1.6700),
    # Saint-Andre-Lez-Lille
    "saint-andre-lez-lille": (50.6600, 3.0400),
    # Alsace (branche Vonthron)
    "alsace": (48.5000, 7.5000),
    "strasbourg": (48.5734, 7.7521),
    "colmar": (48.0794, 7.3585),
}


def normalize_place(place):
    """Normalise un nom de lieu pour la recherche GPS."""
    if not place:
        return ""
    # Prend la premiere partie (avant la virgule = commune)
    parts = place.split(",")
    p = parts[0].strip().lower()
    # Enleve les numeros de departement entre parentheses
    p = re.sub(r'\s*\(\d+\)\s*', '', p)
    # Enleve les numeros postaux
    p = re.sub(r'\b\d{5}\b', '', p)
    # Enleve "rue ...", "37 rue ..."
    p = re.sub(r'\d*\s*rue\s+.*', '', p, flags=re.IGNORECASE)
    p = p.strip().rstrip(',').strip()
    return p


def geocode(place):
    """Cherche les coordonnees GPS d'un lieu dans le cache."""
    if not place:
        return None, None
    norm = normalize_place(place)
    if norm in GEOCACHE:
        return GEOCACHE[norm]
    # Essaye aussi le lieu complet en minuscules
    full = place.strip().lower()
    if full in GEOCACHE:
        return GEOCACHE[full]
    # Essaye chaque partie separee par virgule
    for part in place.split(","):
        p = part.strip().lower()
        p = re.sub(r'\s*\(\d+\)\s*', '', p).strip()
        if p in GEOCACHE:
            return GEOCACHE[p]
    return None, None


def parse_year(date_str):
    """Extrait l'annee d'une chaine de date GEDCOM."""
    if not date_str:
        return None
    # Enleve les prefixes GEDCOM
    date_str = re.sub(r'@#D\w+@\s*', '', date_str)
    date_str = re.sub(r'^(ABT|BEF|AFT|EST|CAL|FROM|TO|BET)\s+', '', date_str, flags=re.IGNORECASE)
    m = re.search(r'\b(\d{4})\b', date_str)
    return int(m.group(1)) if m else None


def format_date_fr(date_str):
    """Formate une date GEDCOM en francais."""
    if not date_str:
        return ""
    MONTHS = {
        'JAN': 'janvier', 'FEB': 'fevrier', 'MAR': 'mars', 'APR': 'avril',
        'MAY': 'mai', 'JUN': 'juin', 'JUL': 'juillet', 'AUG': 'aout',
        'SEP': 'septembre', 'OCT': 'octobre', 'NOV': 'novembre', 'DEC': 'decembre'
    }
    date_str = re.sub(r'@#D\w+@\s*', '', date_str)
    prefix = ""
    m_pref = re.match(r'^(ABT|BEF|AFT|EST|CAL)\s+', date_str, re.IGNORECASE)
    if m_pref:
        prefixes = {'ABT': 'vers', 'BEF': 'avant', 'AFT': 'apres', 'EST': 'vers', 'CAL': 'vers'}
        prefix = prefixes.get(m_pref.group(1).upper(), '') + ' '
        date_str = date_str[m_pref.end():]
    # Format: "DD MON YYYY" ou "MON YYYY" ou "YYYY"
    m = re.match(r'^(\d{1,2})\s+(\w{3})\s+(\d{4})$', date_str.strip())
    if m:
        day, mon, year = m.groups()
        return f"{prefix}{int(day)} {MONTHS.get(mon.upper(), mon)} {year}"
    m = re.match(r'^(\w{3})\s+(\d{4})$', date_str.strip())
    if m:
        mon, year = m.groups()
        return f"{prefix}{MONTHS.get(mon.upper(), mon)} {year}"
    m = re.match(r'^(\d{4})$', date_str.strip())
    if m:
        return f"{prefix}{m.group(1)}"
    return prefix + date_str


# ─────────────────────────────────────────────
#  PARSEUR GEDCOM
# ─────────────────────────────────────────────

def parse_gedcom(filepath):
    """Parse un fichier GEDCOM et retourne (individuals, families)."""
    # Essaye differents encodages
    content = None
    for enc in ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']:
        try:
            with open(filepath, encoding=enc) as f:
                content = f.readlines()
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
    if content is None:
        raise ValueError(f"Impossible de lire {filepath} — encodage inconnu")

    individuals = {}
    families = {}
    current_id = None
    current_type = None  # 'INDI' ou 'FAM'
    current_sub = None   # 'BIRT', 'DEAT', 'MARR'

    for line in content:
        line = line.strip()
        if not line:
            continue

        # Niveau 0 : nouveau record
        m = re.match(r'^0 @(I\d+)@ INDI', line)
        if m:
            current_id = m.group(1)
            current_type = 'INDI'
            current_sub = None
            individuals[current_id] = {
                'name': '', 'givn': '', 'surn': '', 'sex': '',
                'birt_date': '', 'birt_plac': '',
                'deat_date': '', 'deat_plac': '',
                'occu': [],
                'fams': [], 'famc': [],
            }
            continue

        m = re.match(r'^0 @(F\d+)@ FAM', line)
        if m:
            current_id = m.group(1)
            current_type = 'FAM'
            current_sub = None
            families[current_id] = {
                'husb': '', 'wife': '',
                'chil': [],
                'marr_date': '', 'marr_plac': ''
            }
            continue

        if line.startswith('0 '):
            current_id = None
            current_type = None
            current_sub = None
            continue

        # Niveau 1+ : proprietes
        if current_type == 'INDI' and current_id:
            ind = individuals[current_id]
            if line.startswith('1 NAME '):
                raw = line[7:].strip()
                ind['name'] = raw.replace('/', '').strip()
                m_surn = re.search(r'/([^/]+)/', raw)
                if m_surn:
                    ind['surn'] = m_surn.group(1).strip()
                    ind['givn'] = raw[:raw.index('/')].strip()
                else:
                    ind['givn'] = ind['name']
            elif line.startswith('2 GIVN '):
                ind['givn'] = line[7:].strip()
            elif line.startswith('2 SURN '):
                ind['surn'] = line[7:].strip()
            elif line.startswith('1 SEX '):
                ind['sex'] = line[6:].strip()
            elif line.startswith('1 OCCU '):
                ind['occu'].append(line[7:].strip())
            elif line.startswith('1 BIRT'):
                current_sub = 'BIRT'
            elif line.startswith('1 DEAT'):
                current_sub = 'DEAT'
            elif line.startswith('1 FAMS @'):
                fid = re.search(r'@(F\d+)@', line)
                if fid:
                    ind['fams'].append(fid.group(1))
            elif line.startswith('1 FAMC @'):
                fid = re.search(r'@(F\d+)@', line)
                if fid:
                    ind['famc'].append(fid.group(1))
            elif line.startswith('2 DATE ') and current_sub:
                val = line[7:].strip()
                if current_sub == 'BIRT':
                    ind['birt_date'] = val
                elif current_sub == 'DEAT':
                    ind['deat_date'] = val
            elif line.startswith('2 PLAC ') and current_sub:
                val = line[7:].strip()
                if current_sub == 'BIRT':
                    ind['birt_plac'] = val
                elif current_sub == 'DEAT':
                    ind['deat_plac'] = val
            elif line.startswith('1 '):
                current_sub = None

        elif current_type == 'FAM' and current_id:
            fam = families[current_id]
            if line.startswith('1 HUSB @'):
                m2 = re.search(r'@(I\d+)@', line)
                if m2:
                    fam['husb'] = m2.group(1)
            elif line.startswith('1 WIFE @'):
                m2 = re.search(r'@(I\d+)@', line)
                if m2:
                    fam['wife'] = m2.group(1)
            elif line.startswith('1 CHIL @'):
                m2 = re.search(r'@(I\d+)@', line)
                if m2:
                    fam['chil'].append(m2.group(1))
            elif line.startswith('1 MARR'):
                current_sub = 'MARR'
            elif line.startswith('2 DATE ') and current_sub == 'MARR':
                fam['marr_date'] = line[7:].strip()
            elif line.startswith('2 PLAC ') and current_sub == 'MARR':
                fam['marr_plac'] = line[7:].strip()
            elif line.startswith('1 '):
                current_sub = None

    return individuals, families


# ─────────────────────────────────────────────
#  DEDUPLICATION
# ─────────────────────────────────────────────

def deduplicate(individuals, families):
    """
    Gramps cree des doublons (original + copie fusionnee).
    On garde l'individu avec le plus d'informations.
    """
    # Cle de dedup : (nom, date naissance, lieu naissance)
    groups = defaultdict(list)
    for iid, ind in individuals.items():
        key = (ind['name'].lower().strip(), ind['birt_date'].strip(), ind['birt_plac'].strip())
        groups[key].append(iid)

    # Mapping ancien ID -> ID conserve
    id_map = {}
    keep_ids = set()

    for key, ids in groups.items():
        if len(ids) == 1:
            id_map[ids[0]] = ids[0]
            keep_ids.add(ids[0])
        else:
            # Garde celui avec le plus de donnees
            def score(iid):
                ind = individuals[iid]
                s = 0
                if ind['birt_date']:
                    s += 2
                if ind['birt_plac']:
                    s += 2
                if ind['deat_date']:
                    s += 1
                if ind['deat_plac']:
                    s += 1
                s += len(ind['occu']) * 2
                s += len(ind['fams'])
                s += len(ind['famc'])
                return s
            ids_sorted = sorted(ids, key=score, reverse=True)
            best = ids_sorted[0]
            keep_ids.add(best)
            for iid in ids:
                id_map[iid] = best
            # Fusionne les metiers et liens famille
            best_ind = individuals[best]
            for iid in ids_sorted[1:]:
                dup = individuals[iid]
                for occ in dup['occu']:
                    if occ not in best_ind['occu']:
                        best_ind['occu'].append(occ)
                for fid in dup['fams']:
                    if fid not in best_ind['fams']:
                        best_ind['fams'].append(fid)
                for fid in dup['famc']:
                    if fid not in best_ind['famc']:
                        best_ind['famc'].append(fid)
                # Comble les trous
                if not best_ind['birt_date'] and dup['birt_date']:
                    best_ind['birt_date'] = dup['birt_date']
                if not best_ind['birt_plac'] and dup['birt_plac']:
                    best_ind['birt_plac'] = dup['birt_plac']
                if not best_ind['deat_date'] and dup['deat_date']:
                    best_ind['deat_date'] = dup['deat_date']
                if not best_ind['deat_plac'] and dup['deat_plac']:
                    best_ind['deat_plac'] = dup['deat_plac']

    # Met a jour les refs dans les familles
    clean_fams = {}
    for fid, fam in families.items():
        fam['husb'] = id_map.get(fam['husb'], fam['husb'])
        fam['wife'] = id_map.get(fam['wife'], fam['wife'])
        fam['chil'] = [id_map.get(c, c) for c in fam['chil']]
        clean_fams[fid] = fam

    # Remap famc/fams dans les individus conserves
    for iid in keep_ids:
        ind = individuals[iid]
        # Deduplique les liens famille
        ind['fams'] = list(dict.fromkeys(ind['fams']))
        ind['famc'] = list(dict.fromkeys(ind['famc']))

    # Remap les refs husb/wife/chil dans les familles vers les IDs conserves
    for fid, fam in clean_fams.items():
        if fam['husb']:
            fam['husb'] = id_map.get(fam['husb'], fam['husb'])
        if fam['wife']:
            fam['wife'] = id_map.get(fam['wife'], fam['wife'])
        fam['chil'] = list(dict.fromkeys(id_map.get(c, c) for c in fam['chil']))
        # Ne garde que les enfants qui existent encore
        fam['chil'] = [c for c in fam['chil'] if c in keep_ids]

    # Remap les famc/fams des individus conserves pour pointer vers des familles valides
    for iid in keep_ids:
        ind = individuals[iid]
        # Assure que les famc/fams sont uniques
        ind['fams'] = list(dict.fromkeys(ind['fams']))
        ind['famc'] = list(dict.fromkeys(ind['famc']))

    clean_inds = {iid: individuals[iid] for iid in keep_ids}
    return clean_inds, clean_fams, id_map


# ─────────────────────────────────────────────
#  CALCUL DES LIGNEES & GENERATIONS
# ─────────────────────────────────────────────

# Couleurs par branche
LINEAGE_COLORS = {
    "Van Dijk": "#2c5f8a",
    "Bassaisteguy": "#7b3fa0",
    "Louis": "#1a7561",
    "Bleytou": "#c47d0a",
    "Tourdot": "#c0392b",
    "Baudemont": "#b04a00",
    "Cherrier": "#2a8c5a",
    "Vonthron": "#d35400",
    "Duchesne": "#8e6f3e",
    "Oliveau": "#5b7553",
    "Autre": "#888888",
}

# Noms de famille -> lignee
SURNAME_TO_LINEAGE = {
    "van dijk": "Van Dijk",
    "van den dyk": "Van Dijk",
    "baijens": "Van Dijk",
    "snels": "Van Dijk",
    "lubberding": "Van Dijk",
    "rijkevorsel": "Van Dijk",
    "verbaan": "Van Dijk",
    "vrijbus": "Van Dijk",
    "wasman": "Van Dijk",
    "van ameide": "Van Dijk",
    "de koff": "Van Dijk",
    "van middelvelcht": "Van Dijk",
    "willems": "Van Dijk",
    "romans": "Van Dijk",
    "bassaisteguy": "Bassaisteguy",
    "bassagaisteguy": "Bassaisteguy",
    "bassagaitx": "Bassaisteguy",
    "bassagaits": "Bassaisteguy",
    "bassasteguy": "Bassaisteguy",
    "iriartegaray": "Bassaisteguy",
    "lasgoity": "Bassaisteguy",
    "arostalde": "Bassaisteguy",
    "caracotche": "Bassaisteguy",
    "olhasso": "Bassaisteguy",
    "gastellu": "Bassaisteguy",
    "louis": "Louis",
    "sylvestre": "Louis",
    "malache": "Louis",
    "richard": "Louis",
    "vialy": "Louis",
    "berre": "Louis",
    "thomas": "Louis",
    "robert": "Louis",
    "adam": "Louis",
    "francois": "Louis",
    "bleytou": "Bleytou",
    "bleytout": "Bleytou",
    "blaytou": "Bleytou",
    "blaytout": "Bleytou",
    "borderie": "Bleytou",
    "ferre": "Bleytou",
    "borde": "Bleytou",
    "coste": "Bleytou",
    "matignont": "Bleytou",
    "fromentin": "Bleytou",
    "gadras": "Bleytou",
    "tourdot": "Tourdot",
    "ragoy": "Tourdot",
    "remy": "Tourdot",
    "georgeon": "Tourdot",
    "gagnant": "Tourdot",
    "vonthron": "Vonthron",
    "reymann": "Vonthron",
    "beck": "Vonthron",
    "schneiderlin": "Vonthron",
    "keller": "Vonthron",
    "meyer": "Vonthron",
    "braunn": "Vonthron",
    "scmitt": "Vonthron",
    "schmitt": "Vonthron",
    "hasenforder": "Vonthron",
    "walber": "Vonthron",
    "bollecker": "Vonthron",
    "knissler": "Vonthron",
    "siffert": "Vonthron",
    "thomann": "Vonthron",
    "kalbenaeur": "Vonthron",
    "schweitzer": "Vonthron",
    "wisler": "Vonthron",
    "schante": "Vonthron",
    "duchesne": "Duchesne",
    "maurice": "Duchesne",
    "sassier": "Duchesne",
    "vernier": "Duchesne",
    "millet": "Duchesne",
    "gatillon": "Duchesne",
    "guiet": "Duchesne",
    "pichet": "Duchesne",
    "marnay": "Duchesne",
    "charlot": "Duchesne",
    "chesneau": "Duchesne",
    "nicolas": "Duchesne",
    "chauveau": "Duchesne",
    "deplaix": "Duchesne",
    "nonnet": "Duchesne",
    "pachet": "Duchesne",
    "beaumont": "Duchesne",
    "bouillon": "Duchesne",
    "dauzon": "Duchesne",
    "monjalon": "Duchesne",
    "chesnon": "Duchesne",
    "dubois": "Duchesne",
    "martin": "Duchesne",
    "chambille": "Duchesne",
    "chaluau": "Duchesne",
    "flambart": "Duchesne",
    "archambault": "Duchesne",
    "oliveau": "Oliveau",
    "olivaud": "Oliveau",
    "megrier": "Oliveau",
    "texier": "Oliveau",
    "chevalier": "Oliveau",
    "gouigoux": "Oliveau",
    "baillanges": "Oliveau",
    "traineau": "Oliveau",
    "ferrant": "Oliveau",
    "chereau": "Oliveau",
    "baudemont": "Baudemont",
    "jussaume": "Baudemont",
    "bourdeix": "Baudemont",
    "gobert": "Baudemont",
    "despoux": "Baudemont",
    "balais": "Baudemont",
    "patri": "Baudemont",
    "cherrier": "Cherrier",
    "gambais": "Cherrier",
    "tourdot cherrier": "Tourdot",
}


def guess_lineage(ind):
    """Devine la lignee d'un individu d'apres son nom de famille."""
    surn = ind.get('surn', '').strip().lower()
    name = ind.get('name', '').strip().lower()
    # Cherche le nom de famille dans la table
    if surn in SURNAME_TO_LINEAGE:
        return SURNAME_TO_LINEAGE[surn]
    # Essaye avec le nom complet
    for key, lineage in SURNAME_TO_LINEAGE.items():
        if key in name:
            return lineage
    return "Autre"


def compute_generations(individuals, families, root_ids):
    """
    Calcule la generation de chaque individu en remontant depuis les racines (gen 0).
    Utilise a la fois famc (child->parents) et les familles (chil lists).
    Utilise une approche iterative (BFS) pour eviter les problemes de recursion.
    """
    # Construit un index enfant -> parents via les familles
    child_to_parents = {}
    for fid, fam in families.items():
        parents = set()
        if fam.get('husb') and fam['husb'] in individuals:
            parents.add(fam['husb'])
        if fam.get('wife') and fam['wife'] in individuals:
            parents.add(fam['wife'])
        for chil_id in fam.get('chil', []):
            if chil_id in individuals:
                if chil_id not in child_to_parents:
                    child_to_parents[chil_id] = set()
                child_to_parents[chil_id].update(parents)
    # Aussi via famc des individus
    for iid, ind in individuals.items():
        for famc_id in ind.get('famc', []):
            fam = families.get(famc_id, {})
            if iid not in child_to_parents:
                child_to_parents[iid] = set()
            if fam.get('husb') and fam['husb'] in individuals:
                child_to_parents[iid].add(fam['husb'])
            if fam.get('wife') and fam['wife'] in individuals:
                child_to_parents[iid].add(fam['wife'])

    # BFS iteratif
    generations = {}
    queue = [(rid, 0) for rid in root_ids]
    while queue:
        iid, gen = queue.pop(0)
        if iid not in individuals:
            continue
        if iid in generations and generations[iid] <= gen:
            continue
        generations[iid] = gen
        for parent_id in child_to_parents.get(iid, set()):
            if parent_id not in generations or generations[parent_id] > gen + 1:
                queue.append((parent_id, gen + 1))

    return generations


GENERATION_LABELS = {
    0: "Enfant",
    1: "Parent",
    2: "Grand-parent",
    3: "Arriere-grand-parent",
    4: "Arriere-arriere-grand-parent",
}


def generation_label(gen, sex=''):
    """Retourne le label francais d'une generation."""
    if gen is None:
        return ""
    if gen in GENERATION_LABELS:
        lbl = GENERATION_LABELS[gen]
    else:
        lbl = f"Ancetre a la {gen}e generation"
        return lbl
    # Feminise si possible
    if sex == 'F':
        lbl = lbl.replace('Grand-parent', 'Grand-mere')
        lbl = lbl.replace('grand-parent', 'grand-mere')
        lbl = lbl.replace('Parent', 'Mere')
    elif sex == 'M':
        lbl = lbl.replace('Grand-parent', 'Grand-pere')
        lbl = lbl.replace('grand-parent', 'grand-pere')
        lbl = lbl.replace('Parent', 'Pere')
    return lbl


# ─────────────────────────────────────────────
#  CONSTRUCTION DU JSON FINAL
# ─────────────────────────────────────────────

def build_json(individuals, families, generations):
    """Construit la liste JSON finale."""
    result = []

    for iid, ind in individuals.items():
        year = parse_year(ind['birt_date'])
        lat, lng = geocode(ind['birt_plac'])

        # Trouve les conjoints (dedupliques par nom)
        spouses = []
        seen_spouses = set()
        for fam_id in ind.get('fams', []):
            fam = families.get(fam_id, {})
            sp_id = fam.get('wife', '') if ind['sex'] == 'M' else fam.get('husb', '')
            if sp_id and sp_id in individuals:
                sp = individuals[sp_id]
                sp_key = sp['name'].lower().strip()
                if sp_key not in seen_spouses:
                    seen_spouses.add(sp_key)
                    spouses.append({
                        'name': sp['name'],
                        'birt_date': format_date_fr(sp['birt_date']),
                        'deat_date': format_date_fr(sp['deat_date']),
                        'occu': ', '.join(sp['occu']) if sp['occu'] else '',
                        'marr_date': format_date_fr(fam.get('marr_date', '')),
                        'marr_plac': fam.get('marr_plac', ''),
                    })
            elif sp_id == '' and ind['sex'] == 'F':
                sp_id2 = fam.get('husb', '')
                if sp_id2 and sp_id2 in individuals:
                    sp = individuals[sp_id2]
                    sp_key = sp['name'].lower().strip()
                    if sp_key not in seen_spouses:
                        seen_spouses.add(sp_key)
                        spouses.append({
                            'name': sp['name'],
                            'birt_date': format_date_fr(sp['birt_date']),
                            'deat_date': format_date_fr(sp['deat_date']),
                            'occu': ', '.join(sp['occu']) if sp['occu'] else '',
                            'marr_date': format_date_fr(fam.get('marr_date', '')),
                            'marr_plac': fam.get('marr_plac', ''),
                        })

        lineage = guess_lineage(ind)
        gen = generations.get(iid)
        color = LINEAGE_COLORS.get(lineage, "#888888")

        # Place affichee = premiere partie du lieu
        place_display = ind['birt_plac'].split(',')[0].strip() if ind['birt_plac'] else ''

        entry = {
            'id': iid,
            'name': ind['name'],
            'sex': ind['sex'],
            'year': year,
            'birt_date': format_date_fr(ind['birt_date']),
            'birt_plac': ind['birt_plac'],
            'place': place_display,
            'deat_date': format_date_fr(ind['deat_date']),
            'deat_plac': ind['deat_plac'],
            'occu': ', '.join(ind['occu']) if ind['occu'] else '',
            'lat': lat,
            'lng': lng,
            'lineage': lineage,
            'color': color,
            'generation': gen,
            'relation': generation_label(gen, ind['sex']),
            'spouses': spouses,
        }
        result.append(entry)

    # Tri : par lignee puis par annee
    lineage_order = list(LINEAGE_COLORS.keys())
    result.sort(key=lambda x: (
        lineage_order.index(x['lineage']) if x['lineage'] in lineage_order else 99,
        x['year'] or 9999
    ))

    return result


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Convertit un fichier GEDCOM en JSON pour le site de genealogie')
    parser.add_argument('gedcom', help='Chemin vers le fichier .ged')
    parser.add_argument('-o', '--output', default='data/individuals.json', help='Fichier JSON de sortie')
    parser.add_argument('--roots', nargs='*', default=None,
                        help='IDs des individus racines (enfants). Auto-detecte si absent.')
    args = parser.parse_args()

    print(f"Lecture de {args.gedcom}...")
    individuals, families = parse_gedcom(args.gedcom)
    print(f"  {len(individuals)} individus, {len(families)} familles")

    print("Deduplication...")
    individuals, families, id_map = deduplicate(individuals, families)
    print(f"  {len(individuals)} individus uniques apres deduplication")

    # Auto-detection des racines (individus les plus recents sans enfants)
    if args.roots:
        root_ids = [id_map.get(r, r) for r in args.roots]
    else:
        # Cherche les enfants Tourdot Cherrier
        root_ids = []
        for iid, ind in individuals.items():
            name = ind['name'].lower()
            if 'tourdot cherrier' in name or (parse_year(ind['birt_date']) and parse_year(ind['birt_date']) >= 2020):
                root_ids.append(iid)
        if not root_ids:
            # Fallback: individus les plus recents
            by_year = sorted(individuals.items(), key=lambda x: parse_year(x[1]['birt_date']) or 0, reverse=True)
            root_ids = [by_year[0][0]] if by_year else []
        print(f"  Racines auto-detectees: {[individuals[r]['name'] for r in root_ids]}")

    print("Calcul des generations...")
    generations = compute_generations(individuals, families, root_ids)
    print(f"  {len(generations)} individus avec generation calculee")

    print("Construction du JSON...")
    result = build_json(individuals, families, generations)

    # Stats
    with_gps = sum(1 for r in result if r['lat'] is not None)
    with_occu = sum(1 for r in result if r['occu'])
    with_spouse = sum(1 for r in result if r['spouses'])
    no_gps = [r for r in result if r['lat'] is None and r['birt_plac']]

    print(f"\nResultat: {len(result)} individus")
    print(f"  Avec GPS:     {with_gps}")
    print(f"  Avec metier:  {with_occu}")
    print(f"  Avec conjoint: {with_spouse}")

    if no_gps:
        print(f"\n  ATTENTION: {len(no_gps)} lieux sans coordonnees GPS:")
        seen = set()
        for r in no_gps:
            norm = normalize_place(r['birt_plac'])
            if norm not in seen:
                seen.add(norm)
                print(f"    - \"{norm}\" (original: {r['birt_plac']})")
        print("  -> Ajoute-les dans GEOCACHE en haut du script puis relance.")

    # Ecrit le JSON
    os.makedirs(os.path.dirname(args.output) or '.', exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\nJSON ecrit dans {args.output}")


if __name__ == '__main__':
    main()
