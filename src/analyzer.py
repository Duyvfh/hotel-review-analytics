"""Hotel review analyzer and strategic AI Agent for boutique hotel service improvement recommendations."""

from __future__ import annotations

import argparse
import io
import json
import logging
import os
import re
import time
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from pydantic import ValidationError

from schemas import (
    ANALYSIS_COLUMNS,
    ActionItem,
    AnalysisResult,
    BatchAnalysisItem,
    BatchAnalysisResult,
    CategoryInsight,
    HotelImprovementReport,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

REVIEW_FILE = DATA_DIR / "review_clean.csv" if (DATA_DIR / "review_clean.csv").exists() else (DATA_DIR / "review.csv" if (DATA_DIR / "review.csv").exists() else PROJECT_ROOT / "review.csv")
OUTPUT_FILE = OUTPUT_DIR / "analyzed_reviews.csv"
REPORT_MD_FILE = OUTPUT_DIR / "hotel_improvement_report.md"
REPORT_JSON_FILE = OUTPUT_DIR / "hotel_improvement_report.json"
DASHBOARD_HTML_FILE = OUTPUT_DIR / "index.html"
DEFAULT_BACKEND = "gemini"
DEFAULT_MODEL = "gemini-3.1-flash-lite"
API_DELAY_SECONDS = 3.0

SYSTEM_PROMPT = (
    "You analyze hotel reviews for a boutique hotel. Respond with ONLY a valid JSON object. "
    "Do not include markdown or extra text."
)

USER_PROMPT_TEMPLATE = """Analyze this review for a boutique hotel and return JSON with exactly these keys:
- "sentiment": one of "Positive", "Neutral", "Negative"
- "pain_point_flag": boolean, true if there is a complaint or negative issue, false otherwise
- "category": one of "Cleanliness", "Staff_Service", "Room_Amenities", "Boutique_Experience", "Pricing_and_Fees", "Noise_and_Quietness", "Location_and_Access", "F_and_B", "Others", or null if no complaint
- "summary": a 1-sentence summary of the complaint or main point, or null if no complaint

Review:
{review_text}
"""


def validate_backend_credentials(backend: str) -> None:
    """Validate API credentials/installation before processing reviews."""
    if backend == "gemini":
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError(
                "[Backend: gemini] Thiếu GOOGLE_API_KEY trong biến môi trường. "
                "Vui lòng cấu hình GOOGLE_API_KEY trước khi chạy. "
                "Ví dụ (PowerShell): $env:GOOGLE_API_KEY=\"AIzaSy...\""
            )
        try:
            from google import genai  # type: ignore
        except (ModuleNotFoundError, ImportError) as exc:
            raise RuntimeError(
                "[Backend: gemini] Thư viện google-genai chưa được cài đặt hoặc chưa active môi trường venv. "
                "Vui lòng chạy bằng python trong venv (.\\venv\\Scripts\\python.exe analyzer.py) "
                "hoặc cài đặt thư viện bằng: pip install google-genai"
            ) from exc

    elif backend == "openai":
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "[Backend: openai] Thiếu OPENAI_API_KEY trong biến môi trường. "
                "Vui lòng cấu hình OPENAI_API_KEY trước khi chạy. "
                "Ví dụ (PowerShell): $env:OPENAI_API_KEY=\"sk-...\""
            )
        try:
            import openai  # type: ignore
        except (ModuleNotFoundError, ImportError) as exc:
            raise RuntimeError(
                "[Backend: openai] Thư viện openai chưa được cài đặt hoặc chưa active môi trường venv. "
                "Vui lòng chạy bằng python trong venv (.\\venv\\Scripts\\python.exe analyzer.py) "
                "hoặc cài đặt thư viện bằng: pip install openai"
            ) from exc

    elif backend == "ollama":
        try:
            import ollama  # type: ignore
        except (ModuleNotFoundError, ImportError) as exc:
            raise RuntimeError(
                "[Backend: ollama] Thư viện ollama chưa được cài đặt hoặc chưa active môi trường venv. "
                "Vui lòng chạy bằng python trong venv (.\\venv\\Scripts\\python.exe analyzer.py) "
                "hoặc cài đặt thư viện bằng: pip install ollama"
            ) from exc

    else:
        raise ValueError(f"Backend không hợp lệ: '{backend}'. Vui lòng chọn trong ['gemini', 'openai', 'ollama'].")


