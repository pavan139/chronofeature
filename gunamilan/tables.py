"""
Traditional lookup tables for Ashtakoota (Guna Milan) matching.

Every table here encodes a classical rule, not a computation. Where different
schools disagree, the variant used is named in the comment above the table so a
practising astrologer can see exactly which tradition this implements and swap
it without touching the scoring logic.

Indices: nakshatras and rashis are 0-based internally (Ashwini = 0, Aries = 0).
"""

# --------------------------------------------------------------------------
# Nakshatras
# --------------------------------------------------------------------------

NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
    "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha",
    "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana",
    "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada",
    "Revati",
]

NAKSHATRA_DEVANAGARI = [
    "अश्विनी", "भरणी", "कृत्तिका", "रोहिणी", "मृगशिरा", "आर्द्रा",
    "पुनर्वसु", "पुष्य", "आश्लेषा", "मघा", "पूर्व फाल्गुनी",
    "उत्तर फाल्गुनी", "हस्त", "चित्रा", "स्वाति", "विशाखा", "अनुराधा",
    "ज्येष्ठा", "मूल", "पूर्वाषाढा", "उत्तराषाढा", "श्रवण",
    "धनिष्ठा", "शतभिषा", "पूर्व भाद्रपद", "उत्तर भाद्रपद", "रेवती",
]

# --------------------------------------------------------------------------
# Rashis (Moon signs)
# --------------------------------------------------------------------------

RASHIS = [
    "Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya",
    "Tula", "Vrishchika", "Dhanu", "Makara", "Kumbha", "Meena",
]

RASHIS_EN = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

# Sign lords, used by Graha Maitri.
RASHI_LORD = [
    "Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury",
    "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter",
]

# --------------------------------------------------------------------------
# 1. Varna Koota (1 point)
# Brahmin > Kshatriya > Vaishya > Shudra, keyed by the element of the Moon sign.
# --------------------------------------------------------------------------

VARNA_BY_RASHI = [
    "Kshatriya",  # Aries (fire)
    "Vaishya",    # Taurus (earth)
    "Shudra",     # Gemini (air)
    "Brahmin",    # Cancer (water)
    "Kshatriya",  # Leo
    "Vaishya",    # Virgo
    "Shudra",     # Libra
    "Brahmin",    # Scorpio
    "Kshatriya",  # Sagittarius
    "Vaishya",    # Capricorn
    "Shudra",     # Aquarius
    "Brahmin",    # Pisces
]

VARNA_RANK = {"Shudra": 1, "Vaishya": 2, "Kshatriya": 3, "Brahmin": 4}

# --------------------------------------------------------------------------
# 2. Vashya Koota (2 points)
# Signs split across half-signs for Sagittarius and Capricorn, so this is keyed
# by (rashi_index, is_second_half).
# --------------------------------------------------------------------------

VASHYA_BY_RASHI = [
    "Chatushpada",  # Aries
    "Chatushpada",  # Taurus
    "Manava",       # Gemini
    "Jalachara",    # Cancer
    "Vanachara",    # Leo
    "Manava",       # Virgo
    "Manava",       # Libra
    "Keeta",        # Scorpio
    "Manava",       # Sagittarius - first half (second half: Chatushpada)
    "Chatushpada",  # Capricorn - first half (second half: Jalachara)
    "Manava",       # Aquarius
    "Jalachara",    # Pisces
]

# Sagittarius and Capricorn change category at 15 degrees into the sign.
VASHYA_SECOND_HALF_OVERRIDE = {8: "Chatushpada", 9: "Jalachara"}

# Rows are the groom's vashya, columns the bride's.
VASHYA_MATRIX = {
    "Chatushpada": {"Chatushpada": 2.0, "Manava": 1.0, "Jalachara": 2.0, "Vanachara": 0.0, "Keeta": 2.0},
    "Manava":      {"Chatushpada": 1.0, "Manava": 2.0, "Jalachara": 1.0, "Vanachara": 0.0, "Keeta": 2.0},
    "Jalachara":   {"Chatushpada": 2.0, "Manava": 1.0, "Jalachara": 2.0, "Vanachara": 0.5, "Keeta": 2.0},
    "Vanachara":   {"Chatushpada": 1.0, "Manava": 0.0, "Jalachara": 1.0, "Vanachara": 2.0, "Keeta": 2.0},
    "Keeta":       {"Chatushpada": 1.0, "Manava": 0.5, "Jalachara": 0.5, "Vanachara": 2.0, "Keeta": 2.0},
}

# --------------------------------------------------------------------------
# 3. Tara Koota (3 points)
# Computed, not tabulated. Remainders 3, 5 and 7 are inauspicious.
# --------------------------------------------------------------------------

