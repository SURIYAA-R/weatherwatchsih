"""
Quick unit tests for the ML pipeline — run without pytest.
Tests: classifier, scorer, deduplication, geo-verification.
"""
import sys
from datetime import datetime, timezone, timedelta

# Add parent path
sys.path.insert(0, '.')

from app.ml.classifier import classify_event, keyword_match_score
from app.ml.scorer import score_report, is_duplicate, AUTO_FLAG_THRESHOLD
from app.ml.imd_stations import geo_temporal_score, haversine_km

PASS = "✓"
FAIL = "✗"

def check(name, condition, detail=""):
    icon = PASS if condition else FAIL
    print(f"  {icon} {name}" + (f" — {detail}" if detail else ""))
    return condition

def main():
    errors = 0
    print("\n══ CLASSIFIER TESTS ══")

    cat, conf = classify_event("heavy flooding in Dharavi, streets submerged")
    errors += 0 if check("Flood detection", cat=="flood", f"got {cat} ({conf:.2f})") else 1

    cat, conf = classify_event("cyclone approaching Gujarat coast with 150 kmph winds")
    errors += 0 if check("Cyclone detection", cat=="cyclone", f"got {cat} ({conf:.2f})") else 1

    cat, conf = classify_event("dense fog on NH-44, visibility near zero metres")
    errors += 0 if check("Fog detection", cat=="fog", f"got {cat} ({conf:.2f})") else 1

    cat, conf = classify_event("temperature above 45 degrees, heatwave scorching conditions")
    errors += 0 if check("Heatwave detection", cat=="heatwave", f"got {cat} ({conf:.2f})") else 1

    cat, conf = classify_event("golf ball sized hailstones, hailstorm destroying crops")
    errors += 0 if check("Hailstorm detection", cat=="hailstorm", f"got {cat} ({conf:.2f})") else 1

    cat, conf = classify_event("something vague with no weather keywords")
    errors += 0 if check("Unknown fallback", cat=="unknown", f"got {cat} ({conf:.2f})") else 1

    print("\n══ SCORER TESTS ══")

    # High-credibility real report
    r = score_report(
        description="Cyclone Biparjoy making landfall near Kutch coast, 150 kmph wind speed",
        event_category="cyclone", latitude=23.059, longitude=70.112,
        account_age_months=120, is_verified_account=True, prior_verified_count=10,
    )
    errors += 0 if check("High-credibility score >= 55", r.credibility_score >= 55, f"score={r.credibility_score:.1f}") else 1
    errors += 0 if check("High-credibility status", r.auto_status in ["published", "pending"], f"status={r.auto_status}") else 1
    errors += 0 if check("Correct classification", r.classified_category == "cyclone", f"got {r.classified_category}") else 1

    # Fake report (Mumbai snow)
    r_fake = score_report(
        description="Snow falling in Mumbai! Unbelievable snowfall on Marine Drive",
        event_category="hailstorm", latitude=19.076, longitude=72.877,
        account_age_months=0, is_verified_account=False, prior_verified_count=0,
    )
    errors += 0 if check("Fake report score < threshold", r_fake.credibility_score < AUTO_FLAG_THRESHOLD,
                          f"score={r_fake.credibility_score:.1f}") else 1
    errors += 0 if check("Fake report auto-flagged", r_fake.auto_status == "flagged", f"status={r_fake.auto_status}") else 1

    # Step 1 breakdown
    bd = r.breakdown()
    s1 = bd["step1_source_credibility"]
    errors += 0 if check("Step1 verified account +15", s1["pts_verified"] == 15.0, f"got {s1['pts_verified']}") else 1
    errors += 0 if check("Step1 age >6mo +10", s1["pts_account_age"] == 10.0, f"got {s1['pts_account_age']}") else 1

    print("\n══ GEO-VERIFICATION TESTS ══")

    # Mumbai flood — Mumbai station should match
    geo = geo_temporal_score(19.076, 72.877, "flood")
    errors += 0 if check("Mumbai flood geo match", geo["event_known_at_station"] == True,
                          f"station={geo['station_name']}") else 1
    errors += 0 if check("Mumbai station nearby", geo["distance_km"] < 50,
                          f"dist={geo['distance_km']:.1f}km") else 1

    # Haversine sanity check (Delhi to Mumbai ~1150 km)
    dist = haversine_km(28.6, 77.2, 19.1, 72.9)
    errors += 0 if check("Haversine Delhi→Mumbai ~1150km", 1000 < dist < 1300, f"got {dist:.0f}km") else 1

    print("\n══ DEDUPLICATION TESTS ══")

    now = datetime.now(timezone.utc)
    # Same location, category, within 1hr → duplicate
    dup = is_duplicate(19.039, 72.855, "flood", now, 19.040, 72.856, "flood", now - timedelta(minutes=30))
    errors += 0 if check("Near-duplicate detected", dup == True) else 1

    # Different category → not duplicate
    not_dup = is_duplicate(19.039, 72.855, "flood", now, 19.040, 72.856, "cyclone", now)
    errors += 0 if check("Different category → not duplicate", not_dup == False) else 1

    # Same category but 200km away → not duplicate
    far = is_duplicate(19.039, 72.855, "flood", now, 21.170, 81.000, "flood", now)
    errors += 0 if check("Far apart → not duplicate", far == False) else 1

    # Same location but >1hr apart → not duplicate
    old = is_duplicate(19.039, 72.855, "flood", now, 19.040, 72.856, "flood", now - timedelta(hours=2))
    errors += 0 if check("Old report → not duplicate", old == False) else 1

    print(f"\n{'─'*40}")
    if errors == 0:
        print(f"  {PASS} All tests passed!")
    else:
        print(f"  {FAIL} {errors} test(s) failed")
    print()
    return errors

if __name__ == "__main__":
    sys.exit(main())