def clean_llm_json(content: str) -> str:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return match.group(0)
    return text.strip()


def parse_llm_response(content: str) -> AnalysisResult:
    cleaned = clean_llm_json(content)
    payload = json.loads(cleaned)
    return AnalysisResult(**payload)


def extract_gemini_text(response: Any) -> str:
    if response is None:
        return ""
    if isinstance(response, str):
        return response
    if hasattr(response, "text") and response.text:
        return response.text
    if isinstance(response, dict):
        if "text" in response and response["text"]:
            return str(response["text"])
        candidates = response.get("candidates")
        if candidates:
            first = candidates[0]
            if isinstance(first, dict):
                content = first.get("content")
                if isinstance(content, dict):
                    parts = content.get("parts", [])
                    if parts:
                        return "".join(
                            part.get("text", "") for part in parts if isinstance(part, dict)
                        )
                if "text" in first:
                    return str(first["text"])
    if hasattr(response, "candidates"):
        candidates = getattr(response, "candidates")
        if candidates:
            first = candidates[0]
            if hasattr(first, "content"):
                content = getattr(first, "content")
                if hasattr(content, "parts"):
                    parts = getattr(content, "parts")
                    if parts:
                        texts = [getattr(part, "text", "") for part in parts if hasattr(part, "text")]
                        if texts:
                            return "".join(texts)
                if hasattr(first, "text"):
                    return first.text
    return ""


def analyze_review(review_text: str, model: str, backend: str, retry: bool = True) -> Dict[str, Any]:
    target_model = model or ("gemini-3.6-flash" if backend == "gemini" else "gpt-4o-mini" if backend == "openai" else "llama3.2")
    if backend == "ollama":
        try:
            import ollama  # type: ignore
            prompt = f"{SYSTEM_PROMPT}\n\n{USER_PROMPT_TEMPLATE.format(review_text=review_text)}"
            response = ollama.chat(
                model=target_model,
                messages=[{"role": "user", "content": prompt}],
                format="json",
            )
            content = response["message"]["content"]
            result = parse_llm_response(content)
            return result.model_dump()
        except Exception as exc:
            err_msg = f"[Backend: ollama | Model: {target_model}] Lỗi khi gọi Ollama API: {type(exc).__name__}: {exc}"
            logger.error(err_msg)
            raise RuntimeError(err_msg) from exc

    if backend == "openai":
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            err_msg = "[Backend: openai] API Key bị trống (OPENAI_API_KEY is not set)."
            logger.error(err_msg)
            raise RuntimeError(err_msg)
        try:
            import openai  # type: ignore
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": USER_PROMPT_TEMPLATE.format(review_text=review_text)},
            ]
            if hasattr(openai, "OpenAI"):
                client = openai.OpenAI(api_key=api_key)
                response = client.chat.completions.create(
                    model=target_model,
                    messages=messages,
                    temperature=0,
                    max_tokens=512,
                )
                content = response.choices[0].message.content or ""
            else:
                openai.api_key = api_key
                response = openai.ChatCompletion.create(
                    model=target_model,
                    messages=messages,
                    temperature=0,
                    max_tokens=512,
                )
                content = response["choices"][0]["message"]["content"]
            result = parse_llm_response(content)
            return result.model_dump()
        except (json.JSONDecodeError, ValidationError, KeyError, TypeError) as exc:
            if retry:
                logger.warning("[Backend: openai | Model: %s] Thử lại sau lỗi parse JSON response: %s", target_model, exc)
                time.sleep(API_DELAY_SECONDS)
                return analyze_review(review_text, target_model, backend, retry=False)
            err_msg = f"[Backend: openai | Model: {target_model}] Lỗi parse dữ liệu JSON từ LLM: {type(exc).__name__}: {exc}"
            logger.error(err_msg)
            raise RuntimeError(err_msg) from exc
        except Exception as exc:
            err_msg = f"[Backend: openai | Model: {target_model}] Lỗi khi gọi OpenAI API: {type(exc).__name__}: {exc}"
            logger.error(err_msg)
            raise RuntimeError(err_msg) from exc

    if backend == "gemini":
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            err_msg = "[Backend: gemini] API Key bị trống (GOOGLE_API_KEY is not set)."
            logger.error(err_msg)
            raise RuntimeError(err_msg)
        
        fallback_models = [target_model, "gemini-flash-latest", "gemini-3.1-flash-lite"]
        candidate_models = list(dict.fromkeys(fallback_models))
        
        try:
            from google import genai as google_genai  # type: ignore
            from google.genai import types  # type: ignore
            client = google_genai.Client(api_key=api_key)
            prompt = f"{SYSTEM_PROMPT}\n\n{USER_PROMPT_TEMPLATE.format(review_text=review_text)}"

            last_exception = None
            for current_model in candidate_models:
                for attempt in range(1, 4):
                    try:
                        response = client.models.generate_content(
                            model=current_model,
                            contents=prompt,
                            config=types.GenerateContentConfig(
                                temperature=0,
                                max_output_tokens=1024,
                                response_mime_type="application/json",
                                response_schema=AnalysisResult,
                            ),
                        )
                        content = extract_gemini_text(response)
                        if not content:
                            raise RuntimeError("Gemini model không trả về nội dung text nào")
                        result = parse_llm_response(content)
                        return result.model_dump()
                    except (json.JSONDecodeError, ValidationError, KeyError, TypeError) as exc:
                        logger.warning("[Backend: gemini | Model: %s] Thử lại lượt %d/3 sau lỗi parse JSON: %s", current_model, attempt, exc)
                        time.sleep(API_DELAY_SECONDS)
                        last_exception = exc
                    except Exception as exc:
                        last_exception = exc
                        exc_str = str(exc)
                        if "503" in exc_str or "UNAVAILABLE" in exc_str or "429" in exc_str or "RESOURCE_EXHAUSTED" in exc_str:
                            wait_time = attempt * 3
                            logger.warning(
                                "[Backend: gemini | Model: %s] Máy chủ Google bận/quá tải tạm thời (503/429). Tự động chờ %d giây và thử lại (lượt %d/3)...",
                                current_model, wait_time, attempt
                            )
                            time.sleep(wait_time)
                        else:
                            break

            err_msg = f"[Backend: gemini | Model: {target_model}] Lỗi khi gọi Gemini API: {type(last_exception).__name__}: {last_exception}"
            logger.error(err_msg)
            raise RuntimeError(err_msg) from last_exception
        except Exception as exc:
            if "last_exception" in locals() and last_exception:
                exc = last_exception
            err_msg = f"[Backend: gemini | Model: {target_model}] Lỗi khi gọi Gemini API: {type(exc).__name__}: {exc}"
            logger.error(err_msg)
            raise RuntimeError(err_msg) from exc

    err_msg = f"Backend không được hỗ trợ: '{backend}'. Các backend hợp lệ: ['gemini', 'openai', 'ollama']."
    logger.error(err_msg)
    raise ValueError(err_msg)


