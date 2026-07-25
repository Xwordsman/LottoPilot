from pathlib import Path
import re

ROOT = Path(r"E:/AI/Kaifa/Github/LottoPilot/backend")

fixes = {
    "app/core/security.py": [
        ("from base64 import urlsafe_b64decode, urlsafe_b64encode", "from base64 import urlsafe_b64encode"),
        ("from base64 import urlsafe_b64encode, urlsafe_b64decode", "from base64 import urlsafe_b64encode"),
    ],
    "app/models/system.py": [
        ("from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func",
         "from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func"),
        ("from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func\n",
         "from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func\n"),
    ],
    "app/services/analytics.py": [
        ("from collections import defaultdict\n", ""),
        ("from collections import Counter, defaultdict\n", "from collections import Counter\n"),
    ],
    "app/services/backtest.py": [
        ("from app.models.system import Job\n", ""),
    ],
    "app/services/ai/client.py": [
        ("from app.services.ai.rerank import apply_ai_rerank\n", ""),
    ],
    "app/services/ai/rerank_pipeline.py": [
        ("from uuid import UUID\n", ""),
    ],
    "app/services/ingestion/import_csv.py": [
        ("from sqlalchemy.orm import Session\n", ""),
        ("from sqlalchemy.orm import Session  # type: ignore\n", ""),
    ],
    "app/services/recommendation/candidates.py": [
        ("import itertools\n", ""),
        ("import math\n", ""),
    ],
    "app/services/recommendation/engine.py": [
        ("from typing import Any\n", ""),
        ("from app.models.system import Job\n", ""),
    ],
    "app/services/recommendation/evaluate.py": [
        ("from app.services.recommendation.prize_rules import evaluate_ticket_against_draw, map_prize_level\n",
         "from app.services.recommendation.prize_rules import evaluate_ticket_against_draw\n"),
        ("map_prize_level, evaluate_ticket_against_draw", "evaluate_ticket_against_draw"),
    ],
    "app/services/recommendation/scoring.py": [
        ("from app.services.recommendation.features import historical_structure_baselines\n", ""),
        ("from app.services.recommendation.features import (\n    historical_structure_baselines,\n",
         "from app.services.recommendation.features import (\n"),
    ],
    "app/api/v1/settings.py": [
        ("from pydantic import BaseModel, Field\n", ""),
        ("from pydantic import BaseModel, Field, EmailStr\n", "from pydantic import EmailStr\n"),
    ],
}

# Read actual files and fix more carefully
for rel, pairs in fixes.items():
    p = ROOT / rel
    if not p.exists():
        print("missing", rel)
        continue
    t = p.read_text(encoding="utf-8")
    orig = t
    for a, b in pairs:
        if a in t:
            t = t.replace(a, b, 1)
            print("fixed", rel, "->", a[:50])
    if t == orig:
        # show import lines for manual
        print("NO_MATCH", rel)
        for i, line in enumerate(t.splitlines(), 1):
            if line.startswith("import ") or line.startswith("from "):
                print(f"  {i}: {line}")
    else:
        p.write_text(t, encoding="utf-8")

# Special-case files with multi-line imports - inspect content
for rel in [
    "app/core/security.py",
    "app/models/system.py",
    "app/services/analytics.py",
    "app/services/backtest.py",
    "app/services/ai/client.py",
    "app/services/ai/rerank_pipeline.py",
    "app/services/ingestion/import_csv.py",
    "app/services/recommendation/candidates.py",
    "app/services/recommendation/engine.py",
    "app/services/recommendation/evaluate.py",
    "app/services/recommendation/scoring.py",
    "app/api/v1/settings.py",
]:
    p = ROOT / rel
    print("====", rel)
    for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        if line.startswith("import ") or line.startswith("from ") or (line.strip().startswith("(") is False and "import" in line and i < 40):
            if line.startswith("import ") or line.startswith("from ") or line.strip().endswith(",") or line.strip().startswith(")"):
                if "import" in line or line.strip() in {")", "),"} or line.strip().endswith(","):
                    print(f"{i}: {line}")
