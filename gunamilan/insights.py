"""Deterministic explanations. Never invent scores, traits or confidence percentages."""
from .knowledge import TERMS, term_key


def explain_factor(item, system):
    definition = TERMS.get(term_key(item["name"]))
    return {"name": item["name"], "key": term_key(item["name"]), "system": system,
            "meaning": definition["meaning"] if definition else "Read the implemented rule below.",
            "next_step": definition["next_step"] if definition else "Check the input and rule explanation.",
            "explanation": item["explanation"]}


def analyze_match(data):
    a, p = data.get("ashtakoota"), data.get("porutham")
    strong, review, summaries, flags, exceptions = [], [], [], [], []
    if a:
        summaries.append(f"{a['total']:g} of {a['maximum']:g} Ashtakoota points across {len(a['kootas'])} factors.")
        for item in a["kootas"]:
            row = {**explain_factor(item, "ashtakoota"), "score": item["score"], "maximum": item["maximum"],
                   "gap": round(item["maximum"] - item["score"], 2)}
            (strong if row["gap"] == 0 else review).append(row)
        review.sort(key=lambda item: (-item["gap"], item["name"]))
        flags.extend("Ashtakoota: " + name for name in a["blocking_doshas"])
        for name, notes in a.get("exceptions", {}).items():
            for note in notes:
                exceptions.append({"name": name.title(), "text": note})
    if p:
        summaries.append(f"{p['passed']} of {p['total']} Porutham checks passed.")
        flags.extend("Porutham: " + name for name in p["essential_failures"])
    return {"version": 1, "language": "en", "summary": " ".join(summaries), "full_points": strong,
            "review_factors": review, "essential_flags": flags, "exceptions": exceptions,
            "accuracy": "Approximate Moon positions. Ascendant and houses are omitted for unknown times."
            if data.get("accuracy_warning") else "Both birth times were supplied. Input accuracy has not been independently verified.",
            "context": "Points not earned explain the arithmetic, not real-world severity. These scores are not probabilities of relationship success."}


def analyze_chart(chart):
    by_name = {g["name"]: g for g in chart.get("grahas", [])}
    highlights = []
    for name in ["Moon", "Sun"]:
        if g := by_name.get(name):
            highlights.append({"title": name + " sign", "value": g["rashi"],
                               "detail": g["nakshatra"] + " · pada " + str(g["pada"]), "key": "rashi"})
    ascendant = chart.get("ascendant")
    highlights.append({"title": "Ascendant", "value": ascendant["rashi"] if ascendant else "Not calculated",
                       "detail": "Whole-sign houses" if ascendant else "Birth time unknown", "key": "lagna"})
    return {"version": 1, "language": "en", "highlights": highlights,
            "summary": "Your chart maps nine grahas to the sidereal zodiac. Select a graha to explore its exact position.",
            "accuracy": "Birth time supplied. Verify the original record and timezone." if chart.get("time_known") else
            "Approximate noon positions. Your Moon sign or birth star may change across the day."}
