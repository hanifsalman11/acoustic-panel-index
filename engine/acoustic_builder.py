import os
import json
import re
import time
import math
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone

# ==========================================
# ENVIRONMENT CONFIGURATION
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
SITE_BASE_URL = os.environ.get("SITE_BASE_URL", "https://hanifsalman11.github.io/acoustic-panel-index").rstrip("/")
INDEXNOW_KEY = os.environ.get("INDEXNOW_KEY", "e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7").strip()
CUSTOM_ACOUSTIC = os.environ.get("CUSTOM_ACOUSTIC", "").strip()
PAGES_PER_RUN = int(os.environ.get("PAGES_PER_RUN", "3"))

DOCS_DIR = "docs"
DATA_DIR = "data"
PUBLISHED_FILE = os.path.join(DATA_DIR, "published_acoustics.json")
MONETIZATION_FILE = os.path.join(DATA_DIR, "monetization.json")

_CACHED_MODELS = None

# Format: (Room / Product Scenario, Length Ft, Width Ft, Height Ft, Target RT60 Sec, Panel NRC, Room Application)
SEED_ACOUSTICS = [
    ("10×12×8 Ft Podcast & Vocal Recording Booth Acoustic Sizing", 12.0, 10.0, 8.0, 0.30, 1.00, "Podcast & Vocal Studio"),
    ("12×15×8 Ft Home Mixing & Mastering Studio Acoustic Sizing", 15.0, 12.0, 8.0, 0.35, 1.05, "Mixing Control Room"),
    ("14×18×9 Ft Dedicated Dolby Atmos Home Theater Acoustic Sizing", 18.0, 14.0, 9.0, 0.35, 1.00, "Dolby Atmos Home Theater"),
    ("16×22×9 Ft Basement Home Theater & Media Room Sizing", 22.0, 16.0, 9.0, 0.40, 1.00, "Large Home Theater"),
    ("10×10×8 Ft Spare Bedroom Streamer & YouTube Studio Sizing", 10.0, 10.0, 8.0, 0.32, 0.95, "YouTube / Streaming Room"),
    ("12×12×8 Ft Square Room Standing-Wave & Bass Trap Sizing", 12.0, 12.0, 8.0, 0.35, 1.05, "Square Room Axial Mode Fix"),
    ("15×20×10 Ft Live Drum & Band Rehearsal Room Soundproofing", 20.0, 15.0, 10.0, 0.42, 1.05, "Drum & Band Isolation"),
    ("20×30×10 Ft Commercial Open Office & Conference Room Reverb", 30.0, 20.0, 10.0, 0.50, 0.95, "Conference & Office Echo"),
    ("30×40×12 Ft Restaurant & Dining Hall Crowd Noise Control", 40.0, 30.0, 12.0, 0.55, 0.95, "Restaurant Ceiling Clouds"),
    ("40×60×16 Ft Church Sanctuary & Gymnasium Acoustic Panel Sizing", 60.0, 40.0, 16.0, 0.65, 1.00, "Sanctuary / Gym Baffles"),
    ("ATS Acoustics 24\"×48\"×2\" Rigid Fiberglass Panel (NRC 1.05)", 15.0, 12.0, 8.0, 0.35, 1.05, "Mineral Wool / 703 Core"),
    ("Owens Corning 703 (2-Inch vs 4-Inch) DIY Acoustic Panel Sizing", 16.0, 13.0, 8.5, 0.35, 1.05, "3.0 lb/ft³ Fiberglass Board"),
    ("Rockwool Safe'n'Sound (3-Inch) Studio Wall & Bass Trap Sizing", 15.0, 12.0, 8.0, 0.35, 1.05, "Mineral Wool Cavity & Traps"),
    ("Primacoustic Broadway London 12 & London 16 Room Kit Sizing", 14.0, 12.0, 8.0, 0.35, 1.00, "High-Density 6 lb/ft³ Glass"),
    ("GIK Acoustics 242 Panels & 244 Bass Traps Room Sizing", 16.0, 13.0, 8.5, 0.35, 1.05, "First-Reflection & Corner Traps"),
    ("Mass Loaded Vinyl (MLV) 1 Lb/Sq Ft vs 2 Lb/Sq Ft STC Wall", 15.0, 12.0, 8.0, 0.35, 1.00, "STC 55+ Barrier Membrane"),
    ("Green Glue Noiseproofing Compound (28 oz Tubes) Drywall Sizing", 16.0, 14.0, 8.0, 0.35, 1.00, "Double 5/8\" Type-X Drywall"),
    ("Resilient Sound Isolation Clips (RSIC-1) & Hat Channel Spacing", 16.0, 14.0, 8.0, 0.35, 1.00, "24\"×48\" Clip Grid Decoupling"),
    ("2-Inch Polyurethane Acoustic Foam vs 2-Inch Fiberglass (NRC)", 12.0, 10.0, 8.0, 0.35, 0.85, "Mid/High vs Broadband NRC"),
    ("Wood Slat Acoustic Wall Panels (Akuwoodpanel) + Backing Felt", 15.0, 12.0, 8.5, 0.40, 0.85, "Slatted Wood + Mineral Wool"),
    ("Ceiling Cloud Acoustic Baffles for Vaulted Living Room Echo", 22.0, 18.0, 12.0, 0.45, 1.00, "Suspended Ceiling Clouds"),
    ("Home Golf Simulator Enclosure & Garage Bay Acoustic Sizing", 18.0, 14.0, 10.0, 0.40, 0.95, "Impact Driver Noise Damping"),
    ("Audiophile 2-Channel Hi-Fi Listening Room RT60 & First-Reflection", 17.0, 13.0, 8.5, 0.38, 1.00, "Mirror-Point Absorption"),
    ("Voiceover & Audiobook Closet Booth (6×6×8 Ft) Acoustic Sizing", 6.0, 6.0, 8.0, 0.25, 1.05, "Dead-Room <0.25s RT60"),
    ("20×20×9 Ft Two-Car Garage Workshop & Gym Soundproofing", 20.0, 20.0, 9.0, 0.45, 1.00, "Garage Door + Wall Barrier"),
    ("Shared Condo / Apartment Bedroom Party-Wall MLV + Green Glue", 15.0, 12.0, 8.0, 0.38, 1.00, "STC 60 Neighbor Isolation"),
    ("Home Server & Mining Rig Closet Acoustic Baffle & MLV Sizing", 8.0, 6.0, 8.0, 0.30, 1.05, "High-dB Fan Attenuation"),
    ("Indoor Pickleball & Racquet Court Perimeter Acoustic Curtain", 60.0, 30.0, 18.0, 0.60, 0.95, "Outdoor/Indoor Court Barrier"),
    ("Dog Kennel & Vet Boarding Room Washable Acoustic Baffle Sizing", 24.0, 16.0, 9.0, 0.45, 0.95, "PVC-Wrapped Washable Core"),
    ("Sabine vs Eyring RT60 Reverberation Equation & Sabin Calculator", 16.0, 12.0, 8.5, 0.35, 1.00, "Sabine 0.049×V/A Physics")
]


def load_json(filepath, default):
    """Self-healing JSON loader: otomatis pulih jika file korup atau kosong."""
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, type(default)) else default
        except Exception as e:
            print(f"[SELF-HEAL] Recovering {filepath} due to read notice: {e}")
    return default


def save_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    return re.sub(r"[\s-]+", "-", text).strip("-")


def safe_float(val, default=15.0):
    try:
        cleaned = re.sub(r"[^0-9.]", "", str(val))
        return float(cleaned) if cleaned else float(default)
    except Exception:
        return float(default)


def build_amazon_url(search_keywords, mon_cfg):
    domain = mon_cfg.get("marketplace_domain", "www.amazon.com")
    tag = mon_cfg.get("amazon_associate_tag", "YOUR_AMAZON_TAG-20")
    encoded_q = urllib.parse.quote_plus(search_keywords)
    return f"https://{domain}/s?k={encoded_q}&tag={tag}"