INAUSPICIOUS_TARA = {3, 5, 7}

# --------------------------------------------------------------------------
# 4. Yoni Koota (4 points)
# Each nakshatra carries an animal and a gender. Same animal scores full marks;
# natural enemies score zero.
# --------------------------------------------------------------------------

YONI_BY_NAKSHATRA = [
    ("Horse", "M"),     # Ashwini
    ("Elephant", "M"),  # Bharani
    ("Sheep", "F"),     # Krittika
    ("Serpent", "M"),   # Rohini
    ("Serpent", "F"),   # Mrigashira
    ("Dog", "F"),       # Ardra
    ("Cat", "F"),       # Punarvasu
    ("Sheep", "M"),     # Pushya
    ("Cat", "M"),       # Ashlesha
    ("Rat", "M"),       # Magha
    ("Rat", "F"),       # Purva Phalguni
    ("Cow", "M"),       # Uttara Phalguni
    ("Buffalo", "F"),   # Hasta
    ("Tiger", "F"),     # Chitra
    ("Buffalo", "M"),   # Swati
    ("Tiger", "M"),     # Vishakha
    ("Deer", "F"),      # Anuradha
    ("Deer", "M"),      # Jyeshtha
    ("Dog", "M"),       # Mula
    ("Monkey", "M"),    # Purva Ashadha
    ("Mongoose", "F"),  # Uttara Ashadha
    ("Monkey", "F"),    # Shravana
    ("Lion", "F"),      # Dhanishta
    ("Horse", "F"),     # Shatabhisha
    ("Lion", "M"),      # Purva Bhadrapada
    ("Cow", "F"),       # Uttara Bhadrapada
    ("Elephant", "F"),  # Revati
]

_YONI_ORDER = [
    "Horse", "Elephant", "Sheep", "Serpent", "Dog", "Cat", "Rat", "Cow",
    "Buffalo", "Tiger", "Deer", "Monkey", "Mongoose", "Lion",
]

# Symmetric 14x14 compatibility grid, rows and columns in _YONI_ORDER.
# 4 = same yoni, 3 = friendly, 2 = neutral, 1 = unfriendly, 0 = mortal enemy.
_YONI_GRID = [
    [4, 2, 2, 3, 2, 2, 2, 1, 0, 1, 3, 3, 2, 1],  # Horse
    [2, 4, 3, 3, 2, 2, 2, 2, 3, 1, 2, 3, 2, 0],  # Elephant
    [2, 3, 4, 2, 1, 2, 1, 3, 3, 1, 2, 0, 3, 1],  # Sheep
    [3, 3, 2, 4, 2, 1, 1, 1, 1, 2, 2, 2, 0, 2],  # Serpent
    [2, 2, 1, 2, 4, 2, 1, 2, 2, 1, 0, 2, 3, 1],  # Dog
    [2, 2, 2, 1, 2, 4, 0, 2, 2, 1, 3, 3, 2, 1],  # Cat
    [2, 2, 1, 1, 1, 0, 4, 2, 2, 2, 2, 2, 3, 2],  # Rat
    [1, 2, 3, 1, 2, 2, 2, 4, 3, 0, 3, 2, 2, 1],  # Cow
    [0, 3, 3, 1, 2, 2, 2, 3, 4, 1, 2, 2, 2, 1],  # Buffalo
    [1, 1, 1, 2, 1, 1, 2, 0, 1, 4, 1, 1, 2, 1],  # Tiger
    [3, 2, 2, 2, 0, 3, 2, 3, 2, 1, 4, 2, 2, 1],  # Deer
    [3, 3, 0, 2, 2, 3, 2, 2, 2, 1, 2, 4, 3, 1],  # Monkey
    [2, 2, 3, 0, 3, 2, 3, 2, 2, 2, 2, 3, 4, 2],  # Mongoose
    [1, 0, 1, 2, 1, 1, 2, 1, 1, 1, 1, 1, 2, 4],  # Lion
]

YONI_MATRIX = {
    a: {b: _YONI_GRID[i][j] for j, b in enumerate(_YONI_ORDER)}
    for i, a in enumerate(_YONI_ORDER)
}

# --------------------------------------------------------------------------
# 5. Graha Maitri Koota (5 points)
# Natural (naisargika) friendship between the lords of the two Moon signs.
# --------------------------------------------------------------------------