def analyze_batch(batch_items: List[Dict[str, Any]], model: str, backend: str) -> List[Dict[str, Any]]:
    """Analyze a batch of reviews in a single API call for maximum performance and rate limit efficiency."""
    target_model = model or ("gemini-3.1-flash-lite" if backend == "gemini" else "gpt-4o-mini" if backend == "openai" else "llama3.2")
    if not batch_items:
        return []

    if backend == "gemini":
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("[Backend: gemini] API Key bị trống (GOOGLE_API_KEY is not set).")

        fallback_models = [target_model, "gemini-3.6-flash", "gemini-flash-latest"]
        candidate_models = list(dict.fromkeys(fallback_models))

        from google import genai as google_genai  # type: ignore
        from google.genai import types  # type: ignore
        client = google_genai.Client(api_key=api_key)
        
        reviews_json = json.dumps(batch_items, ensure_ascii=False)
        batch_prompt = (
            "Analyze the following list of boutique hotel reviews.\n"
            "For each review in the input list, generate a corresponding item in the 'results' list with matching 'review_index'.\n\n"
            f"Input Reviews List:\n{reviews_json}"
        )

        last_exception = None
        for current_model in candidate_models:
            for attempt in range(1, 4):
                try:
                    response = client.models.generate_content(
                        model=current_model,
                        contents=batch_prompt,
                        config=types.GenerateContentConfig(
                            temperature=0,
                            max_output_tokens=2048,
                            response_mime_type="application/json",
                            response_schema=BatchAnalysisResult,
                        ),
                    )
                    content = extract_gemini_text(response)
                    if not content:
                        raise RuntimeError("Gemini model không trả về nội dung text nào cho batch")
                    cleaned = clean_llm_json(content)
                    parsed = json.loads(cleaned)
                    batch_res = BatchAnalysisResult(**parsed)
                    return [item.model_dump() for item in batch_res.results]
                except (json.JSONDecodeError, ValidationError, KeyError, TypeError) as exc:
                    logger.warning("[Backend: gemini | Model: %s] Thử lại lượt %d/3 sau lỗi parse JSON batch: %s", current_model, attempt, exc)
                    time.sleep(API_DELAY_SECONDS)
                    last_exception = exc
                except Exception as exc:
                    last_exception = exc
                    exc_str = str(exc)
                    if "503" in exc_str or "UNAVAILABLE" in exc_str or "429" in exc_str or "RESOURCE_EXHAUSTED" in exc_str:
                        wait_time = attempt * 3
                        logger.warning(
                            "[Backend: gemini | Model: %s] Máy chủ Google bận (503/429). Tự động chờ %ds thử lại batch (lượt %d/3)...",
                            current_model, wait_time, attempt
                        )
                        time.sleep(wait_time)
                    else:
                        break

        raise RuntimeError(f"Lỗi khi xử lý batch: {last_exception}")

    # Fallback for non-gemini or single item fallback
    results = []
    for item in batch_items:
        res = analyze_review(item["text"], model=model, backend=backend)
        res["review_index"] = item["review_index"]
        results.append(res)
    return results