def get_active_gemini_model(api_key):
    """
    LAPIS 1: Mesin Pemindai Versi Model Free Tier Otomatis berbasis Regex tanpa angka versi manual.
    Otomatis mendeteksi model Gemini Flash STABIL generasi tertinggi lintas tahun.
    """
    global _CACHED_MODELS
    if _CACHED_MODELS is not None:
        return _CACHED_MODELS

    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        req = urllib.request.Request(list_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            scored_models = []

            for m in data.get("models", []):
                name = m.get("name", "").replace("models/", "")
                methods = m.get("supportedGenerationMethods", [])

                if "generateContent" not in methods or "flash" not in name.lower():
                    continue

                if any(bad in name.lower() for bad in [
                    "preview", "exp", "thinking", "image", "tts", "audio", "vision", "8b"
                ]):
                    continue

                ver_match = re.search(r"gemini-(\d+(?:\.\d+)?)-flash", name.lower())
                if ver_match:
                    ver_num = float(ver_match.group(1))
                    if name.lower() == f"gemini-{ver_match.group(1)}-flash":
                        tier_score = 2
                    elif name.lower() == f"gemini-{ver_match.group(1)}-flash-lite":
                        tier_score = 1
                    else:
                        tier_score = 0
                    scored_models.append((ver_num, tier_score, name))
                elif name.lower() == "gemini-flash-latest":
                    scored_models.append((0.1, 0, name))

            if scored_models:
                scored_models.sort(key=lambda x: (x[0], x[1]), reverse=True)
                _CACHED_MODELS = [item[2] for item in scored_models[:2]]
                print(f"[GEMINI] Future-proof active models locked: {_CACHED_MODELS}")
                return _CACHED_MODELS
    except Exception as e:
        print(f"[WARN] Dynamic model discovery notice: {e}")

    _CACHED_MODELS = ["gemini-flash-latest"]
    return _CACHED_MODELS


def discover_google_acoustic_queries(published_slugs):
    """
    LAPIS 4: 3-Tier Infinite Keyword Supply:
    Tier A: Seed List -> Tier B: Google Suggest US -> Tier C: Combinatorial Room × RT60 × NRC Permutator.
    """
    discovered = []
    seeds = [
        "how many acoustic panels for ",
        "acoustic panel calculator ",
        "mass loaded vinyl calculator ",
        "green glue calculator "
    ]
    for seed in seeds:
        try:
            url = f"http://suggestqueries.google.com/complete/search?client=firefox&hl=en&gl=us&q={urllib.parse.quote(seed)}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for suggestion in data[1]:
                    cleaned = suggestion.lower()
                    for pref in seeds:
                        if "how many" in pref or "calculator" in pref:
                            cleaned = cleaned.replace(pref, "")
                    cleaned = re.sub(
                        r"\b(calculator|size|sizing|chart|manual|review|reddit|for)\b",
                        "",
                        cleaned
                    ).strip()
                    if 5 <= len(cleaned) <= 42:
                        dim_m = re.search(r"(\d{1,2})x(\d{1,2})", cleaned)
                        if dim_m:
                            w_v = float(dim_m.group(1))
                            l_v = float(dim_m.group(2))
                        else:
                            w_v, l_v = 12.0, 15.0
                        discovered.append((cleaned.title(), l_v, w_v, 8.5, 0.35, 1.00, "Studio & Home Theater"))
        except Exception as e:
            print(f"[WARN] Google Suggest notice: {e}")

    # Tier C Fallback: Combinatorial Permutator (Anti-Habis Lintas Tahun)
    room_footprints = [
        (10.0, 11.0, 8.0, "10×11 Ft Bedroom Studio"),
        (11.0, 14.0, 8.0, "11×14 Ft Podcast & Mixing Room"),
        (12.0, 16.0, 8.5, "12×16 Ft Media & Theater Room"),
        (14.0, 19.0, 9.0, "14×19 Ft Dedicated Home Theater"),
        (16.0, 24.0, 9.0, "16×24 Ft Basement Rec Room"),
        (20.0, 25.0, 10.0, "20×25 Ft Commercial Studio / Office"),
        (25.0, 35.0, 12.0, "25×35 Ft Fellowship / Lecture Hall")
    ]
    room_uses = [
        ("Voiceover & Podcast (<0.30s RT60)", 0.28, 1.05),
        ("Music Mixing & Mastering (0.35s RT60)", 0.35, 1.05),
        ("Dolby Atmos Home Theater (0.38s RT60)", 0.38, 1.00),
        ("Video Call & Conference Office (0.45s RT60)", 0.45, 0.95)
    ]
    for w_f, l_f, h_f, r_desc in room_footprints:
        for use_desc, t_rt60, p_nrc in room_uses:
            combo_title = f"{r_desc} for {use_desc}"
            test_slug = slugify(f"{combo_title}-rt60-panel-mlv-calculator")
            if test_slug not in published_slugs:
                discovered.append((combo_title, l_f, w_f, h_f, t_rt60, p_nrc, use_desc))
                if len(discovered) >= 25:
                    return discovered
    return discovered


def build_deterministic_acoustic_data(ac_tuple):
    """
    LAPIS 3: Mesin Fisika Akustik Wallace Sabine (RT60 = 0.049 * V / A), MLV & Green Glue (100% Bebas Gagal).
    """
    room_name, len_ft, wid_ft, hgt_ft, target_rt60_sec, panel_nrc, app_type = ac_tuple

    # 1. Geometri Ruangan (Volume V dalam Cubic Feet & Total Luas Permukaan S dalam Sq Ft):
    floor_sqft = int(round(len_ft * wid_ft))
    wall_sqft = int(round(2.0 * (len_ft + wid_ft) * hgt_ft))
    total_surface_sqft = int(round((2.0 * floor_sqft) + wall_sqft))
    volume_cuft = int(round(len_ft * wid_ft * hgt_ft))

    # 2. Rumus Fisika Wallace Clement Sabine (RT60 = 0.049 * V / A_sabins):
    # Ruangan kosong (drywall + lantai kayu/ubin, alpha rata-rata = 0.042):
    untreated_sabins = round(total_surface_sqft * 0.042, 1)
    untreated_rt60_sec = round((0.049 * volume_cuft) / max(10.0, untreated_sabins), 2)

    # Sabin yang dibutuhkan untuk mencapai Target RT60 (A_target = 0.049 * V / Target_RT60):
    target_total_sabins = round((0.049 * volume_cuft) / max(0.20, float(target_rt60_sec)), 1)
    additional_sabins_needed = max(32.0, round(target_total_sabins - untreated_sabins, 1))

    # 3. Jumlah Panel Akustik 2'×4' (8 Sq. Ft. per panel, Sabins per panel = 8.0 * NRC):
    sabins_per_2x4_panel = round(8.0 * panel_nrc, 2)
    panels_2x4_needed = max(4, int(math.ceil(additional_sabins_needed / sabins_per_2x4_panel)))
    # Jumlah Corner Bass Traps (4 sudut tri-corner membutuhkan minimal 4 hingga 8 unit 2'×4' bass traps):
    bass_traps_needed = 4 if volume_cuft <= 1400 else (6 if volume_cuft <= 2600 else 8)
    total_absorption_sqft = panels_2x4_needed * 8
    wall_coverage_pct = round((total_absorption_sqft / max(100.0, float(wall_sqft))) * 100.0, 1)

    # 4. Kebutuhan Soundproofing Dinding (STC Isolation: Mass Loaded Vinyl + Green Glue):
    # Untuk melapisi dinding dengan MLV (1 roll = 100 sq ft) & 5/8" Drywall (1 lembar 4'×8' = 32 sq ft, 2 tabung Green Glue per lembar):
    mlv_100sqft_rolls = max(2, int(math.ceil((wall_sqft * 1.05) / 100.0)))
    drywall_4x8_sheets = max(6, int(math.ceil(wall_sqft / 32.0)))
    green_glue_28oz_tubes = drywall_4x8_sheets * 2

    return {
        "room_name": room_name,
        "app_type": app_type,
        "seo_title": f"{room_name} RT60 Reverb, Acoustic Panel & MLV Calculator (2026)",
        "meta_description": f"Calculate exact Sabine RT60 reverb reduction ({untreated_rt60_sec}s to {target_rt60_sec}s), 2'×4' acoustic panels ({panels_2x4_needed} panels + {bass_traps_needed} bass traps = {additional_sabins_needed} Sabins), {mlv_100sqft_rolls} rolls MLV, and {green_glue_28oz_tubes} Green Glue tubes for {room_name}.",
        "specs": {
            "length_ft": len_ft,
            "width_ft": wid_ft,
            "height_ft": hgt_ft,
            "floor_area_sqft": floor_sqft,
            "wall_area_sqft": wall_sqft,
            "room_volume_cuft": volume_cuft,
            "untreated_rt60_sec": untreated_rt60_sec,
            "target_rt60_sec": target_rt60_sec,
            "additional_sabins_needed": additional_sabins_needed,
            "panel_nrc_rating": panel_nrc,
            "panels_2x4_count": panels_2x4_needed,
            "corner_bass_traps_count": bass_traps_needed,
            "wall_coverage_pct": wall_coverage_pct,
            "mlv_100sqft_rolls": mlv_100sqft_rolls,
            "green_glue_28oz_tubes": green_glue_28oz_tubes,
            "app_type": app_type
        },
        "sabine_verdict": f"Measuring {wid_ft:g}' W × {len_ft:g}' L × {hgt_ft:g}' H ({volume_cuft:,} cu. ft. volume, {wall_sqft:,} sq. ft. wall area), an untreated {room_name} exhibits a slap-echo Reverberation Time ($RT_{{60}}$) of ~{untreated_rt60_sec} seconds ({untreated_sabins} baseline Sabins). Per the Wallace Sabine Equation ($RT_{{60}} = 0.049 \\times V \\div A$), dropping decay time to an acoustically tight {target_rt60_sec} seconds requires adding {additional_sabins_needed} Sabins of broadband absorption—achieved with {panels_2x4_needed}× 24\"×48\"×2\" fiberglass/mineral-wool panels (NRC {panel_nrc}, covering {wall_coverage_pct}% of wall area) plus {bass_traps_needed}× corner bass traps. For full STC 58+ soundblocking through the walls, hang {mlv_100sqft_rolls} rolls (100 sq. ft. each) of 1-lb/ft² Mass Loaded Vinyl and sandwich {drywall_4x8_sheets} sheets of 5/8\" drywall with {green_glue_28oz_tubes} tubes (28 oz) of Green Glue.",
        "hardware_bundle": [
            {
                "badge": f"{panels_2x4_needed}× 2'×4' Panels ({additional_sabins_needed:.0f} Sabins)",
                "title": f"24\" × 48\" × 2\" Fabric-Wrapped Rigid Fiberglass / Mineral Wool Acoustic Panels (NRC {panel_nrc})",
                "price_range": "$149 - $689",
                "amazon_query": "24x48x2 Rigid Fiberglass Acoustic Panels ATS Acoustics Primacoustic",
                "ac_note": f"Each 8 sq. ft. panel adds {sabins_per_2x4_panel} Sabins of broadband absorption down to 125 Hz—eliminating flutter echo."
            },
            {
                "badge": f"{mlv_100sqft_rolls} Rolls Mass Loaded Vinyl",
                "title": "1 Lb/Sq Ft (or 2 Lb/Sq Ft) Mass Loaded Vinyl (MLV) Soundproofing Barrier Roll (4' × 25' = 100 Sq Ft)",
                "price_range": "$169 - $389",
                "amazon_query": "Mass Loaded Vinyl 1 lb sq ft 100 sq ft Soundproofing Barrier Roll",
                "ac_note": "Limp-mass vinyl membrane blocks airborne voices, home theater subwoofers, and traffic noise from passing through walls."
            },
            {
                "badge": f"{green_glue_28oz_tubes} Tubes Green Glue + Clips",
                "title": "Green Glue Noiseproofing Compound Case (12× 28 oz Tubes) + RSIC-1 Sound Isolation Clips",
                "price_range": "$219 - $429",
                "amazon_query": "Green Glue Noiseproofing Compound Case 12 Tubes RSIC-1 Sound Isolation Clips",
                "ac_note": f"Apply 2 tubes per 4'×8' sheet ({green_glue_28oz_tubes} tubes for {wall_sqft:,} sq. ft. walls) to shear low-frequency drywall vibration into heat."
            },
            {
                "badge": f"{bass_traps_needed} Corner Traps & Door Seal",
                "title": "High-Density Tri-Corner Bass Traps + Solid-Core Door Acoustic Perimeter Gasket & Auto Bottom Sweep",
                "price_range": "$79 - $229",
                "amazon_query": "Corner Bass Traps Studio Acoustic Door Seal Kit Automatic Door Bottom Sweep",
                "ac_note": "Stops 60–120 Hz room-mode bass boom in tri-corners and seals the #1 sound leak around hollow/solid room doors."
            }
        ],
        "acoustician_checklist": [
            f"Never confuse Sound Absorption ($RT_{{60}}$ Acoustic Panels) with Sound Blocking (STC Mass Loaded Vinyl + Green Glue): {panels_2x4_needed} fiberglass panels absorb internal room reflections so audio sounds crystal clear, whereas blocking sound from escaping to other rooms requires limp mass (MLV) and decoupled double 5/8\" drywall.",
            "Use the Mirror Trick to place your First-Reflection Panels: sit in your listening/mixing chair while a helper slides a hand mirror flat along the left wall, right wall, and ceiling—every spot where you can see the speakers in the mirror gets a 2\" thick 24\"×48\" panel.",
            "Mount 2-inch rigid fiberglass (Owens Corning 703) or 3-inch Rockwool Safe'n'Sound panels with a 1-inch to 2-inch air gap behind the frame: spacing the panel off the drywall places the core at the quarter-wavelength velocity peak, doubling low-mid absorption below 250 Hz.",
            f"Straddle all 4 vertical room corners with thick Bass Traps ({bass_traps_needed} traps recommended): low-frequency pressure maxima accumulate in 90° dihedral and tri-hedral corners where thin 1-inch foam wedges have zero effect."
        ],
        "faqs": [
            {
                "q": f"How many 2x4 acoustic panels do I need for {room_name} ({floor_sqft:,} sq ft)?",
                "a": f"Using the Wallace Sabine reverberation formula ($RT_{{60}} = 0.049 \\times V \\div A$), a {volume_cuft:,} cu. ft. room needs {additional_sabins_needed} additional Sabins of absorption to drop $RT_{{60}}$ from {untreated_rt60_sec}s to {target_rt60_sec}s. Divided by {sabins_per_2x4_panel} Sabins per 2'×4' panel (8 sq. ft. × {panel_nrc} NRC), install {panels_2x4_needed} panels ({wall_coverage_pct}% wall coverage) plus {bass_traps_needed} corner bass traps."
            },
            {
                "q": f"How many rolls of Mass Loaded Vinyl (MLV) and tubes of Green Glue do I need for {wall_sqft:,} sq ft of walls?",
                "a": f"Covering {wall_sqft:,} sq. ft. of perimeter walls (including 5% seam allowance) requires {mlv_100sqft_rolls} rolls of 100-sq.-ft. Mass Loaded Vinyl. Hanging a second layer of 5/8\" drywall ({drywall_4x8_sheets} sheets of 4'×8') at the standard acoustical dose of 2 tubes (28 oz) per sheet requires {green_glue_28oz_tubes} tubes of Green Glue."
            },
            {
                "q": f"Why is 2-inch rigid fiberglass / Rockwool (NRC {panel_nrc}) better than 1-inch eggcrate foam?",
                "a": f"Cheap 1-inch open-cell polyurethane foam has an NRC of only 0.25–0.40 and only absorbs high-frequency hiss above 2,000 Hz—leaving boxy 250–500 Hz vocal mud untouched. A 2-inch rigid fiberglass (OC 703) or 3-inch Rockwool panel achieves an NRC of 0.95–1.05, absorbing broadband energy down to 125 Hz."
            }
        ]
    }


def generate_acoustic_data(ac_tuple):
    """
    LAPIS 2: Memanggil model Gemini stabil dengan proteksi Cooldown HTTP 429 & Fallback Otomatis.
    """
    if not GEMINI_API_KEY:
        return build_deterministic_acoustic_data(ac_tuple)

    room_name, len_ft, wid_ft, hgt_ft, target_rt60_sec, panel_nrc, app_type = ac_tuple
    det_fallback = build_deterministic_acoustic_data(ac_tuple)
    sp = det_fallback["specs"]

    prompt = f"""
You are a Certified INCE (Institute of Noise Control Engineering) Acoustical Consultant & Studio Designer. Create an accurate 2026 room acoustics RT60 reverberation time (Sabine equation), 2x4 acoustic panel count, corner bass trap sizing, Mass Loaded Vinyl (MLV), and Green Glue tube guide for: "{room_name}".
Baseline specs: Dimensions={wid_ft}' W x {len_ft}' L x {hgt_ft}' H ({sp['room_volume_cuft']} cu ft, Walls={sp['wall_area_sqft']} sq ft), Untreated RT60={sp['untreated_rt60_sec']}s -> Target RT60={target_rt60_sec}s, Additional Sabins Needed={sp['additional_sabins_needed']} Sabins, 2x4 Panels (NRC {panel_nrc})={sp['panels_2x4_count']} Panels ({sp['wall_coverage_pct']}% wall coverage) + {sp['corner_bass_traps_count']} Bass Traps, Soundblocking={sp['mlv_100sqft_rolls']} Rolls MLV (100 sq ft ea) + {sp['green_glue_28oz_tubes']} Tubes Green Glue.
Return ONLY a valid JSON object matching this exact schema:
{{
  "room_name": "{room_name}",
  "app_type": "{app_type}",
  "seo_title": "{room_name} RT60 Reverb, Acoustic Panel & MLV Calculator (2026)",
  "meta_description": "Calculate exact Sabine RT60 reverb time, 2x4 acoustic panel count, corner bass traps, Mass Loaded Vinyl rolls, and Green Glue tubes for {room_name}.",
  "specs": {{
    "length_ft": {len_ft},
    "width_ft": {wid_ft},
    "height_ft": {hgt_ft},
    "floor_area_sqft": {sp['floor_area_sqft']},
    "wall_area_sqft": {sp['wall_area_sqft']},
    "room_volume_cuft": {sp['room_volume_cuft']},
    "untreated_rt60_sec": {sp['untreated_rt60_sec']},
    "target_rt60_sec": {target_rt60_sec},
    "additional_sabins_needed": {sp['additional_sabins_needed']},
    "panel_nrc_rating": {panel_nrc},
    "panels_2x4_count": {sp['panels_2x4_count']},
    "corner_bass_traps_count": {sp['corner_bass_traps_count']},
    "wall_coverage_pct": {sp['wall_coverage_pct']},
    "mlv_100sqft_rolls": {sp['mlv_100sqft_rolls']},
    "green_glue_28oz_tubes": {sp['green_glue_28oz_tubes']},
    "app_type": "{app_type}"
  }},
  "sabine_verdict": "3-sentence technical summary stating room volume, untreated vs target RT60 via Sabine equation (0.049*V/A), required 2x4 panels and bass traps, and MLV rolls / Green Glue tubes for wall STC.",
  "hardware_bundle": [
    {{
      "badge": "{sp['panels_2x4_count']}× 2'×4' Panels ({sp['additional_sabins_needed']:.0f} Sabins)",
      "title": "24\" × 48\" × 2\" Rigid Fiberglass / Mineral Wool Acoustic Panels (NRC {panel_nrc})",
      "price_range": "$149 - $689",
      "amazon_query": "24x48x2 Rigid Fiberglass Acoustic Panels ATS Acoustics Primacoustic",
      "ac_note": "1-sentence broadband Sabin absorption and flutter echo elimination note"
    }},
    {{
      "badge": "{sp['mlv_100sqft_rolls']} Rolls Mass Loaded Vinyl",
      "title": "1 Lb/Sq Ft Mass Loaded Vinyl (MLV) Soundproofing Barrier Roll (100 Sq Ft)",
      "price_range": "$169 - $389",
      "amazon_query": "Mass Loaded Vinyl 1 lb sq ft 100 sq ft Soundproofing Barrier Roll",
      "ac_note": "1-sentence limp-mass STC transmission loss note"
    }},
    {{
      "badge": "{sp['green_glue_28oz_tubes']} Tubes Green Glue + Clips",
      "title": "Green Glue Noiseproofing Compound Case (12× 28 oz Tubes) + RSIC-1 Isolation Clips",
      "price_range": "$219 - $429",
      "amazon_query": "Green Glue Noiseproofing Compound Case 12 Tubes RSIC-1 Clips",
      "ac_note": "1-sentence viscoelastic damping between double 5/8 drywall note"
    }},
    {{
      "badge": "{sp['corner_bass_traps_count']} Bass Traps & Door Seal",
      "title": "High-Density Corner Bass Traps + Solid-Core Door Acoustic Gasket & Bottom Sweep",
      "price_range": "$79 - $229",
      "amazon_query": "Corner Bass Traps Studio Acoustic Door Seal Kit Automatic Sweep",
      "ac_note": "1-sentence low-frequency axial mode trapping and door seal note"
    }}
  ],
  "acoustician_checklist": [
    "Step 1 regarding Absorption (NRC panels for RT60) vs Soundblocking (STC mass + decoupling)",
    "Step 2 regarding the Mirror Trick for first-reflection wall and ceiling cloud panels",
    "Step 3 regarding 1-to-2 inch air-gap mounting behind 2-inch fiberglass panels",
    "Step 4 regarding straddling all 4 tri-corners with thick bass traps"
  ],
  "faqs": [
    {{"q": "How many 2x4 acoustic panels do I need for {room_name}?", "a": "Exact Sabine equation math: volume, Sabins needed, and panel count."}},
    {{"q": "How many rolls of Mass Loaded Vinyl and tubes of Green Glue do I need?", "a": "Exact wall sq ft, 100-sqft MLV rolls, 4x8 drywall sheets, and Green Glue tubes."}},
    {{"q": "What is the ideal RT60 reverberation time for a podcast studio vs home theater?", "a": "Exact target RT60 ranges (0.25s-0.32s voice, 0.35s-0.40s home theater, 0.45s-0.55s office/restaurant)."}}
  ]
}}
"""

    for model_id in get_active_gemini_model(GEMINI_API_KEY):
        for attempt in range(2):
            try:
                endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={GEMINI_API_KEY}"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.2,
                        "responseMimeType": "application/json"
                    }
                }
                req = urllib.request.Request(
                    endpoint,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=40) as resp:
                    result = json.loads(resp.read().decode("utf-8"))
                    raw_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                    raw_text = re.sub(r"\s*```$", "", raw_text)
                    parsed = json.loads(raw_text)
                    if "specs" in parsed and "hardware_bundle" in parsed:
                        time.sleep(6)
                        return parsed
            except urllib.error.HTTPError as he:
                if he.code == 429:
                    print(f"[RATE-LIMIT] HTTP 429 on {model_id} (attempt {attempt + 1}). Cooling down 20s...")
                    time.sleep(20)
                else:
                    print(f"[WARN] HTTP {he.code} on {model_id} for '{room_name}': {he}")
                    break
            except Exception as e:
                print(f"[WARN] Gemini ({model_id}) notice for '{room_name}': {e}")
                break

    return det_fallback