PLANET_FRIENDS = {
    "Sun":     {"Moon", "Mars", "Jupiter"},
    "Moon":    {"Sun", "Mercury"},
    "Mars":    {"Sun", "Moon", "Jupiter"},
    "Mercury": {"Sun", "Venus"},
    "Jupiter": {"Sun", "Moon", "Mars"},
    "Venus":   {"Mercury", "Saturn"},
    "Saturn":  {"Mercury", "Venus"},
}

PLANET_ENEMIES = {
    "Sun":     {"Venus", "Saturn"},
    "Moon":    set(),
    "Mars":    {"Mercury"},
    "Mercury": {"Moon"},
    "Jupiter": {"Mercury", "Venus"},
    "Venus":   {"Sun", "Moon"},
    "Saturn":  {"Sun", "Moon", "Mars"},
}

# Scores keyed by the sorted pair of relationships each lord has to the other.
GRAHA_MAITRI_SCORE = {
    ("friend", "friend"): 5.0,
    ("friend", "neutral"): 4.0,
    ("neutral", "neutral"): 3.0,
    ("enemy", "friend"): 1.0,
    ("enemy", "neutral"): 0.5,
    ("enemy", "enemy"): 0.0,
}

# --------------------------------------------------------------------------
# 6. Gana Koota (6 points)
# --------------------------------------------------------------------------

GANA_BY_NAKSHATRA = [
    "Deva",      # Ashwini
    "Manushya",  # Bharani
    "Rakshasa",  # Krittika
    "Manushya",  # Rohini
    "Deva",      # Mrigashira
    "Manushya",  # Ardra
    "Deva",      # Punarvasu
    "Deva",      # Pushya
    "Rakshasa",  # Ashlesha
    "Rakshasa",  # Magha
    "Manushya",  # Purva Phalguni
    "Manushya",  # Uttara Phalguni
    "Deva",      # Hasta
    "Rakshasa",  # Chitra
    "Deva",      # Swati
    "Rakshasa",  # Vishakha
    "Deva",      # Anuradha
    "Rakshasa",  # Jyeshtha
    "Rakshasa",  # Mula
    "Manushya",  # Purva Ashadha
    "Manushya",  # Uttara Ashadha
    "Deva",      # Shravana
    "Rakshasa",  # Dhanishta
    "Rakshasa",  # Shatabhisha
    "Manushya",  # Purva Bhadrapada
    "Manushya",  # Uttara Bhadrapada
    "Deva",      # Revati
]

# Asymmetric: rows are the groom's gana, columns the bride's.
GANA_MATRIX = {
    "Deva":     {"Deva": 6.0, "Manushya": 5.0, "Rakshasa": 1.0},
    "Manushya": {"Deva": 6.0, "Manushya": 6.0, "Rakshasa": 0.0},
    "Rakshasa": {"Deva": 0.0, "Manushya": 0.0, "Rakshasa": 6.0},
}

# --------------------------------------------------------------------------
# 7. Bhakoot Koota (7 points)
# Zero for the 2/12, 5/9 and 6/8 mutual sign distances.
# --------------------------------------------------------------------------

BHAKOOT_AFFLICTED_PAIRS = {(2, 12), (12, 2), (5, 9), (9, 5), (6, 8), (8, 6)}

# --------------------------------------------------------------------------
# 8. Nadi Koota (8 points)
# Same nadi scores zero. This is the single heaviest koota.
# --------------------------------------------------------------------------

NADI_BY_NAKSHATRA = [
    "Adi",     # Ashwini
    "Madhya",  # Bharani
    "Antya",   # Krittika
    "Antya",   # Rohini
    "Madhya",  # Mrigashira
    "Adi",     # Ardra
    "Adi",     # Punarvasu
    "Madhya",  # Pushya
    "Antya",   # Ashlesha
    "Antya",   # Magha
    "Madhya",  # Purva Phalguni
    "Adi",     # Uttara Phalguni
    "Adi",     # Hasta
    "Madhya",  # Chitra
    "Antya",   # Swati
    "Antya",   # Vishakha
    "Madhya",  # Anuradha
    "Adi",     # Jyeshtha
    "Adi",     # Mula
    "Madhya",  # Purva Ashadha
    "Antya",   # Uttara Ashadha
    "Antya",   # Shravana
    "Madhya",  # Dhanishta
    "Adi",     # Shatabhisha
    "Adi",     # Purva Bhadrapada
    "Madhya",  # Uttara Bhadrapada
    "Antya",   # Revati
]

# --------------------------------------------------------------------------
# Mangal (Manglik) Dosha
# Mars in these houses counted from the reference point.
# --------------------------------------------------------------------------

MANGAL_HOUSES = {1, 2, 4, 7, 8, 12}

# Houses where the affliction is traditionally read as severe.
MANGAL_SEVERE_HOUSES = {7, 8}
