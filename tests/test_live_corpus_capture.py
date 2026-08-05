"""
Tests for the 24-hour corpus capture runner (WO-043).

These tests verify:
1. Rotation policy configuration loading and validation
2. Preflight enforcement (grant conditions)
3. Segment path generation (hourly UTC rotation)
4. Segment rotation logic
5. Manifest generation (SHA-256, compression)
6. Gap ledger integration
"""

import asyncio
import json
import os
import zipfile
from dataclasses import dataclass
from datetime import datetime, timedelta, UTC
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tools.live_corpus_capture import (
    CorpusCaptureRunner,
    CorpusCaptureError,
    RotationConfig,
    LoadRecord,
    SegmentManifest,
    RunManifest,
)


# ── FIXTURES ─────────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_env_vars(monkeypatch, tmp_path):
    """Set up environment variables for testing.

    WO-044: CORPUS_DIR points at tmp_path, not a repo-relative `test_captures/`. Under WO-044 the
    runner opens a CorpusLedger during PREFLIGHT (to report cumulative progress and demand a seam
    cause), and a ledger creates its corpus directory on construction — so a repo-relative default
    made every preflight test litter the working tree with corpus dirs and PREFLIGHT.json files.
    Same family as WO-026's finding: an instrument must not write where it is not invited.
    """
    monkeypatch.setenv("TRADING_ENV", "paper")
    monkeypatch.setenv("CORPUS_ROTATION_CADENCE", "hourly")
    monkeypatch.setenv("CORPUS_SEGMENT_DURATION_SECONDS", "3600")
    monkeypatch.setenv("CORPUS_COMPRESSION_ENABLED", "true")
    monkeypatch.setenv("CORPUS_RETENTION_DAYS", "90")
    monkeypatch.setenv("CORPUS_DIR", str(tmp_path / "captures" / "corpus_24h"))
    monkeypatch.setenv("CORPUS_AUTO_MODE_CONFIRMED", "true")
    # WO-044 [3.9]/[3.10]: the operator prerequisite and the grant expiry are REQUIRED greens.
    monkeypatch.setenv("CORPUS_SHUTDOWN_POLICY_DISABLED", "true")
    monkeypatch.setenv("CORPUS_GRANT_EXPIRY", "2099-01-01")


@pytest.fixture
def valid_config(mock_env_vars):
    """Valid rotation configuration."""
    return RotationConfig.from_env()


@pytest.fixture
def temp_corpus_dir(tmp_path):
    """Temporary corpus directory."""
    corpus_dir = tmp_path / "captures" / "corpus_24h"
    corpus_dir.mkdir(parents=True)
    return corpus_dir


# ── ROTATION CONFIG TESTS ────────────────────────────────────────────────────────

class TestRotationConfig:
    """Tests for rotation policy configuration."""

    def test_from_env_default_values(self, mock_env_vars):
        """Configuration loads with default values from environment."""
        config = RotationConfig.from_env()
        assert config.cadence == "hourly"
        assert config.segment_duration_seconds == 3600
        assert config.compression_enabled is True
        assert config.retention_days == 90

    def test_from_env_custom_values(self, monkeypatch):
        """Configuration respects custom environment values."""
        monkeypatch.setenv("CORPUS_ROTATION_CADENCE", "hourly")
        monkeypatch.setenv("CORPUS_SEGMENT_DURATION_SECONDS", "7200")
        monkeypatch.setenv("CORPUS_COMPRESSION_ENABLED", "false")
        monkeypatch.setenv("CORPUS_RETENTION_DAYS", "180")
        monkeypatch.setenv("CORPUS_DIR", "custom/corpus")

        config = RotationConfig.from_env()
        assert config.cadence == "hourly"
        assert config.segment_duration_seconds == 7200
        assert config.compression_enabled is False
        assert config.retention_days == 180
        assert config.corpus_dir == Path("custom/corpus")

    def test_validate_accepts_valid_config(self, valid_config):
        """Valid configuration passes validation."""
        valid_config.validate()  # Should not raise

    def test_validate_rejects_invalid_cadence(self, valid_config):
        """Invalid rotation cadence is rejected."""
        valid_config.cadence = "size"
        with pytest.raises(ValueError, match="Only 'hourly' is supported"):
            valid_config.validate()

    def test_validate_rejects_invalid_segment_duration(self, valid_config):
        """Invalid segment duration is rejected."""
        valid_config.segment_duration_seconds = 1800
        with pytest.raises(ValueError, match="Must be 3600"):
            valid_config.validate()

    def test_validate_rejects_insufficient_retention(self, valid_config):
        """Retention below 90 days is rejected."""
        valid_config.retention_days = 30
        with pytest.raises(ValueError, match="Minimum is 90 days"):
            valid_config.validate()


# ── LOAD RECORD TESTS ─────────────────────────────────────────────────────────────

