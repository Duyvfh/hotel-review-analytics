"""Unit and integration tests for analyzer.py and Boutique HotelReviewAgent."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pandas as pd
SRC_DIR = Path(__file__).parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from analyzer import HotelReviewAgent, load_reviews, find_review_text_column, validate_backend_credentials
from schemas import HotelImprovementReport

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def test_missing_api_key_validation() -> None:
    """Ensure RuntimeError is raised when API key is missing."""
    with patch.dict(os.environ, {"GOOGLE_API_KEY": ""}, clear=True):
        try:
            validate_backend_credentials("gemini")
            assert False, "Should have raised RuntimeError for missing GOOGLE_API_KEY"
        except RuntimeError as exc:
            assert "GOOGLE_API_KEY" in str(exc)
            print("Missing API key validation test passed:", exc)


def test_load_reviews() -> None:
    path = Path("data/review.csv") if Path("data/review.csv").exists() else Path("review.csv")
    df = load_reviews(path)
    assert not df.empty, "DataFrame should not be empty"
    col = find_review_text_column(df)
    assert col in df.columns, f"DataFrame must have review text column: {col}"
    print(f"Loaded {len(df)} rows from review.csv with column '{col}'")


def test_agent_single_review_with_mock() -> None:
    mock_result = {
        "sentiment": "Negative",
        "pain_point_flag": True,
        "category": "Cleanliness",
        "summary": "Phòng dơ và nhân viên kém.",
    }
    with patch.dict(os.environ, {"GOOGLE_API_KEY": "fake_test_key"}), \
         patch("analyzer.analyze_review", return_value=mock_result):
        agent = HotelReviewAgent(backend="gemini")
        result = agent.analyze_single_review("Phòng dơ, nhân viên phục vụ rất tệ.")
        assert result["sentiment"] == "Negative"
        assert result["pain_point_flag"] is True
        assert result["category"] == "Cleanliness"
        print("Single review mocked API analysis test passed.")


def test_agent_full_flow_with_mock() -> None:
    mock_batch_results = [
        {
            "review_index": i,
            "sentiment": "Negative",
            "pain_point_flag": True,
            "category": "Cleanliness",
            "summary": "Vấn đề vệ sinh phòng.",
        }
        for i in range(5)
    ]
    with patch.dict(os.environ, {"GOOGLE_API_KEY": "fake_test_key"}), \
         patch("analyzer.analyze_batch", return_value=mock_batch_results):
        agent = HotelReviewAgent(backend="gemini")
        path = Path("data/review.csv") if Path("data/review.csv").exists() else Path("review.csv")
        df = load_reviews(path)
        
        analyzed_df = agent.analyze_dataframe(df, limit=5, batch_size=5)
        assert "sentiment" in analyzed_df.columns
        assert "pain_point_flag" in analyzed_df.columns
        assert "category" in analyzed_df.columns
        assert "summary" in analyzed_df.columns
        assert len(analyzed_df) == 5

        report = agent.synthesize_report(analyzed_df, hotel_name="Kunkin Boutique Hotel")
        assert isinstance(report, HotelImprovementReport)
        assert report.total_reviews_analyzed == 5
        assert len(report.action_items) > 0

        md_test_path = Path("test_report.md")
        json_test_path = Path("test_report.json")
        agent.save_report_files(report, md_path=md_test_path, json_path=json_test_path)

        assert md_test_path.exists()
        assert json_test_path.exists()

        md_test_path.unlink()
        json_test_path.unlink()
        print("Full AI Agent batch workflow test passed!")


if __name__ == "__main__":
    test_missing_api_key_validation()
    test_load_reviews()
    test_agent_single_review_with_mock()
    test_agent_full_flow_with_mock()

