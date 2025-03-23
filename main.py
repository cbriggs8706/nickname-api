from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import json

from nickname_converter import (
    get_nicknames,
    get_entry,
    best_guess_matches,
    filter_nicknames_by_metadata,
    search_by_soundex,
    suggest_close_names
)

# Load structured data
with open("nickname_data.json", "r", encoding="utf-8") as f:
    nickname_data = json.load(f)

with open("nickname_variants.json", "r", encoding="utf-8") as f:
    variant_data = json.load(f)

app = FastAPI(title="Nickname Converter API")

# Allow requests from anywhere (adjust for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "Nickname API is live. Use /search?q=..."}

@app.get("/nicknames")
def get_nickname_list(name: str):
    entry = get_entry(name, nickname_data)
    all_nicknames = get_nicknames(name, nickname_data, variant_data)
    return {
        "name": name,
        "nicknames": all_nicknames,
        "century": entry.get("century", []),
        "region": entry.get("region", []),
        "subregion": entry.get("subregion", [])
    }

@app.get("/filter")
def filter_by_metadata(
    century: Optional[int] = Query(None),
    region: Optional[str] = Query(None),
    subregion: Optional[str] = Query(None)
):
    filtered = filter_nicknames_by_metadata(nickname_data, century, region, subregion)
    return {
        name: {
            "nicknames": get_entry(name, filtered)["nicknames"],
            "century": get_entry(name, filtered)["century"],
            "region": get_entry(name, filtered)["region"],
            "subregion": get_entry(name, filtered).get("subregion", [])
        }
        for name in sorted(filtered)
    }

@app.get("/autocomplete")
def autocomplete(q: str = Query(..., description="Partial input to suggest formal names")):
    suggestions = suggest_close_names(q, nickname_data)
    return [name for name, _ in suggestions]

@app.get("/search")
def smart_search(q: str = Query(..., description="Name or nickname to search")):
    matches = best_guess_matches(q, nickname_data)

    # If no good match found, try Soundex fallback
    if not matches:
        soundex_fallback = search_by_soundex(q, nickname_data)
        if soundex_fallback:
            response = []
            for name in soundex_fallback:
                entry = get_entry(name, nickname_data)
                response.append({
                    "name": name,
                    "nicknames": entry.get("nicknames", []),
                    "century": entry.get("century", []),
                    "region": entry.get("region", []),
                    "subregion": entry.get("subregion", []),
                    "score": 65,
                    "sources": ["Soundex"],
                    "duplicate": False
                })
            return response

        # Fallback to suggestion if nothing found
        suggestions = suggest_close_names(q, nickname_data)
        return {
            "matches": [],
            "suggestions": [
                {"name": name, "similarity": score}
                for name, score in suggestions
            ]
        }

    # Normal match results
    response = []
    for name, score, sources in matches:
        entry = get_entry(name, nickname_data)
        response.append({
            "name": name,
            "nicknames": entry.get("nicknames", []),
            "century": entry.get("century", []),
            "region": entry.get("region", []),
            "subregion": entry.get("subregion", []),
            "score": score,
            "sources": sources,
            "duplicate": len(sources) > 1
        })

    return sorted(response, key=lambda x: -x["score"])
