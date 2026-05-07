#!/usr/bin/env python3
"""
RQ5: Cross-Domain Reuse Patterns
=================================
Analyze role distribution and reuse patterns across task domains.

Output:
  output_v2/rq5_domain_roles.csv
  output_v2/rq5_domain_concentration.csv
  output_v2/rq5_domain_hidden_roots.csv
"""
import os
import pandas as pd
import numpy as np

OUT_DIR = os.environ.get("MODELRANK_OUT_DIR", "output_v2")
DATA_DIR = os.environ.get("MODELRANK_DATA_DIR", "data_new/monthly")

# Domain mapping from pipeline_tag
DOMAIN_MAP = {
    # NLP
    "text-generation": "NLP", "text-classification": "NLP",
    "token-classification": "NLP", "question-answering": "NLP",
    "fill-mask": "NLP", "summarization": "NLP", "translation": "NLP",
    "text2text-generation": "NLP", "sentence-similarity": "NLP",
    "feature-extraction": "NLP", "zero-shot-classification": "NLP",
    "table-question-answering": "NLP", "text-ranking": "NLP",
    # CV
    "image-classification": "CV", "object-detection": "CV",
    "image-segmentation": "CV", "text-to-image": "CV",
    "image-to-image": "CV", "depth-estimation": "CV",
    "unconditional-image-generation": "CV", "image-to-text": "CV",
    "zero-shot-image-classification": "CV", "mask-generation": "CV",
    "zero-shot-object-detection": "CV", "image-feature-extraction": "CV",
    "keypoint-detection": "CV", "video-classification": "CV",
    "text-to-video": "CV", "image-to-video": "CV",
    # Multimodal
    "image-text-to-text": "Multimodal", "visual-question-answering": "Multimodal",
    "document-question-answering": "Multimodal", "video-text-to-text": "Multimodal",
    # Audio
    "automatic-speech-recognition": "Audio", "text-to-speech": "Audio",
    "audio-classification": "Audio", "audio-to-audio": "Audio",
    "text-to-audio": "Audio", "voice-activity-detection": "Audio",
    # RL/Robotics
    "reinforcement-learning": "RL/Robotics", "robotics": "RL/Robotics",
}

print("Loading data ...")
models = pd.read_csv(os.path.join(DATA_DIR, "deriv_models.csv"),
                     usecols=["id", "pipeline_tag"])
scores = pd.read_csv(os.path.join(OUT_DIR, "modelrank_scores.csv"))
scores = scores[scores["month"] == "2026-02"].copy()

# Map pipeline_tag to domain
models["domain"] = models["pipeline_tag"].map(DOMAIN_MAP)
scores = scores.merge(models[["id", "domain"]], left_on="model_id", right_on="id", how="left")

# Assign roles (P90)
dl_t = scores["downloads"].quantile(0.90)
mr_t = scores["score_normalized"].quantile(0.90)

def assign_role(row):
    high_dl = row["downloads"] >= dl_t
    high_mr = row["score_normalized"] >= mr_t
    if high_dl and high_mr: return "PR"
    elif high_dl: return "PL"
    elif high_mr: return "HR"
    else: return "LT"

scores["role"] = scores.apply(assign_role, axis=1)

# Filter to models with domain
scored_with_domain = scores[scores["domain"].notna()]
print(f"Models with domain: {len(scored_with_domain):,} / {len(scores):,} "
      f"({len(scored_with_domain)/len(scores)*100:.1f}%)")

# ── 1. Domain-level role distribution ──
print("\n=== 1. Domain Role Distribution ===")
domain_rows = []
for domain in ["NLP", "CV", "Multimodal", "Audio", "RL/Robotics"]:
    sub = scored_with_domain[scored_with_domain["domain"] == domain]
    if len(sub) == 0:
        continue
    counts = sub["role"].value_counts()
    total = len(sub)
    domain_rows.append({
        "domain": domain,
        "total": total,
        "PR": counts.get("PR", 0),
        "PL": counts.get("PL", 0),
        "HR": counts.get("HR", 0),
        "LT": counts.get("LT", 0),
        "PR_pct": counts.get("PR", 0) / total * 100,
        "PL_pct": counts.get("PL", 0) / total * 100,
        "HR_pct": counts.get("HR", 0) / total * 100,
        "LT_pct": counts.get("LT", 0) / total * 100,
    })

domain_df = pd.DataFrame(domain_rows)
domain_df.to_csv(os.path.join(OUT_DIR, "rq5_domain_roles.csv"), index=False)
print(domain_df[["domain", "total", "PR_pct", "PL_pct", "HR_pct", "LT_pct"]].to_string(index=False, float_format="%.1f"))

# ── 2. Domain concentration (Gini) ──
print("\n=== 2. Domain Concentration ===")
def gini(values):
    v = np.sort(np.array(values, dtype=float))
    n = len(v)
    if n == 0 or v.sum() == 0: return 0.0
    idx = np.arange(1, n + 1)
    return (2 * np.sum(idx * v) - (n + 1) * v.sum()) / (n * v.sum())

conc_rows = []
for domain in ["NLP", "CV", "Multimodal", "Audio", "RL/Robotics"]:
    sub = scored_with_domain[scored_with_domain["domain"] == domain]
    if len(sub) == 0:
        continue
    mr_scores = sub["score_normalized"].values
    g = gini(mr_scores)
    top10_share = sub.nlargest(10, "score_normalized")["score_normalized"].sum() / mr_scores.sum() * 100
    active_derivs = (sub["n_derivatives"] > 0).sum()
    conc_rows.append({
        "domain": domain,
        "models": len(sub),
        "gini": round(g, 3),
        "top10_score_share": round(top10_share, 1),
        "pct_with_derivs": round(active_derivs / len(sub) * 100, 1),
    })

conc_df = pd.DataFrame(conc_rows)
conc_df.to_csv(os.path.join(OUT_DIR, "rq5_domain_concentration.csv"), index=False)
print(conc_df.to_string(index=False))

# ── 3. Top Hidden Roots per domain ──
print("\n=== 3. Top Hidden Roots per Domain ===")
hr_rows = []
for domain in ["NLP", "CV", "Multimodal", "Audio", "RL/Robotics"]:
    sub = scored_with_domain[(scored_with_domain["domain"] == domain) &
                              (scored_with_domain["role"] == "HR")]
    top5 = sub.nlargest(5, "score_normalized")
    print(f"\n  {domain} ({len(sub)} Hidden Roots):")
    for _, r in top5.iterrows():
        print(f"    Rank {int(r['rank']):>5}: {r['model_id'][:55]:<55} "
              f"dl={int(r['downloads']):>8,} derivs={int(r['n_derivatives'])}")
        hr_rows.append({
            "domain": domain, "model_id": r["model_id"],
            "rank": int(r["rank"]), "downloads": int(r["downloads"]),
            "n_derivatives": int(r["n_derivatives"]),
            "score": round(r["score_normalized"], 2),
        })

pd.DataFrame(hr_rows).to_csv(os.path.join(OUT_DIR, "rq5_domain_hidden_roots.csv"), index=False)
print("\nDone.")
