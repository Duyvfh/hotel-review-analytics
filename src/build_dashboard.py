"""Interactive Web Dashboard Generator for Boutique Hotel Review AI Analytics."""

import json
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"

REPORT_JSON_FILE = OUTPUT_DIR / "hotel_improvement_report.json" if (OUTPUT_DIR / "hotel_improvement_report.json").exists() else PROJECT_ROOT / "hotel_improvement_report.json"
CSV_FILE = OUTPUT_DIR / "analyzed_reviews.csv" if (OUTPUT_DIR / "analyzed_reviews.csv").exists() else PROJECT_ROOT / "analyzed_reviews.csv"
DASHBOARD_HTML_FILE = OUTPUT_DIR / "index.html"

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
        reviews_list.append({
            "id": idx + 1,
            "reviewer_name": str(row.get("reviewer_name", f"Guest #{idx+1}")),
            "rating": int(row.get("rating")) if pd.notnull(row.get("rating")) and str(row.get("rating")).isdigit() else 5,
            "review_text": str(row.get(review_col, "")),
            "sentiment": str(row.get("sentiment", "Unknown")) if pd.notnull(row.get("sentiment")) else "Unknown",
            "pain_point_flag": bool(row.get("pain_point_flag", False)) if pd.notnull(row.get("pain_point_flag")) else False,
            "category": str(row.get("category", "None")) if pd.notnull(row.get("category")) and str(row.get("category")) != "nan" else "None",
            "summary": str(row.get("summary", "")) if pd.notnull(row.get("summary")) and str(row.get("summary")) != "nan" else "",
        })

    report_json_str = json.dumps(report, ensure_ascii=False)
    reviews_json_str = json.dumps(reviews_list, ensure_ascii=False)

    hotel_name = report.get("hotel_name", "Boutique Hotel")
    exec_summary = report.get("executive_summary", "")
    total_reviews = report.get("total_reviews_analyzed", 0)
    total_pain = report.get("total_pain_points", 0)
    pain_pct = round((total_pain / max(total_reviews, 1)) * 100, 1)
    
    sent_breakdown = report.get("overall_sentiment_breakdown", {})
    pos_count = sent_breakdown.get("Positive", 0)
    neu_count = sent_breakdown.get("Neutral", 0)
    neg_count = sent_breakdown.get("Negative", 0)
    
    high_priority_count = len([item for item in report.get("action_items", []) if item.get("priority") == "High"])

    html_content = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Boutique Hotel Service Analytics Dashboard</title>
    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <!-- Font Awesome Icons -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <!-- Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

    <style>
        :root {
            --bg-body: #0b0f19;
            --bg-card: rgba(22, 30, 49, 0.75);
            --bg-card-hover: rgba(30, 41, 67, 0.85);
            --border-card: rgba(255, 255, 255, 0.08);
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --accent-indigo: #6366f1;
            --accent-purple: #8b5cf6;
            --accent-rose: #f43f5e;
            --accent-emerald: #10b981;
            --accent-amber: #f59e0b;
            --accent-cyan: #06b6d4;
            --radius-lg: 16px;
            --radius-md: 10px;
            --shadow-glow: 0 0 25px rgba(99, 102, 241, 0.15);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Inter', sans-serif;
            background-color: var(--bg-body);
            background-image: 
                radial-gradient(at 10% 10%, rgba(99, 102, 241, 0.12) 0px, transparent 50%),
                radial-gradient(at 90% 90%, rgba(244, 63, 94, 0.08) 0px, transparent 50%);
            color: var(--text-main);
            min-height: 100vh;
            padding: 2rem 1.5rem;
            line-height: 1.5;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
        }

        /* Header */
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2rem;
            padding-bottom: 1.5rem;
            border-bottom: 1px solid var(--border-card);
            flex-wrap: wrap;
            gap: 1rem;
        }

        .header-title h1 {
            font-family: 'Outfit', sans-serif;
            font-size: 2rem;
            font-weight: 800;
            background: linear-gradient(135deg, #ffffff 0%, #a5b4fc 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        .header-title p {
            color: var(--text-muted);
            font-size: 0.9rem;
            margin-top: 0.25rem;
        }

        .badge-model {
            background: rgba(99, 102, 241, 0.15);
            border: 1px solid rgba(99, 102, 241, 0.3);
            color: #c7d2fe;
            padding: 0.35rem 0.85rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
        }

        .btn-action {
            background: linear-gradient(135deg, var(--accent-indigo), var(--accent-purple));
            color: white;
            border: none;
            padding: 0.65rem 1.25rem;
            border-radius: var(--radius-md);
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.9rem;
            box-shadow: 0 4px 14px rgba(99, 102, 241, 0.35);
        }

        .btn-action:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(99, 102, 241, 0.5);
        }

        /* KPI Cards Grid */
        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
            gap: 1.25rem;
            margin-bottom: 2rem;
        }

        .kpi-card {
            background: var(--bg-card);
            backdrop-filter: blur(16px);
            border: 1px solid var(--border-card);
            border-radius: var(--radius-lg);
            padding: 1.5rem;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }

        .kpi-card:hover {
            background: var(--bg-card-hover);
            transform: translateY(-3px);
            border-color: rgba(255, 255, 255, 0.15);
            box-shadow: var(--shadow-glow);
        }

        .kpi-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 4px;
            height: 100%;
            background: var(--accent-indigo);
        }

        .kpi-card.rose::before { background: var(--accent-rose); }
        .kpi-card.amber::before { background: var(--accent-amber); }
        .kpi-card.emerald::before { background: var(--accent-emerald); }

        .kpi-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            color: var(--text-muted);
            font-size: 0.85rem;
            font-weight: 500;
            margin-bottom: 0.75rem;
        }

        .kpi-icon {
            width: 42px;
            height: 42px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2rem;
            background: rgba(255, 255, 255, 0.05);
        }

        .kpi-value {
            font-family: 'Outfit', sans-serif;
            font-size: 2.25rem;
            font-weight: 800;
            color: #ffffff;
            line-height: 1.1;
        }

        .kpi-subtext {
            font-size: 0.8rem;
            color: var(--text-muted);
            margin-top: 0.5rem;
        }

        /* Executive Banner */
        .exec-banner {
            background: linear-gradient(135deg, rgba(30, 41, 67, 0.9), rgba(15, 23, 42, 0.9));
            border: 1px solid rgba(99, 102, 241, 0.25);
            border-radius: var(--radius-lg);
            padding: 1.5rem 1.75rem;
            margin-bottom: 2rem;
            position: relative;
            backdrop-filter: blur(16px);
        }

        .exec-banner h2 {
            font-family: 'Outfit', sans-serif;
            font-size: 1.15rem;
            color: #c7d2fe;
            margin-bottom: 0.5rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .exec-banner p {
            color: #e2e8f0;
            font-size: 0.95rem;
            line-height: 1.6;
        }

        /* Charts Layout */
        .charts-grid {
            display: grid;
            grid-template-columns: 1fr 1.5fr;
            gap: 1.5rem;
            margin-bottom: 2rem;
        }

        @media (max-width: 992px) {
            .charts-grid {
                grid-template-columns: 1fr;
            }
        }

        .chart-card {
            background: var(--bg-card);
            backdrop-filter: blur(16px);
            border: 1px solid var(--border-card);
            border-radius: var(--radius-lg);
            padding: 1.5rem;
            display: flex;
            flex-direction: column;
        }

        .chart-card h3 {
            font-family: 'Outfit', sans-serif;
            font-size: 1.1rem;
            font-weight: 700;
            margin-bottom: 1.25rem;
            color: #f1f5f9;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .chart-wrapper {
            position: relative;
            flex: 1;
            min-height: 340px;
            display: flex;
            align-items: center;
            justify-content: center;
            padding-bottom: 0.5rem;
        }

        /* Table Section */
        .section-card {
            background: var(--bg-card);
            backdrop-filter: blur(16px);
            border: 1px solid var(--border-card);
            border-radius: var(--radius-lg);
            padding: 1.5rem;
            margin-bottom: 2rem;
        }

        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.25rem;
            flex-wrap: wrap;
            gap: 1rem;
        }

        .section-header h3 {
            font-family: 'Outfit', sans-serif;
            font-size: 1.2rem;
            font-weight: 700;
            color: #f1f5f9;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        /* Filter Controls */
        .controls-row {
            display: flex;
            gap: 0.75rem;
            flex-wrap: wrap;
            align-items: center;
        }

        .search-box {
            position: relative;
            min-width: 240px;
        }

        .search-box input {
            width: 100%;
            background: rgba(15, 23, 42, 0.8);
            border: 1px solid var(--border-card);
            padding: 0.55rem 1rem 0.55rem 2.4rem;
            border-radius: var(--radius-md);
            color: white;
            font-size: 0.85rem;
            outline: none;
            transition: border-color 0.2s;
        }

        .search-box input:focus {
            border-color: var(--accent-indigo);
        }

        .search-box i {
            position: absolute;
            left: 0.85rem;
            top: 50%;
            transform: translateY(-50%);
            color: var(--text-muted);
            font-size: 0.85rem;
        }

        .filter-select {
            background: rgba(15, 23, 42, 0.8);
            border: 1px solid var(--border-card);
            padding: 0.55rem 1rem;
            border-radius: var(--radius-md);
            color: white;
            font-size: 0.85rem;
            outline: none;
            cursor: pointer;
        }

        /* Custom Table */
        .table-responsive {
            overflow-x: auto;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            text-align: left;
            font-size: 0.875rem;
        }

        th {
            background: rgba(15, 23, 42, 0.9);
            color: var(--text-muted);
            font-weight: 600;
            padding: 0.85rem 1rem;
            border-bottom: 1px solid var(--border-card);
            text-transform: uppercase;
            font-size: 0.75rem;
            letter-spacing: 0.05em;
        }

        td {
            padding: 1rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
            color: #cbd5e1;
            vertical-align: top;
        }

        tr:hover td {
            background: rgba(255, 255, 255, 0.02);
        }

        /* Badges */
        .badge {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.25rem 0.65rem;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 600;
        }

        .badge-high {
            background: rgba(244, 63, 94, 0.15);
            color: #fca5a5;
            border: 1px solid rgba(244, 63, 94, 0.3);
        }

        .badge-medium {
            background: rgba(245, 158, 11, 0.15);
            color: #fde047;
            border: 1px solid rgba(245, 158, 11, 0.3);
        }

        .badge-low {
            background: rgba(16, 185, 129, 0.15);
            color: #6ee7b7;
            border: 1px solid rgba(16, 185, 129, 0.3);
        }

        .badge-cat {
            background: rgba(99, 102, 241, 0.12);
            color: #a5b4fc;
            border: 1px solid rgba(99, 102, 241, 0.25);
        }

        .badge-pos { background: rgba(16, 185, 129, 0.15); color: #34d399; }
        .badge-neu { background: rgba(245, 158, 11, 0.15); color: #fbbf24; }
        .badge-neg { background: rgba(244, 63, 94, 0.15); color: #f87171; }

        /* Pagination */
        .pagination {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 1.25rem;
            padding-top: 1rem;
            border-top: 1px solid var(--border-card);
            color: var(--text-muted);
            font-size: 0.85rem;
        }

        .page-btn {
            background: rgba(15, 23, 42, 0.8);
            border: 1px solid var(--border-card);
            color: white;
            padding: 0.4rem 0.85rem;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.8rem;
            transition: all 0.2s;
        }

        .page-btn:disabled {
            opacity: 0.4;
            cursor: not-allowed;
        }

        .page-btn:not(:disabled):hover {
            background: var(--accent-indigo);
            border-color: var(--accent-indigo);
        }
    </style>
</head>
<body>

<div class="container">
    <!-- Header -->
    <header>
        <div class="header-title">
            <h1><i class="fa-solid fa-hotel" style="color: var(--accent-indigo);"></i> """ + hotel_name + """</h1>
            <p>Báo cáo Chiến lược AI Analytics & Khảo sát Phản hồi Khách hàng</p>
        </div>
        <div style="display: flex; align-items: center; gap: 1rem;">
            <span class="badge-model"><i class="fa-solid fa-microchip"></i> Model: Gemini 3.1 Flash Lite</span>
            <button class="btn-action" onclick="window.print()"><i class="fa-solid fa-print"></i> Xuất Báo Cáo</button>
        </div>
    </header>

    <!-- Executive Summary Banner -->
    <div class="exec-banner">
        <h2><i class="fa-solid fa-lightbulb" style="color: var(--accent-amber);"></i> 📌 Đánh Giá Tổng Quan Từ AI Agent</h2>
        <p>""" + exec_summary + """</p>
    </div>

    <!-- KPI Cards Grid -->
    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="kpi-header">
                <span>TỔNG SỐ ĐÁNH GIÁ</span>
                <div class="kpi-icon" style="color: var(--accent-indigo);"><i class="fa-solid fa-comments"></i></div>
            </div>
            <div class="kpi-value">""" + str(total_reviews) + """</div>
            <div class="kpi-subtext">Đã thu thập từ file dữ liệu review.csv</div>
        </div>

        <div class="kpi-card rose">
            <div class="kpi-header">
                <span>TỔNG SỐ KHIẾU NẠI (PAIN POINTS)</span>
                <div class="kpi-icon" style="color: var(--accent-rose);"><i class="fa-solid fa-triangle-exclamation"></i></div>
            </div>
            <div class="kpi-value">""" + str(total_pain) + """</div>
            <div class="kpi-subtext">Chiếm """ + str(pain_pct) + """% tổng số phản hồi khách hàng</div>
        </div>

        <div class="kpi-card amber">
            <div class="kpi-header">
                <span>TỶ LỆ TIÊU CỰC (NEGATIVE)</span>
                <div class="kpi-icon" style="color: var(--accent-amber);"><i class="fa-solid fa-face-frown"></i></div>
            </div>
            <div class="kpi-value">""" + str(neg_count) + """</div>
            <div class="kpi-subtext">🟢 """ + str(pos_count) + """ Tích cực | 🟡 """ + str(neu_count) + """ Trung tính</div>
        </div>

        <div class="kpi-card emerald">
            <div class="kpi-header">
                <span>HÀNH ĐỘNG ƯU TIÊN CAO (SLA &lt; 3D)</span>
                <div class="kpi-icon" style="color: var(--accent-emerald);"><i class="fa-solid fa-bolt"></i></div>
            </div>
            <div class="kpi-value">""" + str(high_priority_count) + """</div>
            <div class="kpi-subtext">Các vấn đề Deal-breaker cần khắc phục ngay</div>
        </div>
    </div>

    <!-- Charts Row -->
    <div class="charts-grid">
        <!-- Donut Chart: Sentiment -->
        <div class="chart-card">
            <h3><i class="fa-solid fa-chart-pie" style="color: var(--accent-indigo);"></i> Phân Phối Cảm Xúc Khách Hàng</h3>
            <div class="chart-wrapper">
                <canvas id="sentimentChart"></canvas>
            </div>
        </div>

        <!-- Bar Chart: Category Breakdown -->
        <div class="chart-card">
            <h3><i class="fa-solid fa-chart-simple" style="color: var(--accent-purple);"></i> Phân Bố Khiếu Nại Theo Nhóm Dịch Vụ Boutique</h3>
            <div class="chart-wrapper">
                <canvas id="categoryChart"></canvas>
            </div>
        </div>
    </div>

    <!-- Action Plan SLA Section -->
    <div class="section-card">
        <div class="section-header">
            <h3><i class="fa-solid fa-list-check" style="color: var(--accent-emerald);"></i> 🛠️ Kế Hoạch Hành Động Khắc Phục Dịch Vụ (SLA Matrix)</h3>
        </div>
        <div class="table-responsive">
            <table>
                <thead>
                    <tr>
                        <th>Mức Ưu Tiên</th>
                        <th>Bộ Phận</th>
                        <th>Vấn Đề Ghi Nhận</th>
                        <th>Lý Do Phân Loại</th>
                        <th>Giải Pháp Đề Xuất</th>
                        <th>SLA Khắc Phục</th>
                    </tr>
                </thead>
                <tbody id="actionTableBody">
                    <!-- Dynamic Rows -->
                </tbody>
            </table>
        </div>
    </div>

    <!-- Live Data Explorer -->
    <div class="section-card">
        <div class="section-header">
            <h3><i class="fa-solid fa-database" style="color: var(--accent-cyan);"></i> 🔍 Tra Cứu Dữ Liệu Review Chi Tiết (Data Explorer)</h3>
            <div class="controls-row">
                <div class="search-box">
                    <i class="fa-solid fa-magnifying-glass"></i>
                    <input type="text" id="searchInput" placeholder="Tìm kiếm từ khóa review..." oninput="filterReviews()">
                </div>
                <select class="filter-select" id="sentimentFilter" onchange="filterReviews()">
                    <option value="ALL">Tất cả cảm xúc</option>
                    <option value="Negative">Negative (Tiêu cực)</option>
                    <option value="Neutral">Neutral (Trung tính)</option>
                    <option value="Positive">Positive (Tích cực)</option>
                </select>
                <select class="filter-select" id="categoryFilter" onchange="filterReviews()">
                    <option value="ALL">Tất cả danh mục</option>
                </select>
            </div>
        </div>

        <div class="table-responsive">
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Cảm Xúc</th>
                        <th>Khiếu Nại?</th>
                        <th>Phân Loại Nhóm</th>
                        <th>Nội Dung Đánh Giá (Review Text)</th>
                        <th>Tóm Tắt AI (Summary)</th>
                    </tr>
                </thead>
                <tbody id="reviewsTableBody">
                    <!-- Dynamic Reviews -->
                </tbody>
            </table>
        </div>

        <div class="pagination">
            <span id="pageInfo">Đang hiển thị...</span>
            <div>
                <button class="page-btn" id="prevBtn" onclick="changePage(-1)"><i class="fa-solid fa-chevron-left"></i> Trước</button>
                <button class="page-btn" id="nextBtn" onclick="changePage(1)">Sau <i class="fa-solid fa-chevron-right"></i></button>
            </div>
        </div>
    </div>
</div>

<script>
    // Embedded Data
    const REPORT_DATA = """ + report_json_str + """;
    const REVIEWS_DATA = """ + reviews_json_str + """;

    let currentPage = 1;
    const pageSize = 10;
    let filteredReviews = [...REVIEWS_DATA];

    // Initialize Page
    document.addEventListener('DOMContentLoaded', () => {
        initCharts();
        renderActionItems();
        populateCategoryFilter();
        filterReviews();
    });

    // Initialize Charts
    function initCharts() {
        // Sentiment Donut Chart
        const sentCtx = document.getElementById('sentimentChart').getContext('2d');
        const sentData = REPORT_DATA.overall_sentiment_breakdown || { Positive: 0, Neutral: 0, Negative: 0 };
        
        new Chart(sentCtx, {
            type: 'doughnut',
            data: {
                labels: ['Tích cực (Positive)', 'Trung tính (Neutral)', 'Tiêu cực (Negative)'],
                datasets: [{
                    data: [sentData.Positive || 0, sentData.Neutral || 0, sentData.Negative || 0],
                    backgroundColor: ['#10b981', '#f59e0b', '#f43f5e'],
                    borderWidth: 0,
                    hoverOffset: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        align: 'center',
                        labels: {
                            color: '#cbd5e1',
                            padding: 14,
                            boxWidth: 10,
                            usePointStyle: true,
                            font: { family: 'Inter', size: 12, weight: '500' }
                        }
                    }
                },
                cutout: '65%'
            }
        });

        // Category Horizontal Bar Chart
        const catCtx = document.getElementById('categoryChart').getContext('2d');
        const insights = REPORT_DATA.category_insights || [];
        const catLabels = insights.map(i => i.category);
        const catCounts = insights.map(i => i.complaint_count);

        new Chart(catCtx, {
            type: 'bar',
            data: {
                labels: catLabels,
                datasets: [{
                    label: 'Số lượng khiếu nại',
                    data: catCounts,
                    backgroundColor: 'rgba(99, 102, 241, 0.75)',
                    borderColor: '#6366f1',
                    borderWidth: 1,
                    borderRadius: 6
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: {
                        grid: { color: 'rgba(255,255,255,0.05)' },
                        ticks: { color: '#94a3b8' }
                    },
                    y: {
                        grid: { display: false },
                        ticks: { color: '#cbd5e1', font: { family: 'Inter', size: 11 } }
                    }
                }
            }
        });
    }

    // Render SLA Action Table
    function renderActionItems() {
        const tbody = document.getElementById('actionTableBody');
        tbody.innerHTML = '';
        const items = REPORT_DATA.action_items || [];

        items.forEach(item => {
            const tr = document.createElement('tr');
            let badgeClass = item.priority === 'High' ? 'badge-high' : (item.priority === 'Medium' ? 'badge-medium' : 'badge-low');
            let priorityIcon = item.priority === 'High' ? '🔴 High' : (item.priority === 'Medium' ? '🟡 Medium' : '🟢 Low');

            tr.innerHTML = `
                <td><span class="badge ${badgeClass}">${priorityIcon}</span></td>
                <td><strong style="color: #f1f5f9;">${item.department}</strong></td>
                <td>${item.issue}</td>
                <td style="font-size: 0.8rem; color: #94a3b8;">${item.priority_rationale}</td>
                <td style="color: #e2e8f0;">${item.action_plan}</td>
                <td><span class="badge badge-cat">${item.timeline}</span></td>
            `;
            tbody.appendChild(tr);
        });
    }

    // Populate Category Dropdown Filter
    function populateCategoryFilter() {
        const select = document.getElementById('categoryFilter');
        const categories = [...new Set(REVIEWS_DATA.map(r => r.category).filter(c => c && c !== 'None'))];
        categories.forEach(cat => {
            const opt = document.createElement('option');
            opt.value = cat;
            opt.textContent = cat;
            select.appendChild(opt);
        });
    }

    // Filter Reviews Data
    function filterReviews() {
        const search = document.getElementById('searchInput').value.toLowerCase();
        const sent = document.getElementById('sentimentFilter').value;
        const cat = document.getElementById('categoryFilter').value;

        filteredReviews = REVIEWS_DATA.filter(r => {
            const matchSearch = r.review_text.toLowerCase().includes(search) || (r.summary && r.summary.toLowerCase().includes(search));
            const matchSent = sent === 'ALL' || r.sentiment === sent;
            const matchCat = cat === 'ALL' || r.category === cat;
            return matchSearch && matchSent && matchCat;
        });

        currentPage = 1;
        renderReviewsTable();
    }

    // Render Paginated Reviews Table
    function renderReviewsTable() {
        const tbody = document.getElementById('reviewsTableBody');
        tbody.innerHTML = '';

        const start = (currentPage - 1) * pageSize;
        const end = start + pageSize;
        const pageItems = filteredReviews.slice(start, end);

        if (pageItems.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 2rem;">Không tìm thấy đánh giá phù hợp.</td></tr>';
        } else {
            pageItems.forEach(r => {
                const tr = document.createElement('tr');
                let sentBadge = r.sentiment === 'Positive' ? 'badge-pos' : (r.sentiment === 'Negative' ? 'badge-neg' : 'badge-neu');
                let painBadge = r.pain_point_flag ? '<span class="badge badge-high">Có khiếu nại</span>' : '<span class="badge badge-low">Bình thường</span>';
                let catBadge = r.category && r.category !== 'None' ? `<span class="badge badge-cat">${r.category}</span>` : '-';

                tr.innerHTML = `
                    <td><strong>#${r.id}</strong></td>
                    <td><span class="badge ${sentBadge}">${r.sentiment}</span></td>
                    <td>${painBadge}</td>
                    <td>${catBadge}</td>
                    <td style="max-width: 380px;">${r.review_text}</td>
                    <td style="color: #cbd5e1; font-style: italic;">${r.summary || '-'}</td>
                `;
                tbody.appendChild(tr);
            });
        }

        // Update Pagination Info
        const total = filteredReviews.length;
        const totalPages = Math.ceil(total / pageSize) || 1;
        document.getElementById('pageInfo').textContent = `Hiển thị ${total > 0 ? start + 1 : 0} - ${Math.min(end, total)} trên tổng số ${total} đánh giá`;
        document.getElementById('prevBtn').disabled = currentPage === 1;
        document.getElementById('nextBtn').disabled = currentPage >= totalPages;
    }

    function changePage(delta) {
        currentPage += delta;
        renderReviewsTable();
    }
</script>

</body>
</html>
"""

    DASHBOARD_HTML_FILE.write_text(html_content, encoding="utf-8")
    root_index = PROJECT_ROOT / "index.html"
    root_index.write_text(html_content, encoding="utf-8")
    print(f"Saved dashboard HTML to {DASHBOARD_HTML_FILE} and {root_index}")

if __name__ == "__main__":
    generate_dashboard()