def build_acoustic_html_page(data, slug, mon_cfg):
    room_name = data.get("room_name", "Room Acoustics & Soundproofing")
    sp = data.get("specs", {})
    len_ft = round(safe_float(sp.get("length_ft", 15.0), 15.0), 1)
    wid_ft = round(safe_float(sp.get("width_ft", 12.0), 12.0), 1)
    hgt_ft = round(safe_float(sp.get("height_ft", 8.0), 8.0), 1)
    vol_cu = int(safe_float(sp.get("room_volume_cuft", 1440), 1440))
    wall_sq = int(safe_float(sp.get("wall_area_sqft", 432), 432))
    un_rt60 = round(safe_float(sp.get("untreated_rt60_sec", 1.38), 1.38), 2)
    tg_rt60 = round(safe_float(sp.get("target_rt60_sec", 0.35), 0.35), 2)
    sabins = round(safe_float(sp.get("additional_sabins_needed", 168.0), 168.0), 1)
    panels = int(safe_float(sp.get("panels_2x4_count", 21), 21))
    traps = int(safe_float(sp.get("corner_bass_traps_count", 4), 4))
    mlv_r = int(safe_float(sp.get("mlv_100sqft_rolls", 5), 5))
    gg_tubes = int(safe_float(sp.get("green_glue_28oz_tubes", 28), 28))

    header_cta = mon_cfg.get("header_cta", {})
    header_cta_url = build_amazon_url(header_cta.get("search_query", "24x48+Acoustic+Panels+Mass+Loaded+Vinyl+Green+Glue"), mon_cfg)

    schema_graph = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "SoftwareApplication",
                "name": f"{room_name} RT60 Reverb, Acoustic Panel & MLV Calculator",
                "applicationCategory": "UtilitiesApplication",
                "operatingSystem": "Web Browser",
                "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}
            },
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": f.get("q", ""),
                        "acceptedAnswer": {"@type": "Answer", "text": f.get("a", "")}
                    } for f in data.get("faqs", [])
                ]
            }
        ]
    }

    bundle_html = ""
    for item in data.get("hardware_bundle", []):
        amz_url = build_amazon_url(item.get("amazon_query", item.get("title", "24x48 Acoustic Panels")), mon_cfg)
        bundle_html += f"""
        <div class="bg-zinc-900 border border-zinc-800 rounded-xl p-5 flex flex-col justify-between hover:border-violet-500/60 transition">
          <div>
            <div class="flex items-center justify-between gap-2 mb-2">
              <span class="text-xs font-bold uppercase tracking-wider bg-violet-500/10 text-violet-400 border border-violet-500/20 px-2.5 py-0.5 rounded">{item.get('badge', 'Studio Acoustics')}</span>
              <span class="text-sm font-bold text-emerald-400">{item.get('price_range', '$89+')}</span>
            </div>
            <h3 class="text-base font-bold text-white mt-2">{item.get('title', '')}</h3>
            <p class="text-xs text-zinc-400 mt-2 leading-relaxed">🎙️ {item.get('ac_note', '')}</p>
          </div>
          <a href="{amz_url}" target="_blank" rel="nofollow sponsored" class="mt-5 block text-center bg-violet-500 hover:bg-violet-400 text-zinc-950 font-extrabold py-2.5 px-4 rounded-lg text-sm transition shadow-lg">
            Check Price on Amazon →
          </a>
        </div>"""

    # Build Room Size vs Sabins, 2x4 Panels, MLV Rolls & Green Glue Matrix Table
    ac_tiers = [
        ("10×10×8 Ft (800 ft³ Booth)", "105 Sabins (@0.30s)", "13 Panels + 4 Traps", "4 Rolls MLV (320 ft²)", "20 Tubes Green Glue"),
        ("12×15×8 Ft (1,440 ft³ Studio)", "168 Sabins (@0.35s)", "20 Panels + 4 Traps", "5 Rolls MLV (432 ft²)", "28 Tubes Green Glue"),
        ("14×18×9 Ft (2,268 ft³ Theater)", "265 Sabins (@0.35s)", "32 Panels + 6 Traps", "6 Rolls MLV (576 ft²)", "36 Tubes Green Glue"),
        ("16×22×9 Ft (3,168 ft³ Media)", "335 Sabins (@0.40s)", "40 Panels + 8 Traps", "7 Rolls MLV (684 ft²)", "44 Tubes Green Glue"),
        ("20×30×10 Ft (6,000 ft³ Office)", "510 Sabins (@0.48s)", "60 Panels / Clouds", "10 Rolls MLV (1,000 ft²)", "64 Tubes Green Glue")
    ]
    matrix_rows_html = ""
    for r_lbl, s_lbl, p_lbl, m_lbl, g_lbl in ac_tiers:
        matrix_rows_html += f"""
        <tr class="border-b border-zinc-800 hover:bg-zinc-800/40">
          <td class="py-3 px-4 font-bold text-white">{r_lbl}</td>
          <td class="py-3 px-4 text-zinc-300">{s_lbl}</td>
          <td class="py-3 px-4 font-bold text-violet-400">{p_lbl}</td>
          <td class="py-3 px-4 text-emerald-400 font-semibold">{m_lbl}</td>
          <td class="py-3 px-4 text-xs text-zinc-300">{g_lbl}</td>
        </tr>"""

    checklist_html = ""
    for idx, step_text in enumerate(data.get("acoustician_checklist", []), start=1):
        checklist_html += f"""
        <label class="flex items-start gap-3.5 bg-zinc-900 border border-zinc-800 rounded-xl p-4 cursor-pointer hover:border-zinc-700 transition">
          <input type="checkbox" class="mt-1 w-5 h-5 accent-violet-500 rounded cursor-pointer ac-check">
          <span class="text-sm text-zinc-200 leading-relaxed"><strong>INCE Step {idx}:</strong> {step_text}</span>
        </label>"""

    faqs_html = "".join([
        f"<div class='bg-zinc-900 border border-zinc-800 rounded-xl p-5'><h3 class='font-bold text-white text-base mb-2'>{f.get('q', '')}</h3><p class='text-sm text-zinc-300 leading-relaxed'>{f.get('a', '')}</p></div>"
        for f in data.get("faqs", [])
    ])

    canonical_url = f"{SITE_BASE_URL}/{slug}.html"
    amz_domain = mon_cfg.get("marketplace_domain", "www.amazon.com")
    amz_tag = mon_cfg.get("amazon_associate_tag", "YOUR_AMAZON_TAG-20")

    html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{data.get('seo_title', room_name)}</title>
  <meta name="description" content="{data.get('meta_description', '')}">
  <link rel="canonical" href="{canonical_url}">
  <meta property="og:title" content="{data.get('seo_title', room_name)}">
  <meta property="og:description" content="{data.get('meta_description', '')}">
  <meta property="og:type" content="article">
  <meta property="og:url" content="{canonical_url}">
  <script src="https://cdn.tailwindcss.com"></script>
  <script type="application/ld+json">{json.dumps(schema_graph)}</script>
