import json
from thefuzz import fuzz
import fuzzy
soundex = fuzzy.Soundex(4)

def load_nickname_data(filename="nickname_data.json"):
    with open(filename, "r", encoding="utf-8") as file:
        return json.load(file)

def save_nickname_data(data, filename="nickname_data.json"):
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)

def load_variant_data(filename="nickname_variants.json"):
    with open(filename, "r", encoding="utf-8") as file:
        return json.load(file)

def save_variant_data(data, filename="nickname_variants.json"):
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)

def add_nickname(formal_name, nickname, data):
    """Ensure nickname is added in the new structured format."""
    entry = data.get(formal_name)

    if isinstance(entry, dict):
        if nickname not in entry["nicknames"]:
            entry["nicknames"].append(nickname)
    elif isinstance(entry, list):
        # legacy format, upgrade it
        if nickname not in entry:
            entry.append(nickname)
        data[formal_name] = {
            "nicknames": entry,
            "century": [20],
            "region": ["English"]
        }
    else:
        data[formal_name] = {
            "nicknames": [nickname],
            "century": [20],
            "region": ["English"]
        }
    return data


def add_variant(canonical_name, variant_name, variant_data):
    if canonical_name not in variant_data:
        variant_data[canonical_name] = []
    if variant_name not in variant_data[canonical_name]:
        variant_data[canonical_name].append(variant_name)
    return variant_data


def get_nicknames(name, data, variant_data):
    """Return a list of nicknames for a given name, merging known spelling variants."""
    name_lower = name.lower()
    nicknames = set()

    # Search direct name match
    for formal_name in data:
        if formal_name.lower() == name_lower:
            entry = get_entry(formal_name, data)
            nicknames.update(entry.get("nicknames", []))

    # Check spelling variants
    for canonical, variants in variant_data.items():
        all_names = [canonical] + variants
        if any(name_lower == v.lower() for v in all_names):
            for variant_name in all_names:
                if variant_name in data:
                    entry = get_entry(variant_name, data)
                    nicknames.update(entry.get("nicknames", []))

    return sorted(nicknames)


def search_by_nickname(nickname, data):
    """Return a list of formal names that include the given nickname (case-insensitive)."""
    nickname_lower = nickname.lower()
    results = []
    for formal_name, nicknames in data.items():
        if any(n.lower() == nickname_lower for n in nicknames):
            results.append(formal_name)
    return results

def suggest_close_names(name, data, threshold=70):
    """Return a list of names that closely match the input."""
    suggestions = []
    for key in data.keys():
        score = fuzz.ratio(name.lower(), key.lower())
        if score >= threshold:
            suggestions.append((key, score))
    return sorted(suggestions, key=lambda x: -x[1])

def search_by_nickname_strength(nickname, data, partial_match=False):
    """Return list of formal names with match strength (for reverse lookup)."""
    nickname_lower = nickname.lower()
    results = []

    for formal_name, nicknames in data.items():
        for n in nicknames:
            # Exact match
            if n.lower() == nickname_lower:
                results.append((formal_name, 100))
                break
            # Partial match
            elif partial_match and nickname_lower in n.lower():
                results.append((formal_name, 70))
            # Fuzzy match
            else:
                score = fuzz.ratio(nickname_lower, n.lower())
                if score >= 70:
                    results.append((formal_name, score))

    return sorted(results, key=lambda x: -x[1])

# Reusable soundex helper
def get_soundex_code(name):
    """Return the Soundex code for the given name, or None if invalid."""
    try:
        return soundex(name)
    except Exception:
        return None

def search_by_soundex(name, data):
    """Return names that have a matching Soundex code."""
    code = get_soundex_code(name)
    if not code:
        return []

    matches = []
    for formal_name in data:
        match_code = get_soundex_code(formal_name)
        if match_code and match_code == code:
            matches.append(formal_name)
    return matches

def best_guess_matches(nickname, data):
    """Return combined matches with match sources and scores."""
    seen = {}
    results = []

    # 1. Exact match
    for name in search_by_nickname(nickname, data):
        seen[name] = {"score": 100, "sources": ["Exact"]}

    # 2. Fuzzy/Partial match
    for name, score in search_by_nickname_strength(nickname, data, partial_match=True):
        if name in seen:
            seen[name]["sources"].append("Fuzzy/Partial")
            seen[name]["score"] = max(seen[name]["score"], score)
        else:
            seen[name] = {"score": score, "sources": ["Fuzzy/Partial"]}

    # 3. Soundex
    for name in search_by_soundex(nickname, data):
        if name in seen:
            seen[name]["sources"].append("Soundex")
            seen[name]["score"] = max(seen[name]["score"], 65)
        else:
            seen[name] = {"score": 65, "sources": ["Soundex"]}

    for name, info in seen.items():
        results.append((name, info["score"], info["sources"]))

    return sorted(results, key=lambda x: -x[1])


def get_entry(formal_name, data):
    """Normalize nickname entry to always return a dict with metadata."""
    entry = data.get(formal_name)
    if isinstance(entry, dict):
        return entry
    elif isinstance(entry, list):  # old format
        return {"nicknames": entry, "century": [], "region": []}
    else:
        return {"nicknames": [], "century": [], "region": []}

def filter_nicknames_by_metadata(data, century=None, region=None):
    """Filter names that match a specific century and/or region or subregion."""
    filtered = {}

    for formal_name in data:
        entry = get_entry(formal_name, data)
        if century and century not in entry["century"]:
            continue
        if region and region.lower() not in [r.lower() for r in entry["region"]]:
            continue
        filtered[formal_name] = entry

    return filtered