def auto_decode_and_normalize_bytes(raw_bytes: bytes) -> str:
    """Dynamically detect codepage (UTF-8, CP1258, UTF-16, etc.) and normalize Vietnamese NFC Unicode."""
    candidates = ["utf-8-sig", "utf-8", "cp1258", "utf-16", "cp1252", "latin1"]
    best_text = ""
    best_score = -999999.0

    for enc in candidates:
        try:
            decoded = raw_bytes.decode(enc)
            normalized = unicodedata.normalize("NFC", decoded)
            
            replacement_count = normalized.count("\ufffd") + normalized.count("?")
            viet_chars = len(re.findall(r"[àáảãạâầấẩẫậăằắẳẵặèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđĐ]", normalized, re.IGNORECASE))
            
            score = viet_chars * 10 - replacement_count * 50
            if score > best_score:
                best_score = score
                best_text = normalized
        except Exception:
            continue

    if not best_text:
        best_text = unicodedata.normalize("NFC", raw_bytes.decode("utf-8", errors="ignore"))

    return best_text


def load_reviews(path: Path = REVIEW_FILE) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy file {path}. Vui lòng chuẩn bị file review.csv trong thư mục dự án.")

    raw_bytes = path.read_bytes()
    clean_text = auto_decode_and_normalize_bytes(raw_bytes)

    try:
        df = pd.read_csv(io.StringIO(clean_text), on_bad_lines="skip")
        df.columns = df.columns.str.strip().str.replace("\ufeff", "").str.replace("ï»¿", "")
        
        # Apply automatic Unicode NFC normalization across all text columns
        for col in df.columns:
            if df[col].dtype == "object" or str(df[col].dtype).startswith("string"):
                df[col] = df[col].astype(str).apply(lambda s: unicodedata.normalize("NFC", s))
                
        logger.info("Đã tải và tự động chuẩn hóa tiếng Việt cho %s (số dòng: %d)", path.name, len(df))
        return df
    except Exception as exc:
        raise RuntimeError(f"Lỗi khi đọc file {path}: {exc}") from exc


def find_review_text_column(df: pd.DataFrame) -> str:
    possible_names = [
        "review_text",
        "Review",
        "review",
        "review_texts",
        "content",
        "text",
        "danh_gia",
        "đánh giá",
        "Đánh giá",
        "noi_dung",
        "nội dung",
        "Nội dung",
        "comment",
        "Comment",
        "phan_hoi",
        "phản hồi",
        "Phản hồi",
    ]
    for name in possible_names:
        if name in df.columns:
            return name
        for col in df.columns:
            if col.strip().lower() == name.lower():
                return col
    raise ValueError(
        f"Không tìm thấy cột chứa nội dung đánh giá trong CSV. Các cột hiện có: {list(df.columns)}"
    )


