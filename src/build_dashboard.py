"""Interactive Web Dashboard Generator for Boutique Hotel Review AI Analytics."""

import json
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"

REPORT_JSON_FILE = OUTPUT_DIR / "hotel_improvement_report.json" if (OUTPUT_DIR / "hotel_improvement_report.json").exists() else PROJECT_ROOT / "hotel_improvement_report.json"
CSV_FILE = OUTPUT_DIR / "analyzed_reviews.csv" if (OUTPUT_DIR / "analyzed_reviews.csv").exists() else PROJECT_ROOT / "analyzed_reviews.csv"
DASHBOARD_HTML_FILE = OUTPUT_DIR / "index.html"

CATEGORY_TRANSLATIONS = {
    "Room_Amenities": "Tiện Nghi Phòng Ở",
    "Location_and_Access": "Vị Trí & Di Chuyển",
    "Cleanliness": "Vệ Sinh Phòng Ở",
    "Staff_Service": "Dịch Vụ & Thái Độ Nhân Viên",
    "Pricing_and_Fees": "Chi Phí & Phụ Phí Minh Bạch",
    "Noise_and_Quietness": "Độ Cách Âm & Yên Tĩnh",
    "Boutique_Experience": "Trải Nghiệm Không Gian Boutique",
    "F_and_B": "Ẩm Thực & Bữa Sáng (F&B)",
    "Others": "Vận Hành & Giao Dịch Khác",
    "None": "Không Có Phàn Nàn",
    "Unknown": "Chưa Phân Loại",
}

