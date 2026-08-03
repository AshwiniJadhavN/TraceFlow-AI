"""Tests for the output validators module."""

from __future__ import annotations

import pytest

from validators.output_validators import (
    RISK_MATRIX,
    check_enum,
    correct_fmea_rpn,
    correct_risk_level,
    validate_required_fields,
    VALID_CLASSES,
    VALID_PROBABILITIES,
    VALID_SEVERITIES,
)
from validators.data_privacy import sanitize_for_model


class TestCheckEnum:
    def test_valid_value_passes_through(self):
        assert check_enum("C", VALID_CLASSES, "class") == "C"

    def test_all_valid_classes(self):
        for c in ("A", "B", "C"):
            assert check_enum(c, VALID_CLASSES, "class") == c

    def test_invalid_raises_value_error(self):
        with pytest.raises(ValueError, match="iec_62304_class"):
            check_enum("D", VALID_CLASSES, "iec_62304_class")

    def test_error_message_includes_value(self):
        with pytest.raises(ValueError, match="'X'"):
            check_enum("X", VALID_PROBABILITIES, "probability")

    def test_all_valid_probabilities(self):
        for p in VALID_PROBABILITIES:
            assert check_enum(p, VALID_PROBABILITIES, "p") == p

    def test_all_valid_severities(self):
        for s in VALID_SEVERITIES:
            assert check_enum(s, VALID_SEVERITIES, "s") == s


class TestValidateRequiredFields:
    def test_all_required_fields_present(self):
        validate_required_fields({"a": 1, "b": False}, ("a", "b"), "TestAgent")

    def test_missing_required_field_raises_value_error(self):
        with pytest.raises(ValueError, match="missing required field"):
            validate_required_fields({"a": 1}, ("a", "b"), "TestAgent")

    def test_none_required_field_raises_value_error(self):
        with pytest.raises(ValueError, match="b"):
            validate_required_fields({"a": 1, "b": None}, ("a", "b"), "TestAgent")


class TestDataPrivacy:
    def test_redacts_email_and_patient_identifier(self):
        result = sanitize_for_model(
            "Contact alice@example.com about patient ID PT-12345 requirement."
        )
        assert "alice@example.com" not in result.sanitized_text
        assert "PT-12345" not in result.sanitized_text
        assert result.redactions["email"] == 1
        assert result.redactions["patient_id"] == 1

    def test_blocks_private_key_material(self):
        result = sanitize_for_model("-----BEGIN PRIVATE KEY----- secret")
        assert result.is_blocked
        assert "possible_private_key" in result.blocked_findings


class TestCorrectRiskLevel:
    def test_consistent_value_unchanged(self):
        # Occasional x Catastrophic -> Unacceptable per ISO 14971
        result, corrected = correct_risk_level("Occasional", "Catastrophic", "Unacceptable")
        assert result == "Unacceptable"
        assert corrected is False

    def test_inconsistent_value_auto_corrected(self):
        # Remote x Catastrophic -> High (not Unacceptable)
        result, corrected = correct_risk_level("Remote", "Catastrophic", "Unacceptable")
        assert result == "High"
        assert corrected is True

    def test_improbable_catastrophic_is_medium(self):
        result, _ = correct_risk_level("Improbable", "Catastrophic", "anything")
        assert result == "Medium"

    def test_frequent_negligible_is_medium(self):
        result, _ = correct_risk_level("Frequent", "Negligible", "anything")
        assert result == "Medium"

    def test_unknown_combination_returns_reported(self):
        result, corrected = correct_risk_level("Unknown", "Unknown", "Low")
        assert result == "Low"
        assert corrected is False

    def test_full_matrix_coverage(self):
        """Every cell in RISK_MATRIX should be consistent with itself."""
        for (prob, sev), expected in RISK_MATRIX.items():
            result, corrected = correct_risk_level(prob, sev, expected)
            assert result == expected
            assert corrected is False


class TestCorrectFmeaRpn:
    def test_correct_rpn_unchanged(self):
        data = {
            "severity_score": 8, "occurrence_score": 4, "detectability_score": 6,
            "rpn_before": 192,
            "severity_score_after": 8, "occurrence_score_after": 2, "detectability_score_after": 2,
            "rpn_after": 32,
        }
        result, corrections = correct_fmea_rpn(data)
        assert result["rpn_before"] == 192
        assert result["rpn_after"] == 32
        assert corrections == []

    def test_wrong_rpn_before_is_corrected(self):
        data = {
            "severity_score": 7, "occurrence_score": 4, "detectability_score": 6,
            "rpn_before": 999,   # wrong: should be 168
            "severity_score_after": 7, "occurrence_score_after": 2, "detectability_score_after": 2,
            "rpn_after": 28,
        }
        result, corrections = correct_fmea_rpn(data)
        assert result["rpn_before"] == 168   # 7 * 4 * 6
        assert len(corrections) == 1
        assert "rpn_before" in corrections[0]

    def test_wrong_rpn_after_is_corrected(self):
        data = {
            "severity_score": 7, "occurrence_score": 4, "detectability_score": 6,
            "rpn_before": 168,
            "severity_score_after": 7, "occurrence_score_after": 2, "detectability_score_after": 2,
            "rpn_after": 1,    # wrong: should be 28
        }
        result, corrections = correct_fmea_rpn(data)
        assert result["rpn_after"] == 28
        assert "rpn_after" in corrections[0]

    def test_scores_clamped_to_1_10(self):
        data = {
            "severity_score": 11, "occurrence_score": 0, "detectability_score": 5,
            "rpn_before": 0,  # will be recalculated after clamping
            "severity_score_after": 5, "occurrence_score_after": 1, "detectability_score_after": 1,
            "rpn_after": 5,
        }
        result, corrections = correct_fmea_rpn(data)
        assert result["severity_score"] == 10    # clamped from 11
        assert result["occurrence_score"] == 1   # clamped from 0
        assert result["rpn_before"] == 50         # 10 * 1 * 5

    def test_missing_keys_ignored_gracefully(self):
        # Partial data should not crash
        data = {"severity_score": 5, "occurrence_score": 3}
        result, corrections = correct_fmea_rpn(data)
        assert corrections == []