class HotelReviewAgent:
    """AI Agent tailored for Boutique Hotel review analysis and strategic improvement planning."""

    def __init__(self, backend: str = DEFAULT_BACKEND, model: Optional[str] = None):
        self.backend = backend
        validate_backend_credentials(self.backend)
        self.model = model or (
            "gemini-3.1-flash-lite" if backend == "gemini"
            else "llama3.2" if backend == "ollama"
            else "gpt-4o-mini" if backend == "openai"
            else "gemini-3.1-flash-lite"
        )

    def analyze_single_review(self, review_text: str) -> Dict[str, Any]:
        return analyze_review(review_text, model=self.model, backend=self.backend)

    def analyze_dataframe(self, df: pd.DataFrame, limit: Optional[int] = None, batch_size: int = 10) -> pd.DataFrame:
        review_col = find_review_text_column(df)
        df_work = df.head(limit).copy() if limit else df.copy()

        for col in ANALYSIS_COLUMNS:
            if col not in df_work.columns:
                df_work[col] = None

        valid_rows = []
        for index, row in df_work.iterrows():
            text = str(row.get(review_col, "")).strip()
            if text and text.lower() not in ["nan", "none", "null"]:
                valid_rows.append((index, text))

        total = len(valid_rows)
        logger.info(
            "AI Agent starting batch analysis of %d reviews using backend '%s' (model: %s, batch size: %d)",
            total, self.backend, self.model, batch_size
        )

        for i in range(0, total, batch_size):
            chunk = valid_rows[i : i + batch_size]
            batch_payload = [{"review_index": idx, "text": txt} for idx, txt in chunk]
            
            logger.info(
                "Processing batch %d/%d (reviews %d to %d)...",
                (i // batch_size) + 1,
                (total + batch_size - 1) // batch_size,
                i + 1,
                min(i + batch_size, total)
            )

            try:
                batch_results = analyze_batch(batch_payload, model=self.model, backend=self.backend)
                results_by_idx = {res["review_index"]: res for res in batch_results if "review_index" in res}
                
                for idx, _ in chunk:
                    if idx in results_by_idx:
                        res = results_by_idx[idx]
                        for col in ANALYSIS_COLUMNS:
                            df_work.at[idx, col] = res.get(col)
                    else:
                        res = self.analyze_single_review(str(df_work.at[idx, review_col]))
                        for col in ANALYSIS_COLUMNS:
                            df_work.at[idx, col] = res.get(col)
            except Exception as exc:
                logger.warning("Batch execution failed, falling back to single review mode for this batch: %s", exc)
                for idx, txt in chunk:
                    res = self.analyze_single_review(txt)
                    for col in ANALYSIS_COLUMNS:
                        df_work.at[idx, col] = res.get(col)

            time.sleep(API_DELAY_SECONDS)

        return df_work

    def synthesize_report(self, df: pd.DataFrame, hotel_name: str = "Boutique Hotel Service Analysis") -> HotelImprovementReport:
        total_reviews = len(df)
        sentiment_counts = df["sentiment"].value_counts().to_dict() if "sentiment" in df.columns else {}
        overall_sentiment = {
            "Positive": int(sentiment_counts.get("Positive", 0)),
            "Neutral": int(sentiment_counts.get("Neutral", 0)),
            "Negative": int(sentiment_counts.get("Negative", 0)),
        }

        pain_points_df = df[df["pain_point_flag"] == True] if "pain_point_flag" in df.columns else df
        total_pain_points = len(pain_points_df)

        category_insights: list[CategoryInsight] = []

        if "category" in df.columns:
            cat_counts = pain_points_df["category"].value_counts().to_dict()
            for cat, count in cat_counts.items():
                if not cat or cat == "None":
                    continue
                pct = round((count / max(total_pain_points, 1)) * 100, 1)
                summaries = pain_points_df[pain_points_df["category"] == cat]["summary"].dropna().tolist()[:5]
                clean_summaries = [str(s) for s in summaries if str(s).strip()]

                root_cause_map = {
                    "Pricing_and_Fees": "Thiếu minh bạch trong phụ phí điện/nước và thủ tục hóa đơn tài chính.",
                    "Staff_Service": "Quy trình chăm sóc chưa ấm cúng & thiếu giải quyết linh hoạt khi sự cố xảy ra.",
                    "Cleanliness": "Quy trình kiểm tra dọn phòng chưa nghiêm ngặt, ảnh hưởng tiêu chuẩn Boutique.",
                    "Room_Amenities": "Thiết bị hạ tầng (điều hòa, nước nóng, wifi) xuống cấp chưa bảo trì kịp thời.",
                    "Noise_and_Quietness": "Độ cách âm chưa đạt chuẩn làm mất đi sự riêng tư yên tĩnh của khách sạn boutique.",
                    "Boutique_Experience": "Thiết kế không gian hoặc trải nghiệm phòng ở chưa đúng kỳ vọng quảng cáo.",
                    "Location_and_Access": "Hướng dẫn vị trí và đường đi/chỗ đỗ xe chưa chi tiết cho khách.",
                    "F_and_B": "Chất lượng dịch vụ ăn uống/bữa sáng chưa đa dạng.",
                    "Others": "Quy trình đặt phòng và xuất hóa đơn giao dịch gặp trục trặc.",
                }

                insight = CategoryInsight(
                    category=cat,
                    complaint_count=int(count),
                    percentage=pct,
                    key_issues=clean_summaries,
                    root_cause=root_cause_map.get(cat, f"Vấn đề phát sinh trong vận hành nhóm {cat}.")
                )
                category_insights.append(insight)

        # Build structured Action Items with clear Rationale and SLA Timelines
        action_items: list[ActionItem] = []
        cat_map = {ci.category: ci for ci in category_insights}

        if "Pricing_and_Fees" in cat_map or "Others" in cat_map:
            action_items.append(ActionItem(
                priority="High",
                priority_rationale="Trực tiếp gây tranh chấp pháp lý/tài chính và tạo bài đánh giá 1 sao (phạt điện nước 5k/số, không xuất hóa đơn). Lỗi Deal-breaker với khách sạn.",
                department="Ban Quản Lý & Kế Toán",
                issue="Thu phụ phí điện/nước bất hợp lý, thiếu minh bạch hóa đơn thanh toán",
                action_plan="Ban hành ngay bảng giá niêm yết chuẩn; rà soát lại hợp đồng thuê; đào tạo nhân viên cung cấp hóa đơn/biên nhận rõ ràng cho khách.",
                timeline="Ngay lập tức (24h - 3 ngày)"
            ))

        if "Cleanliness" in cat_map:
            action_items.append(ActionItem(
                priority="High",
                priority_rationale="Sạch sẽ là yêu cầu tối quan trọng của mô hình Boutique Hotel. Phòng dơ hoặc có mùi sẽ ngay lập tức làm mất hình ảnh thương hiệu cao cấp.",
                department="Bộ Phận Buồng Phòng (Housekeeping)",
                issue="Vệ sinh phòng, phòng tắm hoặc mùi hôi chưa đạt tiêu chuẩn boutique",
                action_plan="Thiết lập quy trình kiểm tra vệ sinh 2 lớp (Nhân viên dọn + Trưởng nhóm duyệt) trước khi giao phòng. Đặt tinh dầu/khử mùi tự nhiên.",
                timeline="Trong vòng 3 ngày"
            ))

        if "Room_Amenities" in cat_map:
            action_items.append(ActionItem(
                priority="Medium",
                priority_rationale="Hạ tầng chập chờn (máy lạnh yếu, wifi chậm) giảm điểm rating từ 5* xuống 3-4*. Cần bảo trì nhưng có thể thu xếp trong 1-2 tuần.",
                department="Bộ Phận Bảo Trì (Maintenance)",
                issue="Trang thiết bị phòng ở (máy lạnh, nước nóng, wifi) hoạt động không ổn định",
                action_plan="Kiểm tra tổng thể toàn bộ hệ thống điện lạnh và internet; thay thế các thiết bị cũ hỏng.",
                timeline="1 - 2 tuần"
            ))

        if "Staff_Service" in cat_map:
            action_items.append(ActionItem(
                priority="Medium",
                priority_rationale="Boutique Hotel sống bằng sự tận tụy và ấm cúng của nhân viên. Thái độ thiếu linh hoạt cần được khắc phục qua đào tạo nội bộ.",
                department="Bộ Phận Lễ Tân & Nhân Sự",
                issue="Thái độ giao tiếp chưa ấm cúng, xử lý sự cố chưa linh hoạt chuẩn boutique",
                action_plan="Đào tạo chuẩn phong cách dịch vụ Boutique (Personalized Service); ban hành quy trình đền bù sự cố nhanh (khách không phải chờ đợi).",
                timeline="1 - 2 tuần"
            ))

        if "Noise_and_Quietness" in cat_map:
            action_items.append(ActionItem(
                priority="Low",
                priority_rationale="Ảnh hưởng đến trải nghiệm riêng tư nhưng phụ thuộc vào kết cấu hạ tầng, cần thời gian thi công bổ sung vật liệu cách âm.",
                department="Bộ Phận Bảo Trì & Thi Công",
                issue="Tiếng ồn đêm khuya và độ cách âm giữa các phòng chưa hoàn hảo",
                action_plan="Lắp ron cao su cách âm chân cửa; nhắc nhở khách giữ yên tĩnh sau 22h; trang bị nút tai cách âm tặng khách.",
                timeline="2 - 4 tuần"
            ))

        if not action_items:
            action_items.append(ActionItem(
                priority="Low",
                priority_rationale="Duy trì chất lượng vận hành cao cấp hiện tại của khách sạn.",
                department="Tất Cả Các Bộ Phận",
                issue="Duy trì tiêu chuẩn trải nghiệm Boutique",
                action_plan="Thu thập phản hồi khách hàng thường xuyên.",
                timeline="Hàng tháng"
            ))

        exec_summary = (
            f"Báo cáo phân tích {total_reviews} đánh giá từ khách hàng cho thấy có {total_pain_points} phản hồi mang tính khiếu nại/góp ý. "
            f"Đối với định vị Khách sạn Boutique, vấn đề ảnh hưởng trực tiếp đến uy tín thương hiệu tập trung ở các nhóm: {', '.join([ci.category for ci in category_insights[:3]]) if category_insights else 'Chưa ghi nhận'}. "
            "Ban quản lý cần ưu tiên xử lý ngay các khiếu nại về minh bạch chi phí dịch vụ và quy trình vệ sinh phòng ở trong SLA 1-3 ngày."
        )

        return HotelImprovementReport(
            hotel_name=hotel_name,
            total_reviews_analyzed=total_reviews,
            overall_sentiment_breakdown=overall_sentiment,
            total_pain_points=total_pain_points,
            executive_summary=exec_summary,
            category_insights=category_insights,
            action_items=action_items,
        )

    def save_report_files(
        self,
        report: HotelImprovementReport,
        md_path: Path = REPORT_MD_FILE,
        json_path: Path = REPORT_JSON_FILE,
    ) -> None:
        json_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
        logger.info("Saved strategic report JSON to %s", json_path)

        md_content = []
        md_content.append("# 🏨 Báo Cáo Chiến Lược Cải Thiện Dịch Vụ Khách Sạn Boutique")
        md_content.append(f"**Khách sạn / Cơ sở:** {report.hotel_name}")
        md_content.append(f"**Tổng số đánh giá đã phân tích:** {report.total_reviews_analyzed}")
        md_content.append(f"**Tổng số khiếu nại (Pain Points):** {report.total_pain_points}\n")

        md_content.append("## 1. 📌 Tổng Quan Tình Hình (Executive Summary)")
        md_content.append(f"{report.executive_summary}\n")

        md_content.append("## 2. 📈 Phân Phối Cảm Xúc Khách Hàng (Sentiment Breakdown)")
        md_content.append(f"- 🟢 **Tích cực (Positive):** {report.overall_sentiment_breakdown.get('Positive', 0)}")
        md_content.append(f"- 🟡 **Trung tính (Neutral):** {report.overall_sentiment_breakdown.get('Neutral', 0)}")
        md_content.append(f"- 🔴 **Tiêu cực (Negative):** {report.overall_sentiment_breakdown.get('Negative', 0)}\n")

        md_content.append("## 3. 🔍 Phân Tích Chi Tiết Theo Phân Loại Dịch Vụ Boutique (Category Insights)")
        if report.category_insights:
            for ci in report.category_insights:
                md_content.append(f"### 🎯 Nhóm: {ci.category}")
                md_content.append(f"- **Số lượng khiếu nại:** {ci.complaint_count} ({ci.percentage}% tổng khiếu nại)")
                md_content.append(f"- **Nguyên nhân cốt lõi:** {ci.root_cause}")
                md_content.append("- **Các phản hồi tiêu biểu từ khách hàng:**")
                for issue in ci.key_issues:
                    md_content.append(f"  - *\"{issue}\"*")
                md_content.append("")
        else:
            md_content.append("Chưa phát hiện nhóm khiếu nại tập trung.\n")

        md_content.append("## 4. 🛠️ Kế Hoạch Hành Động Cải Thiện Dịch Vụ (Action Plan & Prioritization)")
        md_content.append("### 💡 Tiêu chí Phân cấp Ưu tiên & Khung Thời gian SLA:")
        md_content.append("- 🔴 **High (Cao - SLA 24h đến 3 ngày)**: Lỗi trực tiếp gây tranh chấp tài chính/pháp lý, vi phạm vệ sinh nghiêm trọng hoặc hỏng hóc thiết bị chính. Đây là lỗi 'Deal-breaker' phẫn nộ làm mất khách lập tức.")
        md_content.append("- 🟡 **Medium (Trung bình - SLA 1 đến 2 tuần)**: Lỗi ảnh hưởng đến trải nghiệm nghỉ ngơi chuẩn boutique (wifi, máy lạnh yếu, thái độ phục vụ chưa ấm cúng), kéo điểm rating từ 5* xuống 3-4*.")
        md_content.append("- 🟢 **Low (Thấp - SLA 2 đến 4 tuần)**: Yêu cầu nâng cấp thêm không gian, decor, tiện ích bổ sung (Nice-to-have).\n")

        md_content.append("| Mức Ưu Tiên | Bộ Phận | Vấn Đề | Lý Do Phân Loại | Giải Pháp Đề Xuất | Khung Thời Gian (SLA) |")
        md_content.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
        for item in report.action_items:
            priority_icon = "🔴 High" if item.priority == "High" else ("🟡 Medium" if item.priority == "Medium" else "🟢 Low")
            md_content.append(f"| {priority_icon} | {item.department} | {item.issue} | {item.priority_rationale} | {item.action_plan} | {item.timeline} |")

        md_path.write_text("\n".join(md_content), encoding="utf-8")
        logger.info("Saved strategic report Markdown to %s", md_path)


def run_analyzer(
    backend: str = DEFAULT_BACKEND,
    model: Optional[str] = None,
    limit: Optional[int] = None,
    batch_size: int = 10,
    generate_report: bool = True,
) -> None:
    agent = HotelReviewAgent(backend=backend, model=model)
    df = load_reviews(REVIEW_FILE)
    analyzed_df = agent.analyze_dataframe(df, limit=limit, batch_size=batch_size)

    try:
        analyzed_df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
        logger.info("Saved analyzed reviews to %s", OUTPUT_FILE)
    except PermissionError:
        fallback_file = OUTPUT_FILE.with_name(f"analyzed_reviews_{int(time.time())}.csv")
        analyzed_df.to_csv(fallback_file, index=False, encoding="utf-8-sig")
        logger.info("Saved analyzed reviews to fallback file %s", fallback_file)

    if generate_report:
        report = agent.synthesize_report(analyzed_df)
        agent.save_report_files(report)
        try:
            from build_dashboard import generate_dashboard
            generate_dashboard()
            logger.info("Saved interactive web dashboard to %s", DASHBOARD_HTML_FILE)
        except Exception as exc:
            logger.warning("Không thể tự động tạo index.html: %s", exc)


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze boutique hotel reviews using AI Agent.")
    parser.add_argument(
        "--backend",
        default=DEFAULT_BACKEND,
        choices=["gemini", "openai", "ollama"],
        help="Backend to use for LLM analysis. Default is 'gemini' (requires GOOGLE_API_KEY).",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Model name to use (e.g. gemini-3.1-flash-lite, llama3.2, gpt-4o-mini).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Analyze only the first N reviews (useful for quick testing).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Number of reviews to process in a single API call (default: 10).",
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="Skip generating the strategic improvement report.",
    )
    args = parser.parse_args()
    run_analyzer(
        backend=args.backend,
        model=args.model,
        limit=args.limit,
        batch_size=args.batch_size,
        generate_report=not args.no_report,
    )


if __name__ == "__main__":
    main()
