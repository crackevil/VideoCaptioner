"""Root-level test configuration and shared fixtures."""

import os

import pytest

from videocaptioner.core.asr.asr_data import ASRData, ASRDataSeg
from videocaptioner.core.utils import cache


@pytest.fixture
def sample_asr_data():
    """Create sample ASR data for testing."""
    segments = [
        ASRDataSeg(start_time=0, end_time=1000, text="I am a student"),
        ASRDataSeg(start_time=1000, end_time=2000, text="You are a teacher"),
        ASRDataSeg(start_time=2000, end_time=3000, text="VideoCaptioner is a tool for captioning videos"),
    ]
    return ASRData(segments)


@pytest.fixture
def check_env_vars():
    """Check if required environment variables are set."""
    def _check(*var_names):
        missing = [var for var in var_names if not os.getenv(var)]
        if missing:
            pytest.skip(f"Required environment variables not set: {', '.join(missing)}")
    return _check