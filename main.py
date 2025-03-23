from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
import json
from nickname_converter import (
    get_nicknames,
    search_by_nickname,
    best_guess_matches,
    filter_nicknames_by_metadata,
    get_entry,
    search_by_soundex
)

# Load data files
with open("nickname_data.json", "r", encoding="utf-8") as f:
    nickname_data = json.load(f)

with open("nickname_variants.json", "r", encoding="utf-8") as f:
    variant_data = json.load(f)

app = FastAPI(title="Nickname Converter API")

# Enable CORS for local dev / frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/nicknames")
def get_nickname_list(name: str):
    entry = get_entry(name, nickname_data)
    all_nicknames = get_nicknames(name, nickname_data, variant_data)
    return {
        "name": name,
        "nicknames": all_nicknames,
        "century": entry.get("century", []),
        "region": entry.get("region", [])
    }


@app.get("/reverse")
def reverse_lookup(nickname: str):
    return search_by_nickname(nickname, nickname_data)

@app.get("/best-match")
def best_match(input: str):
    matches = best_guess_matches(input, nickname_data)
    return [
        {"name": name, "score": score, "sources": sources}
        for name, score, sources in matches
    ]

@app.get("/soundex")
def soundex_match(name: str):
    return search_by_soundex(name, nickname_data)

@app.get("/filter")
def filter_by_metadata(
    century: Optional[int] = Query(None),
    region: Optional[str] = Query(None)
):
    filtered = filter_nicknames_by_metadata(nickname_data, century, region)
    return {
        name: {
            "nicknames": get_entry(name, filtered)["nicknames"],
            "century": get_entry(name, filtered)["century"],
            "region": get_entry(name, filtered)["region"]
        }
        for name in sorted(filtered)
    }