</head>
<body class="bg-zinc-950 text-zinc-100 antialiased min-h-screen flex flex-col">
  <header class="border-b border-zinc-800 bg-zinc-900/80 backdrop-blur sticky top-0 z-30">
    <div class="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
      <a href="index.html" class="text-lg font-black tracking-tight text-white flex items-center gap-2">
        <span class="bg-violet-500 text-zinc-950 px-2 py-0.5 rounded font-black">ACOUSTIC</span>SabinIndex
      </a>
      <a href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="text-xs sm:text-sm bg-violet-500 hover:bg-violet-400 text-zinc-950 font-extrabold px-3.5 py-2 rounded-lg transition">
        {header_cta.get('cta_text', 'Shop Acoustic Panels, MLV & Green Glue →')}
      </a>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-10 flex-1 w-full">
    <div class="mb-8">
      <div class="flex flex-wrap items-center gap-2.5 mb-3">
        <span class="text-xs font-extrabold uppercase tracking-widest bg-violet-500 text-zinc-950 px-3 py-1 rounded-full">{panels}× 2'×4' Panels + {traps} Bass Traps</span>
        <span class="text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-3 py-1 rounded-full">RT60: {un_rt60}s → {tg_rt60}s ({sabins:.0f} Sabins)</span>
        <span class="text-xs font-semibold bg-zinc-800 text-zinc-300 px-3 py-1 rounded-full">STC Wall: {mlv_r} Rolls MLV + {gg_tubes} Tubes Green Glue</span>
      </div>
      <h1 class="text-3xl sm:text-4xl font-black text-white leading-tight">{data.get('seo_title', room_name)}</h1>
      <div class="mt-4 bg-zinc-900 border-l-4 border-violet-500 p-4 rounded-r-xl text-sm text-zinc-200 leading-relaxed">
        <strong>Wallace Sabine $RT_{{60}}$ & STC Mass-Law Verdict:</strong> {data.get('sabine_verdict', '')}
      </div>
    </div>

    <!-- INTERACTIVE SABINE RT60 REVERB, 2x4 PANEL, MLV & GREEN GLUE CALCULATOR -->
    <section class="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 sm:p-8 mb-12 shadow-2xl">
      <h2 class="text-xl font-extrabold text-white mb-2">Interactive {room_name} Sabine $RT_{{60}}$, Panel & MLV Calculator</h2>
      <p class="text-xs text-zinc-400 mb-6">Adjust your room dimensions, target reverberation time ($RT_{{60}}$), and absorber material NRC to compute exact Sabins required, 24"×48" acoustic panel count, Mass Loaded Vinyl rolls, and Green Glue tubes.</p>

      <div class="grid md:grid-cols-2 gap-8 items-center">
        <div class="space-y-5">
          <div class="grid grid-cols-3 gap-3">
            <div>
              <div class="flex justify-between text-xs font-medium mb-1">
                <label for="lenSlider" class="text-zinc-300">Length (Ft)</label>
                <span class="text-violet-400 font-bold"><span id="lenVal">{len_ft:g}</span>'</span>
              </div>
              <input id="lenSlider" type="range" min="6" max="50" step="1" value="{int(len_ft)}" class="w-full accent-violet-500 cursor-pointer">
            </div>
            <div>
              <div class="flex justify-between text-xs font-medium mb-1">
                <label for="widSlider" class="text-zinc-300">Width (Ft)</label>
                <span class="text-violet-400 font-bold"><span id="widVal">{wid_ft:g}</span>'</span>
              </div>
              <input id="widSlider" type="range" min="6" max="40" step="1" value="{int(wid_ft)}" class="w-full accent-violet-500 cursor-pointer">
            </div>
            <div>
              <div class="flex justify-between text-xs font-medium mb-1">
                <label for="hgtSlider" class="text-zinc-300">Height (Ft)</label>
                <span class="text-violet-400 font-bold"><span id="hgtVal">{hgt_ft:g}</span>'</span>
              </div>
              <input id="hgtSlider" type="range" min="7" max="16" step="0.5" value="{hgt_ft}" class="w-full accent-violet-500 cursor-pointer">
            </div>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label for="rt60Select" class="block text-xs font-medium text-zinc-400 mb-1">Target Room Reverb ($RT_{{60}}$)</label>
              <select id="rt60Select" class="w-full bg-zinc-950 border border-zinc-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-violet-500">
                <option value="0.28" {"selected" if tg_rt60 <= 0.30 else ""}>0.28 sec (Podcast / Vocal Booth)</option>
                <option value="0.35" {"selected" if 0.30 < tg_rt60 <= 0.37 else ""}>0.35 sec (Mixing / Home Theater)</option>
                <option value="0.42" {"selected" if 0.37 < tg_rt60 <= 0.46 else ""}>0.42 sec (Hi-Fi / Live Music Room)</option>
                <option value="0.52" {"selected" if tg_rt60 > 0.46 else ""}>0.52 sec (Office / Restaurant / Hall)</option>
              </select>
            </div>
            <div>
              <label for="nrcSelect" class="block text-xs font-medium text-zinc-400 mb-1">Panel Material (NRC Rating)</label>
              <select id="nrcSelect" class="w-full bg-zinc-950 border border-zinc-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-violet-500">
                <option value="1.05" selected>2" Fiberglass OC-703 / Rockwool (NRC 1.05)</option>
                <option value="0.90">2" Acoustic Wood Slat + Felt (NRC 0.90)</option>
                <option value="0.65">2" Polyurethane Studio Foam (NRC 0.65)</option>
              </select>
            </div>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div class="bg-zinc-950 border border-violet-500/30 rounded-xl p-4">
            <span class="text-xs uppercase text-violet-400 font-bold">2'×4' Panels & Traps</span>
            <div class="text-2xl sm:text-3xl font-black text-white mt-1"><span id="panelsOut">{panels}</span> <span class="text-xs font-normal text-zinc-400">Panels</span></div>
            <p id="sabinNoteOut" class="text-xs text-violet-400 font-semibold mt-1">+{traps} Corner Traps ({sabins:.0f} Sabins)</p>
          </div>

          <div class="bg-zinc-950 border border-emerald-500/30 rounded-xl p-4">
            <span class="text-xs uppercase text-emerald-400 font-bold">STC Wall Soundproofing</span>
            <div id="mlvOut" class="text-xl sm:text-2xl font-black text-emerald-400 mt-1">{mlv_r} Rolls MLV</div>
            <p id="ggNoteOut" class="text-xs text-zinc-300 font-semibold mt-1">+{gg_tubes} Tubes Green Glue</p>
          </div>
        </div>
      </div>

      <div class="mt-6 bg-violet-950/40 border border-violet-500/30 rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div id="acAdviceBanner" class="text-sm text-violet-100 font-medium"></div>
        <a id="dynamicAcBtn" href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="shrink-0 bg-violet-500 hover:bg-violet-400 text-zinc-950 font-extrabold px-4 py-2.5 rounded-lg text-xs uppercase tracking-wider transition">
          Shop Matched Acoustic Panels & MLV on Amazon →
        </a>
      </div>
    </section>

    <section class="mb-12">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-extrabold text-white">Complete {room_name} Panels, MLV & Green Glue Bundle</h2>
        <span class="text-xs text-zinc-400">ASTM C423 (NRC 1.05) & ASTM E90 (STC 58+) Rated</span>
      </div>
      <div class="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">{bundle_html}</div>
    </section>

    <section class="mb-12">
      <h2 class="text-2xl font-extrabold text-white mb-4">Room Volume, Sabine Absorption Sabins, 2'×4' Panel Count & MLV/Green Glue Chart</h2>
      <div class="overflow-x-auto bg-zinc-900 border border-zinc-800 rounded-xl">
        <table class="w-full text-left border-collapse text-sm">
          <thead>
            <tr class="border-b border-zinc-800 bg-zinc-950/60 text-zinc-400 uppercase text-xs">
              <th class="py-3.5 px-4">Room Size & Volume</th>
              <th class="py-3.5 px-4">Required Sabins</th>
              <th class="py-3.5 px-4 text-violet-400">2'×4' Panels + Traps</th>
              <th class="py-3.5 px-4 text-emerald-400">Mass Loaded Vinyl (100 ft²)</th>
              <th class="py-3.5 px-4">Green Glue (28 oz)</th>
            </tr>
          </thead>
          <tbody>{matrix_rows_html}</tbody>
        </table>
      </div>
    </section>

    <section class="mb-12">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-extrabold text-white">INCE Studio First-Reflection Mirror Trick, Air-Gap & STC Decoupling Checklist</h2>
        <span id="acBadge" class="text-xs font-bold bg-zinc-800 text-violet-400 px-3 py-1 rounded-full">0 / 4 Completed</span>
      </div>
      <div class="space-y-3">{checklist_html}</div>
    </section>

    <section class="mb-12">
      <h2 class="text-2xl font-extrabold text-white mb-5">Frequently Asked Questions ({room_name})</h2>
      <div class="space-y-4">{faqs_html}</div>
    </section>
  </main>

  <footer class="border-t border-zinc-800 py-8 text-center text-xs text-zinc-500 px-4">
    <p>© {datetime.now(timezone.utc).year} AcousticSabinIndex. Independent Wallace Sabine RT60 & STC Soundproofing Engineering Database. As an Amazon Associate, we earn from qualifying purchases.</p>
  </footer>

  <script>
    const amzDomain = "{amz_domain}";
    const amzTag = "{amz_tag}";

    const lenSlider = document.getElementById('lenSlider');
    const widSlider = document.getElementById('widSlider');
    const hgtSlider = document.getElementById('hgtSlider');
    const rt60Select = document.getElementById('rt60Select');
    const nrcSelect = document.getElementById('nrcSelect');
    const lenVal = document.getElementById('lenVal');
    const widVal = document.getElementById('widVal');
    const hgtVal = document.getElementById('hgtVal');
    const panelsOut = document.getElementById('panelsOut');
    const sabinNoteOut = document.getElementById('sabinNoteOut');
    const mlvOut = document.getElementById('mlvOut');
    const ggNoteOut = document.getElementById('ggNoteOut');
    const acAdviceBanner = document.getElementById('acAdviceBanner');
    const dynamicAcBtn = document.getElementById('dynamicAcBtn');

    function recalculateAcoustic() {{
      const lFt = parseFloat(lenSlider.value);
      const wFt = parseFloat(widSlider.value);
      const hFt = parseFloat(hgtSlider.value);
      const targetRt = parseFloat(rt60Select.value);
      const nrc = parseFloat(nrcSelect.value);

      lenVal.textContent = lFt;
      widVal.textContent = wFt;
      hgtVal.textContent = hFt.toFixed(1);

      const floorSqft = lFt * wFt;
      const wallSqft = 2.0 * (lFt + wFt) * hFt;
      const totSurf = (2.0 * floorSqft) + wallSqft;
      const volCuft = lFt * wFt * hFt;

      const baseSabins = totSurf * 0.042;
      const reqSabins = Math.max(28.0, ((0.049 * volCuft) / targetRt) - baseSabins);
      const sabinsPerPanel = 8.0 * nrc;
      const panelCount = Math.max(4, Math.ceil(reqSabins / sabinsPerPanel));
      const trapCount = volCuft <= 1400 ? 4 : (volCuft <= 2600 ? 6 : 8);

      const mlvRolls = Math.max(2, Math.ceil((wallSqft * 1.05) / 100.0));
      const dwSheets = Math.max(6, Math.ceil(wallSqft / 32.0));
      const ggTubes = dwSheets * 2;

      panelsOut.textContent = panelCount;
      sabinNoteOut.textContent = `+${{trapCount}} Corner Traps (${{Math.round(reqSabins)}} Sabins)`;
      mlvOut.textContent = `${{mlvRolls}} Rolls MLV`;
      ggNoteOut.textContent = `+${{ggTubes}} Tubes Green Glue (${{Math.round(wallSqft)}} ft²)`;

      acAdviceBanner.innerHTML = `🎙️ <strong>Sabine & STC Spec:</strong> Dropping your ${{Math.round(volCuft).toLocaleString()}} ft³ room to <strong>${{targetRt}}s RT60</strong> requires <strong>${{panelCount}}× 24"×48" Acoustic Panels</strong> + <strong>${{trapCount}}× Corner Bass Traps</strong> (${{Math.round(reqSabins)}} Sabins). For STC wall isolation, install <strong>${{mlvRolls}} Rolls of Mass Loaded Vinyl</strong> + <strong>${{ggTubes}} Tubes of Green Glue</strong>.`;
      dynamicAcBtn.href = `https://${{amzDomain}}/s?k=24x48x2+Fiberglass+Acoustic+Panels+Mass+Loaded+Vinyl+Green+Glue&tag=${{amzTag}}`;
    }}

    lenSlider.addEventListener('input', recalculateAcoustic);
    widSlider.addEventListener('input', recalculateAcoustic);
    hgtSlider.addEventListener('input', recalculateAcoustic);
    rt60Select.addEventListener('change', recalculateAcoustic);
    nrcSelect.addEventListener('change', recalculateAcoustic);
    recalculateAcoustic();

    const checks = document.querySelectorAll('.ac-check');
    const badge = document.getElementById('acBadge');
    checks.forEach(ch => {{
      ch.addEventListener('change', () => {{
        const done = Array.from(checks).filter(c => c.checked).length;
        badge.textContent = `${{done}} / ${{checks.length}} Completed`;
      }});
    }});
  </script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, f"{slug}.html"), "w", encoding="utf-8") as f:
        f.write(html)