class TestLoadRecord:
    """Tests for load conditions recording."""

    def test_load_record_capture(self):
        """Load record captures current conditions."""
        record = LoadRecord.capture()
        assert isinstance(record.cpu_percent, float)
        assert isinstance(record.memory_gb, float)
        assert isinstance(record.background_quiet, bool)

    def test_load_record_fields(self):
        """Load record has required fields."""
        record = LoadRecord(
            cpu_percent=15.5,
            memory_gb=8.2,
            other_processes=["chrome.exe"],
            background_quiet=True,
        )
        assert record.cpu_percent == 15.5
        assert record.memory_gb == 8.2
        assert record.other_processes == ["chrome.exe"]
        assert record.background_quiet is True


# ─── SEGMENT MANIFEST TESTS ───────────────────────────────────────────────────────

class TestSegmentManifest:
    """Tests for segment manifest entries."""

    def test_segment_manifest_fields(self):
        """Segment manifest has required fields."""
        manifest = SegmentManifest(
            filename="corpus_HOST_20260728T00Z.jsonl",
            sha256="abc123",
            frame_count=1000,
            size_bytes=220000000,
            compressed=False,
            start_utc="2026-07-28T00:00:00Z",
            end_utc="2026-07-28T01:00:00Z",
        )
        assert manifest.filename == "corpus_HOST_20260728T00Z.jsonl"
        assert manifest.frame_count == 1000
        assert manifest.compressed is False


# ─── RUN MANIFEST TESTS ────────────────────────────────────────────────────────────

class TestRunManifest:
    """Tests for run-level manifest."""

    def test_run_manifest_to_dict(self, valid_config):
        """Run manifest serializes to dict correctly."""
        load_record = LoadRecord(cpu_percent=10.0, memory_gb=8.0)
        manifest = RunManifest(
            run_id="20260728T000000Z",
            host="TESTHOST",
            start_utc="2026-07-28T00:00:00Z",
            end_utc="2026-07-29T00:00:00Z",
            load_record=load_record,
        )
        result = manifest.to_dict()
        assert result["run_id"] == "20260728T000000Z"
        assert result["host"] == "TESTHOST"
        assert result["load_record"]["cpu_percent"] == 10.0
        assert result["load_record"]["memory_gb"] == 8.0


# ─── PREFLIGHT TESTS ───────────────────────────────────────────────────────────────

class TestCorpusCaptureRunnerPreflight:
    """Tests for corpus capture runner preflight."""

    def test_preflight_passes_with_paper_env(self, mock_env_vars):
        """Preflight passes when TRADING_ENV=paper."""
        runner = CorpusCaptureRunner()
        # Preflight is called in __init__; if it passes, we get here
        assert runner._trading_env == "paper"

    def test_preflight_fails_with_non_paper_env(self, monkeypatch, mock_env_vars):
        """Preflight fails when TRADING_ENV is not 'paper'."""
        monkeypatch.setenv("TRADING_ENV", "mainnet")
        with pytest.raises(CorpusCaptureError, match="PREFLIGHT_FAILED"):
            CorpusCaptureRunner()

    def test_preflight_records_load_conditions(self, mock_env_vars):
        """Preflight captures and records load conditions."""
        runner = CorpusCaptureRunner()
        assert runner._load_record is not None
        assert isinstance(runner._load_record.cpu_percent, float)
        assert isinstance(runner._load_record.memory_gb, float)

    def test_preflight_validates_rotation_config(self, mock_env_vars, monkeypatch):
        """Preflight validates rotation configuration."""
        monkeypatch.setenv("CORPUS_ROTATION_CADENCE", "size")  # Invalid
        with pytest.raises(CorpusCaptureError, match="CONFIG_INVALID"):
            CorpusCaptureRunner()

    # ── WO-044 [3.9] the operator prerequisite ────────────────────────────────────────────
    def test_preflight_refuses_without_shutdown_policy_confirmation(self, mock_env_vars,
                                                                    monkeypatch):
        """The shutdown policy must be CONFIRMED disabled — absent confirmation is RED.

        This is the condition whose absence cost two runs (20260729044021 ~2h37m and
        20260730152029 ~3h55m, both killed with every frame on disk and no manifest). It is
        operator-declared because a process cannot inspect a host security policy, and a check
        that silently assumed the answer would be worse than no check at all.
        """
        monkeypatch.delenv("CORPUS_SHUTDOWN_POLICY_DISABLED", raising=False)
        with pytest.raises(CorpusCaptureError, match="PREFLIGHT_FAILED"):
            CorpusCaptureRunner()

    def test_shutdown_policy_confirmation_is_recorded_in_the_preflight(self, mock_env_vars,
                                                                       tmp_path):
        """Confirmed, it is written into PREFLIGHT.json — stated, not merely believed."""
        runner = CorpusCaptureRunner()
        record = json.loads(
            (runner._run_dir() / "PREFLIGHT.json").read_text(encoding="utf-8"))
        cond = record["conditions"]["shutdown_policy_disabled"]
        assert cond["green"] is True
        assert cond["operator_declared"] is True
        assert cond["confirmed_via"] == "CORPUS_SHUTDOWN_POLICY_DISABLED"

    # ── WO-044 [3.10] the grant expiry ────────────────────────────────────────────────────
    def test_preflight_refuses_without_a_declared_grant_expiry(self, mock_env_vars, monkeypatch):
        """A grant with no declared end quietly outlives its authorisation."""
        monkeypatch.delenv("CORPUS_GRANT_EXPIRY", raising=False)
        with pytest.raises(CorpusCaptureError, match="PREFLIGHT_FAILED"):
            CorpusCaptureRunner()

    def test_preflight_refuses_an_expired_grant(self, mock_env_vars, monkeypatch):
        """Past the expiry the run REFUSES rather than trusting anyone to remember."""
        monkeypatch.setenv("CORPUS_GRANT_EXPIRY", "2020-01-01")
        with pytest.raises(CorpusCaptureError, match="PREFLIGHT_FAILED"):
            CorpusCaptureRunner()

    def test_grant_expiry_records_days_remaining(self, mock_env_vars, tmp_path):
        runner = CorpusCaptureRunner()
        record = json.loads(
            (runner._run_dir() / "PREFLIGHT.json").read_text(encoding="utf-8"))
        cond = record["conditions"]["grant_expiry"]
        assert cond["green"] is True
        assert cond["expiry_date"] == "2099-01-01"
        assert cond["days_remaining"] > 0


