"""Part B: IsolationForest + rule-based threat detection."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

from backend.security_events import SecurityEventLog


@dataclass
class ThreatAssessment:
    tx_id: str
    threat_level: str  # LOW | MEDIUM | HIGH
    confidence: float
    reason: str
    is_high_alert: bool = False


class ThreatDetector:
    ML_MAP = {-1: "HIGH", 1: "LOW"}
    LEVEL_RANK = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}

    def __init__(self, security_log: SecurityEventLog) -> None:
        self.security_log = security_log
        self.assessments: list[ThreatAssessment] = []
        self.high_alerts: list[ThreatAssessment] = []
        self.training_size = 0
        self.model_accuracy = 0.0

    def _rule_based_level(self, row: dict[str, Any]) -> str:
        if row["failed_logins"] > 2 or row["doc_tamper_flag"] == 1:
            return "HIGH"
        if row["verification_attempts"] > 3:
            return "MEDIUM"
        return "LOW"

    def _higher_level(self, a: str, b: str) -> str:
        return a if self.LEVEL_RANK[a] >= self.LEVEL_RANK[b] else b

    def _augment_synthetic(self, rows: list[dict[str, Any]], min_size: int = 20) -> list[dict[str, Any]]:
        augmented = list(rows)
        random.seed(42)
        while len(augmented) < min_size:
            augmented.append({
                "event_type": "synthetic_verify",
                "actor_wallet": f"0x{random.randint(0, 2**160 - 1):040x}",
                "failed_logins": random.randint(0, 4),
                "verification_attempts": random.randint(0, 6),
                "doc_tamper_flag": random.choice([0, 0, 0, 1]),
                "time_gap_sec": random.uniform(0, 500),
                "wallet_age_blocks": random.randint(1, 5000),
            })
        return augmented

    def train_and_classify(self, tx_ids: list[str]) -> list[ThreatAssessment]:
        rows = self.security_log.to_feature_rows()
        rows = self._augment_synthetic(rows, 20)
        self.training_size = len(rows)

        features = np.array([
            [r["failed_logins"], r["verification_attempts"], r["doc_tamper_flag"],
             r["time_gap_sec"], r["wallet_age_blocks"]]
            for r in rows
        ])

        labels = np.array([1 if self._rule_based_level(r) == "LOW" else -1 for r in rows])
        if len(features) >= 4:
            X_train, X_test, y_train, y_test = train_test_split(
                features, labels, test_size=0.25, random_state=42
            )
            model = IsolationForest(contamination=0.15, random_state=42)
            model.fit(X_train)
            preds = model.predict(X_test)
            self.model_accuracy = round(accuracy_score(y_test, preds) * 100, 2)
            ml_model = model
        else:
            ml_model = IsolationForest(contamination=0.15, random_state=42)
            ml_model.fit(features)
            self.model_accuracy = 100.0

        real_rows = self.security_log.to_feature_rows()
        for i, row in enumerate(real_rows):
            tx_id = tx_ids[i] if i < len(tx_ids) else f"SEC-{i+1:03d}"
            feat = np.array([[
                row["failed_logins"], row["verification_attempts"], row["doc_tamper_flag"],
                row["time_gap_sec"], row["wallet_age_blocks"],
            ]])
            ml_pred = ml_model.predict(feat)[0]
            ml_level = self.ML_MAP.get(ml_pred, "MEDIUM")
            rule_level = self._rule_based_level(row)
            final_level = self._higher_level(ml_level, rule_level)
            score = min(1.0, max(0.0, (
                row["failed_logins"] * 0.15
                + row["verification_attempts"] * 0.1
                + row["doc_tamper_flag"] * 0.5
                + (0.2 if final_level == "HIGH" else 0.05)
            )))
            reason = (
                f"failed_logins={row['failed_logins']}, "
                f"verify_attempts={row['verification_attempts']}, "
                f"tamper={row['doc_tamper_flag']}, "
                f"ML={ml_level}, rule={rule_level}"
            )
            assessment = ThreatAssessment(
                tx_id=tx_id,
                threat_level=final_level,
                confidence=round(score, 2),
                reason=reason,
                is_high_alert=final_level == "HIGH",
            )
            self.assessments.append(assessment)
            if assessment.is_high_alert:
                self.high_alerts.append(assessment)

        return self.assessments