def rebuild_portal_sitemap_and_rss(published, mon_cfg):
    header_cta = mon_cfg.get("header_cta", {})
    header_cta_url = build_amazon_url(header_cta.get("search_query", "24x48+Acoustic+Panels+Mass+Loaded+Vinyl+Green+Glue"), mon_cfg)

    cards_html = ""
    for item in reversed(published):
        cards_html += f"""
        <a href="{item['slug']}.html" class="block bg-zinc-900 border border-zinc-800 hover:border-violet-500/60 rounded-xl p-5 transition group">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-black uppercase bg-violet-500 text-zinc-950 px-2.5 py-0.5 rounded">{item.get('panels', 20)}× 2'×4' Panels ({item.get('sabins', 168)} Sabins)</span>
            <span class="text-xs text-zinc-400">MLV: {item.get('mlv', 5)} Rolls | {item.get('rt60', 0.35)}s RT60</span>
          </div>
          <h2 class="text-base font-bold text-white group-hover:text-violet-400 transition">{item['room_name']}</h2>
          <p class="text-xs text-zinc-400 mt-2 line-clamp-2">{item['description']}</p>
          <span class="inline-block mt-4 text-xs font-extrabold text-violet-400">Calculate RT60, Panels & MLV Rolls →</span>
        </a>"""

    index_html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AcousticSabinIndex — Room RT60 Reverb, Acoustic Panel Count, MLV & Green Glue Calculator (2026)</title>
  <meta name="description" content="Calculate exact room reverberation time (Wallace Sabine RT60 formula), 24x48 fiberglass acoustic panel and corner bass trap counts, Mass Loaded Vinyl (MLV) rolls, and Green Glue tubes for studios, home theaters, offices, and gyms.">
  <link rel="canonical" href="{SITE_BASE_URL}/">
  <link rel="alternate" type="application/rss+xml" title="AcousticSabinIndex RSS Feed" href="{SITE_BASE_URL}/rss.xml">
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-zinc-950 text-zinc-100 min-h-screen flex flex-col">
  <header class="border-b border-zinc-800 bg-zinc-900/80 sticky top-0 z-30 backdrop-blur">
    <div class="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
      <div class="text-lg font-black text-white flex items-center gap-2">
        <span class="bg-violet-500 text-zinc-950 px-2 py-0.5 rounded font-black">ACOUSTIC</span>SabinIndex
      </div>
      <a href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="text-xs sm:text-sm bg-violet-500 hover:bg-violet-400 text-zinc-950 font-extrabold px-3.5 py-2 rounded-lg transition">
        {header_cta.get('cta_text', 'Shop Acoustic Panels, MLV & Green Glue →')}
      </a>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-12 flex-1 w-full">
    <div class="text-center max-w-2xl mx-auto mb-10">
      <h1 class="text-3xl sm:text-5xl font-black text-white tracking-tight">Room Acoustics $RT_{{60}}$, 2'×4' Panel, MLV & Green Glue Database</h1>
      <p class="text-zinc-400 mt-3 text-base sm:text-lg">Select your studio, home theater, or acoustic material below to calculate Wallace Sabine $RT_{{60}}$ absorption Sabins, 24"×48" panel and bass trap quantities, Mass Loaded Vinyl rolls, and Green Glue tubes.</p>
      <div class="mt-6">
        <input id="filterInput" type="text" placeholder="Search room size or material (e.g. 12x15 Studio, Home Theater, Podcast Booth, Owens Corning 703, Mass Loaded Vinyl, Green Glue...)" class="w-full bg-zinc-900 border border-zinc-700 rounded-xl px-4 py-3.5 text-sm text-white focus:outline-none focus:border-violet-500">
      </div>
    </div>

    <div id="acGrid" class="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">{cards_html}</div>
  </main>

  <footer class="border-t border-zinc-800 py-8 text-center text-xs text-zinc-500">
    <p>© {datetime.now(timezone.utc).year} AcousticSabinIndex. As an Amazon Associate, we earn from qualifying purchases.</p>
  </footer>

  <script>
    const filterInput = document.getElementById('filterInput');
    const cards = Array.from(document.getElementById('acGrid').children);
    filterInput.addEventListener('input', (e) => {{
      const q = e.target.value.toLowerCase();
      cards.forEach(c => {{
        c.style.display = c.textContent.toLowerCase().includes(q) ? 'block' : 'none';
      }});
    }});
  </script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    urls_xml = f"""  <url>
    <loc>{SITE_BASE_URL}/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>\n"""

    for item in published:
        urls_xml += f"""  <url>
    <loc>{SITE_BASE_URL}/{item['slug']}.html</loc>
    <lastmod>{item.get('date', today)}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.9</priority>
  </url>\n"""

    with open(os.path.join(DOCS_DIR, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(f"""<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls_xml}</urlset>""")

    rss_items = ""
    for item in list(reversed(published))[:30]:
        rss_items += f"""    <item>
      <title>{item['title']}</title>
      <link>{SITE_BASE_URL}/{item['slug']}.html</link>
      <guid>{SITE_BASE_URL}/{item['slug']}.html</guid>
      <description>{item['description']}</description>
    </item>\n"""

    rss_xml = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>AcousticSabinIndex Room Acoustics RT60 & Soundproofing Database</title>
    <link>{SITE_BASE_URL}/</link>
    <description>Interactive Sabine RT60 Reverb, 2x4 Acoustic Panel, Mass Loaded Vinyl & Green Glue Calculators</description>
    <atom:link href="{SITE_BASE_URL}/rss.xml" rel="self" type="application/rss+xml" />
    <atom:link href="https://pubsubhubbub.appspot.com/" rel="hub" />
{rss_items}  </channel>
</rss>"""

    with open(os.path.join(DOCS_DIR, "rss.xml"), "w", encoding="utf-8") as f:
        f.write(rss_xml)

    with open(os.path.join(DOCS_DIR, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {SITE_BASE_URL}/sitemap.xml\n")

    with open(os.path.join(DOCS_DIR, f"{INDEXNOW_KEY}.txt"), "w", encoding="utf-8") as f:
        f.write(INDEXNOW_KEY)


def notify_search_engines(new_urls):
    """Multi-Endpoint Search Engine Pinger (IndexNow Global + Bing + Google WebSub)."""
    if not SITE_BASE_URL or not new_urls:
        return
    parsed_host = urllib.parse.urlparse(SITE_BASE_URL).netloc
    payload = {
        "host": parsed_host,
        "key": INDEXNOW_KEY,
        "keyLocation": f"{SITE_BASE_URL}/{INDEXNOW_KEY}.txt",
        "urlList": new_urls
    }
    for idx_endpoint in ["https://api.indexnow.org/indexnow", "https://www.bing.com/indexnow"]:
        try:
            req = urllib.request.Request(
                idx_endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json; charset=utf-8"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                print(f"[INDEXNOW] Pushed {len(new_urls)} URLs to {idx_endpoint} (HTTP {resp.status})")
                break
        except Exception as e:
            print(f"[WARN] IndexNow ({idx_endpoint}) notice: {e}")

    try:
        hub_data = urllib.parse.urlencode({
            "hub.mode": "publish",
            "hub.url": f"{SITE_BASE_URL}/rss.xml"
        }).encode("utf-8")
        req_hub = urllib.request.Request(
            "https://pubsubhubbub.appspot.com/",
            data=hub_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST"
        )
        with urllib.request.urlopen(req_hub, timeout=15) as resp_hub:
            print(f"[WEBSUB] Google PubSubHubbub ping status: {resp_hub.status}")
    except Exception as e:
        print(f"[WARN] WebSub ping notice: {e}")


def main():
    published = load_json(PUBLISHED_FILE, [])
    mon_cfg = load_json(MONETIZATION_FILE, {})
    published_slugs = {item["slug"] for item in published if "slug" in item}

    candidates = []
    if CUSTOM_ACOUSTIC:
        candidates.append((CUSTOM_ACOUSTIC.strip(), 15.0, 12.0, 8.0, 0.35, 1.05, "Studio & Home Theater"))
    candidates.extend(SEED_ACOUSTICS)
    candidates.extend(discover_google_acoustic_queries(published_slugs))

    new_urls = []
    count = 0

    for ac_tuple in candidates:
        if count >= PAGES_PER_RUN:
            break
        r_name = ac_tuple[0]
        slug = slugify(f"{r_name}-rt60-panel-mlv-calculator")
        if slug in published_slugs:
            continue

        print(f"[ENGINE] Generating Sabine RT60 acoustic panel & MLV calculator for: {r_name}...")
        try:
            data = generate_acoustic_data(ac_tuple)
            build_acoustic_html_page(data, slug, mon_cfg)
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            sp = data.get("specs", {})

            published.append({
                "room_name": data.get("room_name", r_name),
                "slug": slug,
                "title": data.get("seo_title", f"{r_name} Acoustic Calculator"),
                "description": data.get("meta_description", ""),
                "panels": int(safe_float(sp.get("panels_2x4_count", 20), 20)),
                "sabins": int(safe_float(sp.get("additional_sabins_needed", 168), 168)),
                "mlv": int(safe_float(sp.get("mlv_100sqft_rolls", 5), 5)),
                "rt60": round(safe_float(sp.get("target_rt60_sec", ac_tuple[4]), ac_tuple[4]), 2),
                "date": today
            })
            published_slugs.add(slug)
            if SITE_BASE_URL:
                new_urls.append(f"{SITE_BASE_URL}/{slug}.html")
            count += 1
            if count < PAGES_PER_RUN:
                time.sleep(15)
        except Exception as e:
            print(f"[ERROR] Failed building {r_name}: {e}")

    save_json(PUBLISHED_FILE, published)
    rebuild_portal_sitemap_and_rss(published, mon_cfg)
    if new_urls and SITE_BASE_URL:
        new_urls.append(f"{SITE_BASE_URL}/")
        notify_search_engines(new_urls)
    print(f"[DONE] Published {count} new Sabine RT60 acoustic panel & MLV calculator pages.")


if __name__ == "__main__":
    main()
