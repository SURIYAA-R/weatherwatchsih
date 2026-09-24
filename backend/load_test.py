"""
Section 4 — Load test: reports/sec vs latency benchmark.

Run:  python load_test.py
Produces: load_test_results.json + prints a table of sustained RPS / latency.

Does NOT require the API to be running — tests the ML pipeline in-process.
"""
import time
import json
import statistics
from app.ml.scorer import score_report

SAMPLE_INPUTS = [
    dict(description="Heavy flooding in Dharavi, streets submerged", event_category="flood",
         latitude=19.039, longitude=72.855),
    dict(description="Cyclone approaching Kutch coast, wind speeds 150 kmph", event_category="cyclone",
         latitude=23.059, longitude=70.112),
    dict(description="Dense fog on NH-44, visibility near zero", event_category="fog",
         latitude=29.389, longitude=76.969),
    dict(description="Heatwave in Churu, temperature 49 degrees Celsius", event_category="heatwave",
         latitude=28.296, longitude=74.969),
    dict(description="Thunderstorm with lightning hitting Bengaluru, gusty winds", event_category="thunderstorm",
         latitude=12.934, longitude=77.626),
]

def run_batch(n_reports: int) -> tuple[float, float]:
    """Scores n_reports and returns (duration_sec, avg_latency_ms)."""
    latencies = []
    for i in range(n_reports):
        inp = SAMPLE_INPUTS[i % len(SAMPLE_INPUTS)]
        t0 = time.perf_counter()
        score_report(**inp)
        latencies.append((time.perf_counter() - t0) * 1000)
    total = sum(latencies) / 1000  # seconds
    return total, statistics.mean(latencies)

def main():
    results = []
    print(f"\n{'Reports':>10} {'Duration(s)':>12} {'RPS':>8} {'Avg ms':>10} {'p95 ms':>10}")
    print("-" * 56)

    for n in [10, 50, 100, 500, 1000, 5000]:
        latencies = []
        t_start = time.perf_counter()
        for i in range(n):
            inp = SAMPLE_INPUTS[i % len(SAMPLE_INPUTS)]
            t0 = time.perf_counter()
            score_report(**inp)
            latencies.append((time.perf_counter() - t0) * 1000)
        dur = time.perf_counter() - t_start
        rps = n / dur
        avg_ms = statistics.mean(latencies)
        p95_ms = sorted(latencies)[int(len(latencies) * 0.95)]
        print(f"{n:>10} {dur:>12.3f} {rps:>8.1f} {avg_ms:>10.3f} {p95_ms:>10.3f}")
        results.append({"n": n, "duration_s": round(dur,4), "rps": round(rps,1), "avg_ms": round(avg_ms,4), "p95_ms": round(p95_ms,4)})

    with open("load_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nResults saved to load_test_results.json")
    print(f"\nPeak sustained RPS: {max(r['rps'] for r in results):.0f}")
    print(f"Average latency (all runs): {statistics.mean(r['avg_ms'] for r in results):.2f} ms per report")

if __name__ == "__main__":
    main()
