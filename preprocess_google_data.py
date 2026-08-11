"""Robust Preprocessor for Raw Scraped Review Data (google.csv / google.xlsx -> review.csv).

Automatically detects review columns, skips invalid/empty rows without stopping,
standardizes 1-5 star ratings ("5 sao", "4 sao"...), normalizes Unicode NFC text,
and processes the dataset completely to the end.
"""

import re
import sys
import unicodedata
from pathlib import Path
import pandas as pd

DATA_DIR = Path("data")
INPUT_CSV = DATA_DIR / "google.csv"
INPUT_XLSX = DATA_DIR / "google.xlsx"
OUTPUT_FILE = DATA_DIR / "review.csv"


def auto_detect_columns(df_raw: pd.DataFrame) -> dict:
    """Dynamically locate Author, Rating, Time, and Review text columns."""
    cols = [str(c).strip() for c in df_raw.columns]
    col_map = {"author": None, "rating": None, "time": None, "review": None}

    # Search by known column names / HTML class tags from Google Maps scrapers
    for i, col in enumerate(cols):
        col_lower = col.lower()
        if col in ["d4r55", "author", "tên", "name", "user"] and col_map["author"] is None:
            col_map["author"] = i
        elif col in ["fontbodylarge", "rating", "đánh giá", "score", "stars"] and col_map["rating"] is None:
            col_map["rating"] = i
        elif col in ["xrkppb", "time", "thời gian", "date"] and col_map["time"] is None:
            col_map["time"] = i
        elif col in ["wii7pd", "review", "content", "text", "bình luận", "phản hồi"] and col_map["review"] is None:
            col_map["review"] = i

    # Fallback heuristics if column tags were not matched
    if col_map["author"] is None and df_raw.shape[1] > 1:
        col_map["author"] = 1
    if col_map["rating"] is None and df_raw.shape[1] > 4:
        col_map["rating"] = 4
    if col_map["time"] is None and df_raw.shape[1] > 5:
        col_map["time"] = 5

    # If review column is not found by name, pick column with longest average text length
    if col_map["review"] is None:
        best_col_idx = df_raw.shape[1] - 1
        max_avg_len = -1
        for col_idx in range(df_raw.shape[1]):
            col_series = df_raw.iloc[:, col_idx].astype(str)
            avg_len = col_series.str.len().mean()
            if avg_len > max_avg_len:
                max_avg_len = avg_len
                best_col_idx = col_idx
        col_map["review"] = best_col_idx

    return col_map


def standardize_star_rating(rating_val: str, time_val: str, row_cells: list) -> tuple[str, str]:
    """Parse raw rating into standard 'X sao' format and prevent date string leakage."""
    r_str = str(rating_val).strip() if pd.notna(rating_val) else ""
    t_str = str(time_val).strip() if pd.notna(time_val) else "Mới đây"

    date_keywords = ["năm", "tháng", "tuần", "ngày", "trước", "ago"]
    is_r_date = any(k in r_str.lower() for k in date_keywords)
    is_t_date = any(k in t_str.lower() for k in date_keywords)

    # If rating column accidentally captured a date string
    if is_r_date:
        actual_time = r_str
        actual_rating = "5 sao"
        # Search all row cells for a valid 1-5 star pattern
        for cell in row_cells:
            c_text = str(cell).strip()
            if any(k in c_text.lower() for k in date_keywords):
                continue
            m = re.search(r"\b([1-5](?:[\.,]\d)?)\s*(?:/\s*5|\s*sao)?\b", c_text)
            if m:
                score = float(m.group(1).replace(",", "."))
                actual_rating = f"{round(score)} sao"
                break
        return actual_rating, actual_time

    # Standard rating conversion (e.g. 5/5 -> 5 sao, 4,5/5 -> 4 sao)
    m = re.search(r"([1-5](?:[\.,]\d)?)", r_str)
    if m:
        score = float(m.group(1).replace(",", "."))
        final_rating = f"{round(score)} sao"
    else:
        final_rating = "5 sao"

    final_time = t_str if is_t_date or t_str != "N/A" else "Mới đây"
    return final_rating, final_time


def preprocess_google_data(
    input_file: Path = INPUT_CSV,
    output_file: Path = OUTPUT_FILE,
) -> pd.DataFrame:
    """Preprocess raw scraped CSV/XLSX into clean review.csv, standardizing 1-5 star scale."""
    if not input_file.exists() and INPUT_XLSX.exists():
        input_file = INPUT_XLSX

    if not input_file.exists():
        raise FileNotFoundError(f"Không tìm thấy file dữ liệu đầu vào: {input_file}")

    print(f"[INFO] Dang doc va tien xu ly du lieu tu: {input_file}...")

    # Load raw file
    if input_file.suffix.lower() == ".xlsx":
        df_raw = pd.read_excel(input_file)
    else:
        df_raw = pd.read_csv(input_file, encoding="utf-8-sig", on_bad_lines="skip")

    total_rows = len(df_raw)
    col_map = auto_detect_columns(df_raw)

    valid_reviews = []
    skipped_count = 0

    # Continuously process every single row from index 0 to end of file
    for idx in range(total_rows):
        author_val = df_raw.iloc[idx, col_map["author"]] if col_map["author"] < df_raw.shape[1] else None
        rating_val = df_raw.iloc[idx, col_map["rating"]] if col_map["rating"] < df_raw.shape[1] else None
        time_val = df_raw.iloc[idx, col_map["time"]] if col_map["time"] < df_raw.shape[1] else None
        review_val = df_raw.iloc[idx, col_map["review"]] if col_map["review"] < df_raw.shape[1] else None

        # Sanitize review text
        review_text = str(review_val).strip() if pd.notna(review_val) else ""
        review_text = unicodedata.normalize("NFC", review_text)

        # CONDITION CHECK: Skip empty / corrupted / invalid review cells and continue to next row
        if (
            not review_text
            or len(review_text) < 3
            or review_text.lower() in ["nan", "none", "null", "...", "-", "undefined"]
        ):
            skipped_count += 1
            continue

        # Format clean author name
        author = str(author_val).strip() if pd.notna(author_val) else "Khách hàng"
        author = unicodedata.normalize("NFC", author)

        # Standardize Rating to 1-5 Star Scale ("5 sao", "4 sao"...) & Fix Time
        row_cells = df_raw.iloc[idx].tolist()
        star_rating, time_str = standardize_star_rating(str(rating_val), str(time_val), row_cells)

        time_str = unicodedata.normalize("NFC", time_str)

        valid_reviews.append({
            "Tên": author,
            "Đánh giá": star_rating,
            "Thời gian": time_str,
            "Review": review_text,
        })

    # Create clean output DataFrame
    clean_df = pd.DataFrame(valid_reviews)

    # Save to data/review.csv with UTF-8-BOM encoding for Excel / Pandas compatibility
    output_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        clean_df.to_csv(output_file, index=False, encoding="utf-8-sig")
        saved_path = output_file
    except PermissionError:
        saved_path = output_file.with_name("review_clean.csv")
        clean_df.to_csv(saved_path, index=False, encoding="utf-8-sig")

    print("==================================================")
    print(f"[THONG KE PREPROCESS]")
    print(f" - Tong so dong trong file tho: {total_rows}")
    print(f" - So dong o trong/khong dat dieu kien da LOAI BO: {skipped_count}")
    print(f" - So luong Review hop le DA LUU thanh cong: {len(clean_df)}")
    print(f" - File ket qua duoc luu tai: {saved_path}")
    print("==================================================")

    return clean_df


if __name__ == "__main__":
    preprocess_google_data()