def generate_dashboard() -> None:
    if not REPORT_JSON_FILE.exists() or not CSV_FILE.exists():
        print(f"Required input files missing: {REPORT_JSON_FILE} or {CSV_FILE}")
        return

    report_json_raw = REPORT_JSON_FILE.read_text(encoding="utf-8")
    report = json.loads(report_json_raw)
    
    df = pd.read_csv(CSV_FILE, encoding="utf-8-sig")
    
    reviews_list = []
    review_col = "review_text"
    for col in ["review_text", "Review", "review", "content", "text"]:
        if col in df.columns:
            review_col = col
            break

    for idx, row in df.iterrows():
        rating_val = 5
        raw_rating = str(row.get("rating", "")) if pd.notnull(row.get("rating")) else ""
        if raw_rating.isdigit():
            rating_val = int(raw_rating)
        elif "sao" in str(row.get("Đánh giá", "")):
            try:
                rating_val = int(str(row.get("Đánh giá", "")).split()[0])
            except (ValueError, IndexError):
                rating_val = 5

        cat_raw = str(row.get("category", "None")) if pd.notnull(row.get("category")) and str(row.get("category")) != "nan" else "None"
        reviews_list.append({
            "id": idx + 1,
            "reviewer_name": str(row.get("Tên", str(row.get("reviewer_name", f"Khách hàng #{idx+1}")))),
            "rating": rating_val,
            "review_text": str(row.get(review_col, "")),
            "sentiment": str(row.get("sentiment", "Unknown")) if pd.notnull(row.get("sentiment")) else "Unknown",
            "pain_point_flag": bool(row.get("pain_point_flag", False)) if pd.notnull(row.get("pain_point_flag")) else False,
            "category": cat_raw,
            "category_vi": CATEGORY_TRANSLATIONS.get(cat_raw, cat_raw),
            "summary": str(row.get("summary", "")) if pd.notnull(row.get("summary")) and str(row.get("summary")) != "nan" else "",
            "time_ago": str(row.get("Thời gian", "")) if pd.notnull(row.get("Thời gian")) else ""
        })

    report_json_str = json.dumps(report, ensure_ascii=False)
    reviews_json_str = json.dumps(reviews_list, ensure_ascii=False)
    cat_trans_json_str = json.dumps(CATEGORY_TRANSLATIONS, ensure_ascii=False)

    hotel_name = report.get("hotel_name", "Boutique Hotel Service Analysis")
    exec_summary = report.get("executive_summary", "")
    total_reviews = report.get("total_reviews_analyzed", 0)
    total_pain = report.get("total_pain_points", 0)
    pain_pct = round((total_pain / max(total_reviews, 1)) * 100, 1)
    
    sent_breakdown = report.get("overall_sentiment_breakdown", {})
    pos_count = sent_breakdown.get("Positive", 0)
    neu_count = sent_breakdown.get("Neutral", 0)
    neg_count = sent_breakdown.get("Negative", 0)
    
    pos_pct = round((pos_count / max(total_reviews, 1)) * 100, 1)
    neg_pct = round((neg_count / max(total_reviews, 1)) * 100, 1)
    net_sentiment = round(pos_pct - neg_pct, 1)
    net_sentiment_str = f"+{net_sentiment}%" if net_sentiment > 0 else f"{net_sentiment}%"

    action_items = report.get("action_items", [])
    high_priority_count = len([item for item in action_items if item.get("priority") == "High"])

    bhi_score = round(max(0, min(100, (pos_count * 10 + neu_count * 6 - neg_count * 10 - high_priority_count * 12) / max(total_reviews, 1) * 10)), 1)
    if bhi_score >= 80:
        bhi_status = "Xuất sắc (Excellent)"
        bhi_color = "#10b981"
    elif bhi_score >= 65:
        bhi_status = "Cần cải thiện (Needs Attention)"
        bhi_color = "#f59e0b"
    else:
        bhi_status = "Cảnh báo cao (High Risk)"
        bhi_color = "#f43f5e"

    html_content = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{hotel_name} - AI Executive Dashboard</title>
    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <!-- Font Awesome Icons -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <!-- Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

    <style>
        :root {{
            --bg-body: #090d16;
            --bg-card: rgba(18, 26, 43, 0.75);
            --bg-card-hover: rgba(26, 37, 60, 0.85);
            --border-card: rgba(255, 255, 255, 0.08);
            --border-glow: rgba(245, 158, 11, 0.25);
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --text-subtext: #64748b;
            
            --accent-gold: #f59e0b;
            --accent-gold-light: #fbbf24;
            --accent-indigo: #6366f1;
            --accent-purple: #8b5cf6;
            --accent-rose: #f43f5e;
            --accent-emerald: #10b981;
            --accent-cyan: #06b6d4;

            --radius-xl: 20px;
            --radius-lg: 14px;
            --radius-md: 10px;

            --shadow-glass: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
            --shadow-glow-gold: 0 0 25px rgba(245, 158, 11, 0.15);
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: 'Inter', sans-serif;
            background-color: var(--bg-body);
            background-image: 
                radial-gradient(at 0% 0%, rgba(245, 158, 11, 0.07) 0px, transparent 50%),
                radial-gradient(at 100% 0%, rgba(99, 102, 241, 0.1) 0px, transparent 50%),
                radial-gradient(at 50% 100%, rgba(244, 63, 94, 0.06) 0px, transparent 50%);
            background-attachment: fixed;
            color: var(--text-main);
            min-height: 100vh;
            padding: 1.5rem;
            line-height: 1.6;
        }}

        .container {{
            max-width: 1440px;
            margin: 0 auto;
        }}

        /* Header Bar */
        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1.25rem 1.75rem;
            background: var(--bg-card);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid var(--border-card);
            border-radius: var(--radius-xl);
            box-shadow: var(--shadow-glass);
            margin-bottom: 1.75rem;
            flex-wrap: wrap;
            gap: 1rem;
        }}

        .brand-section {{
            display: flex;
            align-items: center;
            gap: 1rem;
        }}

        .brand-icon {{
            width: 48px;
            height: 48px;
            border-radius: 12px;
            background: linear-gradient(135deg, rgba(245, 158, 11, 0.2), rgba(99, 102, 241, 0.2));
            border: 1px solid var(--accent-gold);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.4rem;
            color: var(--accent-gold);
            box-shadow: var(--shadow-glow-gold);
        }}

        .brand-title h1 {{
            font-family: 'Outfit', sans-serif;
            font-size: 1.5rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            background: linear-gradient(135deg, #ffffff 0%, #cbd5e1 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        .brand-title p {{
            font-size: 0.85rem;
            color: var(--text-muted);
            display: flex;
            align-items: center;
            gap: 0.4rem;
        }}

        .status-badge-container {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
            flex-wrap: wrap;
        }}

        .badge-pill {{
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.4rem 0.85rem;
            border-radius: 50px;
            font-size: 0.8rem;
            font-weight: 600;
            backdrop-filter: blur(8px);
        }}

        .badge-ai {{
            background: rgba(99, 102, 241, 0.15);
            color: #a5b4fc;
            border: 1px solid rgba(99, 102, 241, 0.3);
        }}

        .badge-boutique {{
            background: rgba(245, 158, 11, 0.15);
            color: #fcd34d;
            border: 1px solid rgba(245, 158, 11, 0.3);
        }}

        /* Executive Summary Banner */
        .exec-banner {{
            background: linear-gradient(135deg, rgba(30, 41, 67, 0.9), rgba(18, 26, 43, 0.85));
            backdrop-filter: blur(12px);
            border: 1px solid var(--border-card);
            border-left: 4px solid var(--accent-gold);
            border-radius: var(--radius-xl);
            padding: 1.5rem 1.75rem;
            margin-bottom: 1.75rem;
            box-shadow: var(--shadow-glass);
            position: relative;
            overflow: hidden;
        }}

        .exec-header {{
            display: flex;
            align-items: center;
            gap: 0.6rem;
            font-family: 'Outfit', sans-serif;
            font-size: 1.1rem;
            font-weight: 700;
            color: var(--accent-gold);
            margin-bottom: 0.6rem;
        }}

        .exec-content {{
            font-size: 0.95rem;
            color: #e2e8f0;
            line-height: 1.6;
        }}

        /* Top KPI Grid */
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 1.25rem;
            margin-bottom: 1.75rem;
        }}

        .kpi-card {{
            background: var(--bg-card);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border-card);
            border-radius: var(--radius-lg);
            padding: 1.35rem;
            box-shadow: var(--shadow-glass);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
        }}

        .kpi-card:hover {{
            transform: translateY(-4px);
            background: var(--bg-card-hover);
            border-color: rgba(255, 255, 255, 0.15);
        }}

        .kpi-head {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 0.8rem;
        }}

        .kpi-title {{
            font-size: 0.85rem;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}

        .kpi-icon {{
            width: 38px;
            height: 38px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.1rem;
        }}

        .icon-gold {{ background: rgba(245, 158, 11, 0.15); color: var(--accent-gold); }}
        .icon-emerald {{ background: rgba(16, 185, 129, 0.15); color: var(--accent-emerald); }}
        .icon-rose {{ background: rgba(244, 63, 94, 0.15); color: var(--accent-rose); }}
        .icon-indigo {{ background: rgba(99, 102, 241, 0.15); color: var(--accent-indigo); }}

        .kpi-val {{
            font-family: 'Outfit', sans-serif;
            font-size: 2.1rem;
            font-weight: 800;
            line-height: 1.1;
            margin-bottom: 0.4rem;
        }}

        .kpi-subtext {{
            font-size: 0.8rem;
            color: var(--text-subtext);
            display: flex;
            align-items: center;
            gap: 0.4rem;
        }}

        .kpi-subtext span {{
            font-weight: 600;
        }}

        /* Main Dashboard Grid */
        .dash-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1.5rem;
            margin-bottom: 1.75rem;
        }}

        .dash-card {{
            background: var(--bg-card);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border-card);
            border-radius: var(--radius-xl);
            padding: 1.5rem;
            box-shadow: var(--shadow-glass);
            display: flex;
            flex-direction: column;
        }}

        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.25rem;
            padding-bottom: 0.75rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }}

        .card-header h3 {{
            font-family: 'Outfit', sans-serif;
            font-size: 1.15rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 0.6rem;
        }}

        .chart-container {{
            position: relative;
            width: 100%;
            height: 280px;
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        /* Department SLA Matrix Section */
        .matrix-section {{
            background: var(--bg-card);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border-card);
            border-radius: var(--radius-xl);
            padding: 1.5rem;
            box-shadow: var(--shadow-glass);
            margin-bottom: 1.75rem;
        }}

        .dept-tabs {{
            display: flex;
            gap: 0.5rem;
            margin-bottom: 1.25rem;
            overflow-x: auto;
            padding-bottom: 0.4rem;
        }}

        .dept-tab-btn {{
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(255, 255, 255, 0.08);
            color: var(--text-muted);
            padding: 0.5rem 1rem;
            border-radius: 50px;
            font-size: 0.85rem;
            font-weight: 500;
            cursor: pointer;
            white-space: nowrap;
            transition: all 0.2s;
        }}

        .dept-tab-btn.active, .dept-tab-btn:hover {{
            background: rgba(245, 158, 11, 0.15);
            color: #fcd34d;
            border-color: rgba(245, 158, 11, 0.4);
        }}

        .action-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 1.25rem;
        }}

        .action-card {{
            background: rgba(12, 18, 30, 0.6);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: var(--radius-lg);
            padding: 1.25rem;
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
            transition: all 0.2s ease;
        }}

        .action-card:hover {{
            border-color: rgba(245, 158, 11, 0.3);
            background: rgba(20, 29, 48, 0.8);
        }}

        .action-head {{
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .priority-badge {{
            padding: 0.25rem 0.65rem;
            border-radius: 50px;
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
        }}

        .p-high {{
            background: rgba(244, 63, 94, 0.2);
            color: #fca5a5;
            border: 1px solid rgba(244, 63, 94, 0.4);
            animation: pulse-border 2s infinite;
        }}

        .p-med {{
            background: rgba(245, 158, 11, 0.2);
            color: #fde047;
            border: 1px solid rgba(245, 158, 11, 0.4);
        }}

        @keyframes pulse-border {{
            0% {{ box-shadow: 0 0 0 0 rgba(244, 63, 94, 0.4); }}
            70% {{ box-shadow: 0 0 0 8px rgba(244, 63, 94, 0); }}
            100% {{ box-shadow: 0 0 0 0 rgba(244, 63, 94, 0); }}
        }}

        .dept-tag {{
            font-size: 0.8rem;
            color: var(--text-muted);
            display: flex;
            align-items: center;
            gap: 0.4rem;
            font-weight: 600;
        }}

        .issue-title {{
            font-weight: 600;
            font-size: 0.95rem;
            color: #f1f5f9;
            line-height: 1.4;
        }}

        .action-body {{
            font-size: 0.85rem;
            color: #cbd5e1;
            background: rgba(0, 0, 0, 0.25);
            padding: 0.75rem;
            border-radius: var(--radius-md);
            border-left: 3px solid var(--accent-gold);
        }}

        .sla-pill {{
            align-self: flex-start;
            font-size: 0.75rem;
            color: #a5b4fc;
            background: rgba(99, 102, 241, 0.12);
            padding: 0.25rem 0.6rem;
            border-radius: 4px;
            display: inline-flex;
            align-items: center;
            gap: 0.3rem;
            font-weight: 600;
        }}

        /* Interactive Reviews Section */
        .reviews-section {{
            background: var(--bg-card);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border-card);
            border-radius: var(--radius-xl);
            padding: 1.5rem;
            box-shadow: var(--shadow-glass);
        }}

        .filter-controls {{
            display: grid;
            grid-template-columns: 2fr 1fr 1fr 1fr;
            gap: 0.85rem;
            margin-bottom: 1.25rem;
        }}

        .search-box input, .select-box select {{
            width: 100%;
            padding: 0.65rem 1rem;
            background: rgba(12, 18, 30, 0.7);
            border: 1px solid var(--border-card);
            border-radius: var(--radius-md);
            color: var(--text-main);
            font-size: 0.88rem;
            outline: none;
            transition: all 0.2s;
        }}

        .search-box input:focus, .select-box select:focus {{
            border-color: var(--accent-gold);
            box-shadow: 0 0 0 2px rgba(245, 158, 11, 0.2);
        }}

        .table-wrapper {{
            overflow-x: auto;
            border-radius: var(--radius-md);
            border: 1px solid rgba(255, 255, 255, 0.05);
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.88rem;
            text-align: left;
        }}

        th {{
            background: rgba(12, 18, 30, 0.9);
            color: var(--text-muted);
            font-weight: 600;
            padding: 0.85rem 1rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            white-space: nowrap;
        }}

        td {{
            padding: 0.9rem 1rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
            vertical-align: top;
        }}

        tr:hover td {{
            background: rgba(255, 255, 255, 0.02);
        }}

        /* Mobile Cards */
        .mobile-review-cards {{
            display: none;
            flex-direction: column;
            gap: 1rem;
        }}

        .m-review-card {{
            background: rgba(12, 18, 30, 0.7);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: var(--radius-lg);
            padding: 1.1rem;
            display: flex;
            flex-direction: column;
            gap: 0.6rem;
        }}

        .m-card-top {{
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .star-rating {{
            color: var(--accent-gold);
            font-size: 0.85rem;
        }}

        .badge {{
            display: inline-block;
            padding: 0.2rem 0.6rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
        }}

        .badge-pos {{ background: rgba(16, 185, 129, 0.15); color: #6ee7b7; border: 1px solid rgba(16, 185, 129, 0.3); }}
        .badge-neu {{ background: rgba(148, 163, 184, 0.15); color: #cbd5e1; border: 1px solid rgba(148, 163, 184, 0.3); }}
        .badge-neg {{ background: rgba(244, 63, 94, 0.15); color: #fca5a5; border: 1px solid rgba(244, 63, 94, 0.3); }}
        .badge-cat {{ background: rgba(99, 102, 241, 0.15); color: #c7d2fe; border: 1px solid rgba(99, 102, 241, 0.3); }}

        /* Pagination */
        .pagination {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 1.25rem;
            flex-wrap: wrap;
            gap: 0.75rem;
        }}

        .page-info {{
            font-size: 0.85rem;
            color: var(--text-muted);
        }}

        .page-btns {{
            display: flex;
            gap: 0.5rem;
        }}

        .btn-page {{
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--border-card);
            color: var(--text-main);
            padding: 0.45rem 0.9rem;
            border-radius: var(--radius-md);
            font-size: 0.82rem;
            cursor: pointer;
            transition: all 0.2s;
        }}

        .btn-page:hover:not(:disabled) {{
            background: var(--accent-gold);
            color: #000;
            font-weight: 600;
        }}

        .btn-page:disabled {{
            opacity: 0.4;
            cursor: not-allowed;
        }}

        /* Responsive Breakpoints */
        @media (max-width: 1024px) {{
            .kpi-grid {{
                grid-template-columns: repeat(2, 1fr);
            }}
            .dash-grid {{
                grid-template-columns: 1fr;
            }}
            .filter-controls {{
                grid-template-columns: 1fr 1fr;
            }}
        }}

        @media (max-width: 768px) {{
            body {{
                padding: 0.85rem;
            }}
            header {{
                padding: 1rem;
            }}
            .brand-title h1 {{
                font-size: 1.25rem;
            }}
            .kpi-grid {{
                grid-template-columns: 1fr;
            }}
            .filter-controls {{
                grid-template-columns: 1fr;
            }}
            .table-wrapper {{
                display: none;
            }}
            .mobile-review-cards {{
                display: flex;
            }}
            .action-grid {{
                grid-template-columns: 1fr;
            }}
        }}

        @media (max-width: 480px) {{
            .exec-banner {{
                padding: 1.1rem;
            }}
            .kpi-val {{
                font-size: 1.8rem;
            }}
        }}
    </style>
</head>
<body>

<div class="container">
    <!-- Header -->
    <header>
        <div class="brand-section">
            <div class="brand-icon">
                <i class="fa-solid fa-hotel"></i>
            </div>
            <div class="brand-title">
                <h1>{hotel_name}</h1>
                <p><i class="fa-solid fa-brain" style="color: var(--accent-gold);"></i> AI Review Intelligence & Operational SLA Dashboard</p>
            </div>
        </div>
        <div class="status-badge-container">
            <span class="badge-pill badge-boutique"><i class="fa-solid fa-crown"></i> Boutique Standard</span>
            <span class="badge-pill badge-ai"><i class="fa-solid fa-bolt"></i> Live AI Analytics</span>
        </div>
    </header>

    <!-- Executive Summary Banner -->
    <div class="exec-banner">
        <div class="exec-header">
            <i class="fa-solid fa-wand-magic-sparkles"></i> Tóm Tắt Chiến Lược Dịch Vụ (Executive AI Summary)
        </div>
        <div class="exec-content">
            {exec_summary}
        </div>
    </div>

    <!-- Top KPI Grid -->
    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="kpi-head">
                <span class="kpi-title">Boutique Health Index</span>
                <div class="kpi-icon icon-gold"><i class="fa-solid fa-award"></i></div>
            </div>
            <div class="kpi-val" style="color: {bhi_color};">{bhi_score} <span style="font-size: 1.1rem; color: var(--text-muted);">/100</span></div>
            <div class="kpi-subtext">Đánh giá tổng quan: <span style="color: {bhi_color};">{bhi_status}</span></div>
        </div>

        <div class="kpi-card">
            <div class="kpi-head">
                <span class="kpi-title">Net Sentiment Score</span>
                <div class="kpi-icon icon-emerald"><i class="fa-solid fa-chart-line"></i></div>
            </div>
            <div class="kpi-val" style="color: {"#10b981" if net_sentiment >= 0 else "#f43f5e"};">{net_sentiment_str}</div>
            <div class="kpi-subtext">Tích cực: <span style="color: #6ee7b7;">{pos_pct}%</span> | Tiêu cực: <span style="color: #fca5a5;">{neg_pct}%</span></div>
        </div>

        <div class="kpi-card">
            <div class="kpi-head">
                <span class="kpi-title">Rủi Ro SLA Cao</span>
                <div class="kpi-icon icon-rose"><i class="fa-solid fa-triangle-exclamation"></i></div>
            </div>
            <div class="kpi-val" style="color: var(--accent-rose);">{high_priority_count} <span style="font-size: 1.1rem; color: var(--text-muted);">Sự cố</span></div>
            <div class="kpi-subtext">Cần khắc phục ngay trong <span style="color: #fca5a5;">24h - 3 ngày</span></div>
        </div>

        <div class="kpi-card">
            <div class="kpi-head">
                <span class="kpi-title">Tỷ Lệ Khiếu Nại</span>
                <div class="kpi-icon icon-indigo"><i class="fa-solid fa-comments"></i></div>
            </div>
            <div class="kpi-val" style="color: var(--accent-gold);">{pain_pct}%</div>
            <div class="kpi-subtext"><span style="color: #fcd34d;">{total_pain} / {total_reviews}</span> phản hồi chứa góp ý/phàn nàn</div>
        </div>
    </div>

    <!-- Main Analytics Charts Grid -->
    <div class="dash-grid">
        <div class="dash-card">
            <div class="card-header">
                <h3><i class="fa-solid fa-pie-chart" style="color: var(--accent-gold);"></i> Phân Bổ Cảm Xúc Khách Hàng</h3>
                <span style="font-size: 0.8rem; color: var(--text-muted);">Tổng số: {total_reviews} reviews</span>
            </div>
            <div class="chart-container">
                <canvas id="sentimentChart"></canvas>
            </div>
        </div>

        <div class="dash-card">
            <div class="card-header">
                <h3><i class="fa-solid fa-chart-bar" style="color: var(--accent-indigo);"></i> Nhóm Vấn Đề Khiếu Nại Hàng Đầu</h3>
                <span style="font-size: 0.8rem; color: var(--text-muted);">Theo tỷ lệ góp ý</span>
            </div>
            <div class="chart-container">
                <canvas id="categoryChart"></canvas>
            </div>
        </div>
    </div>

    <!-- Departmental SLA Action Plan Matrix -->
    <div class="matrix-section">
        <div class="card-header">
            <h3><i class="fa-solid fa-list-check" style="color: var(--accent-gold);"></i> Ma Trận Hành Động & Thời Hạn Xử Lý Theo Phòng Ban (SLA)</h3>
            <span style="font-size: 0.8rem; color: var(--text-muted);">Ưu tiên giải quyết khiếu nại khách hàng</span>
        </div>

        <div class="dept-tabs">
            <button class="dept-tab-btn active" onclick="filterDept('ALL')">Tất cả phòng ban</button>
            <button class="dept-tab-btn" onclick="filterDept('Housekeeping')">🧹 Housekeeping</button>
            <button class="dept-tab-btn" onclick="filterDept('Ban Quản Lý & Kế Toán')">👔 Quản Lý & Kế Toán</button>
            <button class="dept-tab-btn" onclick="filterDept('Bảo Trì')">🛠 Bảo Trì</button>
            <button class="dept-tab-btn" onclick="filterDept('Lễ Tân')">🛎 Lễ Tân & Nhân Sự</button>
        </div>

        <div class="action-grid" id="actionItemsGrid">
            <!-- Action Cards dynamic rendering -->
        </div>
    </div>

    <!-- Interactive Reviews Table Section -->
    <div class="reviews-section">
        <div class="card-header">
            <h3><i class="fa-solid fa-magnifying-glass" style="color: var(--accent-indigo);"></i> Danh Sách Chi Tiết & Tra Cứu Đánh Giá</h3>
            <span style="font-size: 0.8rem; color: var(--text-muted);">Bộ lọc thời gian thực</span>
        </div>

        <div class="filter-controls">
            <div class="search-box">
                <input type="text" id="searchInput" placeholder="🔍 Tìm kiếm nội dung đánh giá hoặc tóm tắt..." onkeyup="applyFilters()">
            </div>
            <div class="select-box">
                <select id="sentimentFilter" onchange="applyFilters()">
                    <option value="ALL">Tất cả Cảm xúc</option>
                    <option value="Positive">Positive (Tích cực)</option>
                    <option value="Neutral">Neutral (Trung lập)</option>
                    <option value="Negative">Negative (Tiêu cực)</option>
                </select>
            </div>
            <div class="select-box">
                <select id="painFilter" onchange="applyFilters()">
                    <option value="ALL">Tất cả Khiếu nại</option>
                    <option value="PAIN">Có khiếu nại</option>
                    <option value="NORMAL">Bình thường</option>
                </select>
            </div>
            <div class="select-box">
                <select id="categoryFilter" onchange="applyFilters()">
                    <option value="ALL">Tất cả Danh mục (Việt hóa)</option>
                    <option value="Room_Amenities">Tiện Nghi Phòng Ở</option>
                    <option value="Location_and_Access">Vị Trí & Di Chuyển</option>
                    <option value="Cleanliness">Vệ Sinh Phòng Ở</option>
                    <option value="Staff_Service">Dịch Vụ & Thái Độ Nhân Viên</option>
                    <option value="Pricing_and_Fees">Chi Phí & Phụ Phí Minh Bạch</option>
                    <option value="Noise_and_Quietness">Độ Cách Âm & Yên Tĩnh</option>
                    <option value="Boutique_Experience">Trải Nghiệm Không Gian Boutique</option>
                    <option value="F_and_B">Ẩm Thực & Bữa Sáng (F&B)</option>
                    <option value="Others">Vận Hành & Giao Dịch Khác</option>
                </select>
            </div>
        </div>

        <!-- Desktop Table View -->
        <div class="table-wrapper">
            <table>
                <thead>
                    <tr>
                        <th style="width: 60px;">ID</th>
                        <th style="width: 110px;">Cảm xúc</th>
                        <th style="width: 120px;">Xếp hạng</th>
                        <th style="width: 170px;">Danh mục (Tiếng Việt)</th>
                        <th>Nội dung Đánh giá</th>
                        <th style="width: 320px;">Tóm tắt AI</th>
                    </tr>
                </thead>
                <tbody id="reviewsTableBody">
                    <!-- Dynamic Rows -->
                </tbody>
            </table>
        </div>

        <!-- Mobile Responsive Card View -->
        <div class="mobile-review-cards" id="mobileCardsContainer">
            <!-- Dynamic Cards for Mobile -->
        </div>

        <!-- Pagination Bar -->
        <div class="pagination">
            <div class="page-info" id="pageInfo">Đang tải...</div>
            <div class="page-btns">
                <button class="btn-page" id="prevBtn" onclick="changePage(-1)"><i class="fa-solid fa-chevron-left"></i> Trang trước</button>
                <button class="btn-page" id="nextBtn" onclick="changePage(1)">Trang sau <i class="fa-solid fa-chevron-right"></i></button>
            </div>
        </div>
    </div>
</div>

<script>
    const reportData = {report_json_str};
    const reviewsData = {reviews_json_str};
    const catTranslations = {cat_trans_json_str};

    let filteredReviews = [...reviewsData];
    let currentPage = 1;
    const pageSize = 6;
    let selectedDept = 'ALL';

    document.addEventListener('DOMContentLoaded', () => {{
        initCharts();
        renderActionItems();
        applyFilters();
    }});

    function initCharts() {{
        // Sentiment Donut Chart
        const ctxSent = document.getElementById('sentimentChart').getContext('2d');
        new Chart(ctxSent, {{
            type: 'doughnut',
            data: {{
                labels: ['Tích cực (Positive)', 'Trung lập (Neutral)', 'Tiêu cực (Negative)'],
                datasets: [{{
                    data: [{pos_count}, {neu_count}, {neg_count}],
                    backgroundColor: ['#10b981', '#94a3b8', '#f43f5e'],
                    borderWidth: 2,
                    borderColor: '#090d16'
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        position: 'bottom',
                        labels: {{ color: '#cbd5e1', font: {{ family: 'Inter', size: 12 }} }}
                    }}
                }},
                cutout: '70%'
            }}
        }});

        // Category Bar Chart (Translated to Vietnamese)
        const catLabels = [];
        const catCounts = [];
        if (reportData.category_insights) {{
            reportData.category_insights.forEach(item => {{
                const catVi = catTranslations[item.category] || item.category;
                catLabels.push(catVi);
                catCounts.push(item.complaint_count);
            }});
        }}

        const ctxCat = document.getElementById('categoryChart').getContext('2d');
        new Chart(ctxCat, {{
            type: 'bar',
            data: {{
                labels: catLabels,
                datasets: [{{
                    label: 'Số lượt phàn nàn',
                    data: catCounts,
                    backgroundColor: ['rgba(245, 158, 11, 0.85)', 'rgba(99, 102, 241, 0.85)', 'rgba(244, 63, 94, 0.85)', 'rgba(16, 185, 129, 0.85)', 'rgba(6, 182, 212, 0.85)'],
                    borderRadius: 6
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ display: false }}
                }},
                scales: {{
                    x: {{ ticks: {{ color: '#94a3b8' }}, grid: {{ display: false }} }},
                    y: {{ ticks: {{ color: '#94a3b8', stepSize: 1 }}, grid: {{ color: 'rgba(255, 255, 255, 0.05)' }} }}
                }}
            }}
        }});
    }}

    function renderActionItems() {{
        const grid = document.getElementById('actionItemsGrid');
        grid.innerHTML = '';

        const items = reportData.action_items || [];
        const filtered = selectedDept === 'ALL' ? items : items.filter(i => i.department.toLowerCase().includes(selectedDept.toLowerCase()));

        if (filtered.length === 0) {{
            grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 2rem;">Không có kế hoạch hành động thuộc phòng ban này.</div>';
            return;
        }}

        filtered.forEach(item => {{
            const card = document.createElement('div');
            card.className = 'action-card';
            const pClass = item.priority === 'High' ? 'p-high' : 'p-med';
            
            card.innerHTML = `
                <div class="action-head">
                    <span class="priority-badge ${{pClass}}">${{item.priority}} Priority</span>
                    <span class="dept-tag"><i class="fa-solid fa-sitemap"></i> ${{item.department}}</span>
                </div>
                <div class="issue-title">${{item.issue}}</div>
                <div class="action-body">
                    <strong>Hành động:</strong> ${{item.action_plan}}
                </div>
                <div class="sla-pill"><i class="fa-regular fa-clock"></i> Thời hạn SLA: ${{item.timeline}}</div>
            `;
            grid.appendChild(card);
        }});
    }}

    function filterDept(dept) {{
        selectedDept = dept;
        document.querySelectorAll('.dept-tab-btn').forEach(btn => btn.classList.remove('active'));
        event.target.classList.add('active');
        renderActionItems();
    }}

    function applyFilters() {{
        const search = document.getElementById('searchInput').value.toLowerCase();
        const sent = document.getElementById('sentimentFilter').value;
        const pain = document.getElementById('painFilter').value;
        const cat = document.getElementById('categoryFilter').value;

        filteredReviews = reviewsData.filter(r => {{
            const matchSearch = r.review_text.toLowerCase().includes(search) || (r.summary && r.summary.toLowerCase().includes(search));
            const matchSent = sent === 'ALL' || r.sentiment === sent;
            const matchPain = pain === 'ALL' || (pain === 'PAIN' && r.pain_point_flag) || (pain === 'NORMAL' && !r.pain_point_flag);
            const matchCat = cat === 'ALL' || r.category === cat;
            return matchSearch && matchSent && matchPain && matchCat;
        }});

        currentPage = 1;
        renderReviews();
    }}

    function renderReviews() {{
        const tbody = document.getElementById('reviewsTableBody');
        const mContainer = document.getElementById('mobileCardsContainer');
        tbody.innerHTML = '';
        mContainer.innerHTML = '';

        const start = (currentPage - 1) * pageSize;
        const end = start + pageSize;
        const pageItems = filteredReviews.slice(start, end);

        if (pageItems.length === 0) {{
            const emptyHtml = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 2rem;">Không tìm thấy đánh giá nào phù hợp.</td></tr>';
            tbody.innerHTML = emptyHtml;
            mContainer.innerHTML = '<div style="text-align: center; color: var(--text-muted); padding: 2rem;">Không tìm thấy đánh giá phù hợp.</div>';
        }} else {{
            pageItems.forEach(r => {{
                let sentBadge = r.sentiment === 'Positive' ? 'badge-pos' : (r.sentiment === 'Negative' ? 'badge-neg' : 'badge-neu');
                
                const catVi = r.category_vi || catTranslations[r.category] || r.category;
                let catBadge = r.category && r.category !== 'None' ? `<span class="badge badge-cat">${{catVi}}</span>` : '-';
                
                let stars = '';
                for (let i = 1; i <= 5; i++) {{
                    stars += i <= r.rating ? '<i class="fa-solid fa-star"></i>' : '<i class="fa-regular fa-star" style="opacity:0.3;"></i>';
                }}

                // Desktop Row
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td><strong>#${{r.id}}</strong></td>
                    <td><span class="badge ${{sentBadge}}">${{r.sentiment}}</span></td>
                    <td class="star-rating">${{stars}}</td>
                    <td>${{catBadge}}</td>
                    <td>${{r.review_text}}</td>
                    <td style="color: #cbd5e1; font-style: italic;">${{r.summary || '-'}}</td>
                `;
                tbody.appendChild(tr);

                // Mobile Card
                const mCard = document.createElement('div');
                mCard.className = 'm-review-card';
                mCard.innerHTML = `
                    <div class="m-card-top">
                        <span class="badge ${{sentBadge}}">${{r.sentiment}}</span>
                        <div class="star-rating">${{stars}}</div>
                    </div>
                    <div style="font-size: 0.8rem; color: #a5b4fc;">🏷 Danh mục: <strong>${{catVi}}</strong></div>
                    <div style="font-size: 0.9rem; color: #f1f5f9;">${{r.review_text}}</div>
                    <div style="font-size: 0.8rem; color: #cbd5e1; font-style: italic; background: rgba(0,0,0,0.2); padding: 0.5rem; border-radius: 6px;">
                        💡 Tóm tắt AI: ${{r.summary || 'Không có'}}
                    </div>
                `;
                mContainer.appendChild(mCard);
            }});
        }}

        const total = filteredReviews.length;
        const totalPages = Math.ceil(total / pageSize) || 1;
        document.getElementById('pageInfo').textContent = `Hiển thị ${{total > 0 ? start + 1 : 0}} - ${{Math.min(end, total)}} trên tổng số ${{total}} đánh giá`;
        document.getElementById('prevBtn').disabled = currentPage === 1;
        document.getElementById('nextBtn').disabled = currentPage >= totalPages;
    }}

    function changePage(delta) {{
        currentPage += delta;
        renderReviews();
    }}
</script>

</body>
</html>
"""

    DASHBOARD_HTML_FILE.write_text(html_content, encoding="utf-8")
    root_index = PROJECT_ROOT / "index.html"
    root_index.write_text(html_content, encoding="utf-8")
    print(f"Successfully generated localized responsive dashboard HTML to {DASHBOARD_HTML_FILE} and {root_index}")

if __name__ == "__main__":
    generate_dashboard()
