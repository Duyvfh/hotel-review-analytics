# 🏨 Boutique Hotel Review AI Analytics & Strategic Improvement Agent

Hệ thống AI Agent phân tích trải nghiệm và đánh giá của khách hàng dành cho **Khách sạn Boutique**. Dự án tự động đọc hiểu phản hồi từ khách hàng, gắn nhãn cảm xúc, bóc tách các điểm nghẽn vận hành (Pain Points), lập báo cáo cải thiện dịch vụ và khởi tạo **Web Dashboard trực quan hóa tương tác**.

---

## 🚀 Tính Năng Nổi Bật

- **Mô Hình AI Tiên Tiến (`gemini-3.1-flash-lite`):** Tốc độ phản hồi cực nhanh, chính xác và tiết kiệm tài nguyên.
- **Tối Ưu Phân Tích Theo Lô (Batching Engine):** Gom 10–20 bài đánh giá trong 1 request API duy nhất ➔ **Giảm 90% lượt gọi API** và rút ngắn thời gian xử lý từ vài phút xuống còn vài chục giây.
- **Web Dashboard Trực Quan Hóa Tương Tác ([output/dashboard.html](file:///d:/Code/output/dashboard.html)):**
  - Giao diện **Modern Dark Mode / Glassmorphism** sang trọng.
  - Đồ thị Donut phân bổ Cảm xúc & Đồ thị Bar Phân loại 8 nhóm dịch vụ Boutique (Chart.js).
  - Ma trận Kế hoạch Hành động khắc phục SLA phân cấp 🔴 High (24h-3d), 🟡 Medium (1-2w), 🟢 Low (2-4w).
  - Công cụ tra cứu & lọc dữ liệu review real-time (Live Explorer).
- **Phân Loại 8 Nhóm Vận Hành Khách Sạn Boutique:** `Cleanliness`, `Staff_Service`, `Room_Amenities`, `Boutique_Experience`, `Pricing_and_Fees`, `Noise_and_Quietness`, `Location_and_Access`, `F_and_B`, `Others`.
- **Tự Động Phục Hồi Lỗi (Self-Healing & Auto-Retry):** Tự động xử lý các đợt quá tải máy chủ (HTTP 429/503) bằng cơ chế Exponential Backoff & Model Fallback.
- **Chuẩn Hóa Mã Hóa UTF-8 / UTF-8-sig:** Đảm bảo toàn bộ tập tin tiếng Việt xuất ra không bị lỗi ký tự.

---

## 📂 Cấu Trúc Dự Án (Project Architecture)

```text
d:\Code\
├── data/                      # 📥 Dữ liệu đánh giá đầu vào
│   ├── review.csv             # Tập tin chứa danh sách đánh giá của khách hàng
│   ├── competitors.json       # Dữ liệu tham chiếu đối thủ (tùy chọn)
│   └── google.xlsx            # Dữ liệu khảo sát bổ sung
├── output/                    # 📤 Kết quả phân tích & báo cáo xuất ra
│   ├── dashboard.html         # 🌐 Web Dashboard trực quan hóa tương tác (Chart.js)
│   ├── analyzed_reviews.csv   # 📄 File CSV chi tiết đã gắn nhãn cảm xúc & tóm tắt
│   ├── hotel_improvement_report.md # 📊 Báo cáo chiến lược định dạng Markdown
│   └── hotel_improvement_report.json # 📑 Báo cáo cấu trúc JSON
├── src/                       # ⚙️ Mã nguồn Python cốt lõi
│   ├── analyzer.py            # AI Agent xử lý batching & tổng hợp báo cáo
│   ├── schemas.py             # Pydantic Schemas định dạng dữ liệu
│   ├── scraper.py             # Web Scraper thu thập dữ liệu review
│   └── build_dashboard.py     # Trình khởi tạo Web Dashboard HTML
├── tests/                     # 🧪 Bộ kiểm thử tự động (Unit Tests)
│   ├── test_analyzer.py       # Test luồng xử lý Agent & mock API
│   └── test_scraper.py        # Test bộ cào dữ liệu
├── analyzer.py                # 🚀 Shortcut launcher chạy ở thư mục gốc
├── README.md                  # Hướng dẫn sử dụng dự án
└── requirements.txt           # Danh sách thư viện phụ thuộc
```

---

## 🛠️ Hướng Dẫn Cài Đặt & Chạy Chương Trình

### 1. Kích Hoạt Môi Trường Ảo (Virtual Environment)

Mở PowerShell tại thư mục dự án `d:\Code` và thực thi:

```powershell
# Kích hoạt venv (PowerShell)
.\venv\Scripts\Activate.ps1
```

*(Nếu chưa cài thư viện, chạy: `.\venv\Scripts\pip.exe install -r requirements.txt`)*

---

### 2. Thiết Lập API Key Google Gemini

```powershell
$env:GOOGLE_API_KEY="MÃ_KEY_GEMINI_CỦA_BẠN"
```

---

### 3. Phân Tích Toàn Bộ Đánh Giá & Xuất Dashboard

Chạy lệnh đơn giản ở thư mục gốc:

```powershell
.\venv\Scripts\python.exe analyzer.py
```

*Sau khi chạy hoàn tất, kết quả sẽ tự động lưu vào thư mục `output/`. Bạn có thể mở trực tiếp file `output/dashboard.html` trên trình duyệt để xem báo cáo!*

---

## 🎛️ Tùy Chọn Dòng Lệnh (CLI Options)

Bạn có thể tùy chỉnh các tham số khi chạy `analyzer.py`:

```powershell
# 1. Chạy thử nghiệm 10 đánh giá đầu tiên
.\venv\Scripts\python.exe analyzer.py --limit 10

# 2. Điều chỉnh kích thước lô (batch-size = 20 reviews / 1 request API)
.\venv\Scripts\python.exe analyzer.py --batch-size 20

# 3. Chỉ định model cụ thể (ví dụ: gemini-3.6-flash)
.\venv\Scripts\python.exe analyzer.py --model gemini-3.6-flash

# 4. Chỉ xuất file CSV, bỏ qua tạo báo cáo chiến lược
.\venv\Scripts\python.exe analyzer.py --no-report
```

---

## 🌐 Web Dashboard ([output/dashboard.html](file:///d:/Code/output/dashboard.html))

File Dashboard được tích hợp sẵn dữ liệu và thư viện `Chart.js`. Bạn chỉ cần click đúp vào file hoặc mở qua trình duyệt:

1. **4 Thẻ Chỉ Số KPI:** Tổng Đánh Giá, Tổng Khiếu Nại (Pain Points), Tỷ Lệ Tiêu Cực, Số Lượng Việc Cần Làm Ngay (SLA <3 ngày).
2. **Đồ Thị Cảm Xúc & Phân Loại Dịch Vụ:** Trực quan hóa số lượng khiếu nại theo 8 nhóm vận hành.
3. **Ma Trận Hành Động SLA:** Phân loại 🔴 High, 🟡 Medium, 🟢 Low đi kèm giải pháp và phòng ban trách nhiệm.
4. **Bộ Tra Cứu Real-Time:** Lọc theo từ khóa, cảm xúc hoặc nhóm dịch vụ trực tiếp trên trình duyệt.

---

## 🧪 Chạy Kiểm Thử Tự Động (Unit Tests)

Để kiểm tra độ ổn định của hệ thống và luồng mock API:

```powershell
.\venv\Scripts\python.exe tests/test_analyzer.py
```