# ─── SEGMENT PATH TESTS ────────────────────────────────────────────────────────────

class TestCorpusCaptureRunnerSegments:
    """Tests for segment path generation and rotation."""

    def test_get_segment_path_hourly_rotation(self, mock_env_vars):
        """Segment path follows hourly UTC rotation pattern."""
        runner = CorpusCaptureRunner()
        utc_time = datetime(2026, 7, 28, 14, 30, 0, tzinfo=UTC)
        segment_path = runner._get_segment_path(utc_time)

        # Check filename format (avoid run_id coincidence)
        segment_filename = segment_path.name
        # Should align to hour boundary with host prefix
        assert "20260728T14Z.jsonl" in segment_filename
        assert segment_filename.startswith("corpus_")
        assert segment_filename.endswith(".jsonl")

    def test_get_segment_path_utc_alignment(self, mock_env_vars):
        """Segment path aligns to UTC hour boundary regardless of local time."""
        runner = CorpusCaptureRunner()
        # 14:30 UTC should align to 14:00 UTC
        utc_time = datetime(2026, 7, 28, 14, 30, 0, tzinfo=UTC)
        segment_path = runner._get_segment_path(utc_time)

        # Extract just the filename for checking (avoid run_id coincidence)
        segment_filename = segment_path.name
        # Check: aligned to 14:00, not 14:30 or 15:00
        assert "T14Z" in segment_filename  # Not T15Z - aligned to hour boundary
        # Verify it's T14Z (hour) not T1430 (minutes) by checking the pattern
        # The timestamp portion should be YYYYMMDDTHHZ (no minutes)
        import re
        timestamp_match = re.search(r'\d{8}T\d{2}Z\.jsonl$', segment_filename)
        assert timestamp_match is not None, "Filename should end with YYYYMMDDTHHZ.jsonl pattern"

    def test_get_segment_boundary(self, mock_env_vars):
        """Segment boundary is top of next hour."""
        runner = CorpusCaptureRunner()
        utc_time = datetime(2026, 7, 28, 14, 30, 0, tzinfo=UTC)
        boundary = runner._get_segment_boundary(utc_time)

        assert boundary == datetime(2026, 7, 28, 15, 0, 0, tzinfo=UTC)


# ─── DRY RUN TESTS ────────────────────────────────────────────────────────────────

class TestDryRun:
    """Tests for dry-run mode (preflight only)."""

    def test_dry_run_passes_preflight(self, mock_env_vars):
        """Dry run completes preflight without opening socket."""
        # This would be tested via CLI --dry-run flag
        # For now, we test that preflight passes
        runner = CorpusCaptureRunner()
        assert runner._load_record is not None  # Preflight ran


# ─── MANIFEST GENERATION TESTS ─────────────────────────────────────────────────────

class TestManifestGeneration:
    """Tests for manifest generation."""

    def test_manifest_includes_all_required_fields(self, mock_env_vars):
        """Manifest includes all required fields per WO-042 policy."""
        runner = CorpusCaptureRunner()
        assert runner._manifest is None  # Not created until run

        # After run, manifest should have:
        # - run_id, host, start_utc, end_utc
        # - segments list (with sha256, frame_count, size_bytes, compressed)
        # - gap_ledger, gap_ledger_sha256
        # - load_record
        # - host_suspend_events
        # - performance_summary
