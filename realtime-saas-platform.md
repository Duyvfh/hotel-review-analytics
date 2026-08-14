# 🏨 Kế Hoạch Nâng Cấp: Hotel Review Analytics → SaaS Real-Time Platform

> **Mục tiêu:** Chuyển đổi project phân tích đánh giá khách sạn boutique từ công cụ offline-thủ công (nhập CSV, chạy script, mở file HTML) lên một nền tảng web tự động hoàn toàn — tự thu thập reviews từ Google Maps / Booking / Agoda, tự phân tích bằng AI, tự cập nhật dashboard realtime, và yêu cầu đăng nhập để xem.

---

## 📍 Xuất phát điểm hiện tại (Giai đoạn 0 — ĐÃ HOÀN THÀNH)

| Thành phần | Hiện trạng | File |
|---|---|---|
| Thu thập dữ liệu | Thủ công — copy CSV từ bên ngoài vào `data/` | `data/google.csv` |
| Tiền xử lý | Script chạy tay `preprocess_google_data.py` | `preprocess_google_data.py` |
| Phân tích AI | Script chạy tay `python src/analyzer.py` (Gemini API, batch + cache) | `src/analyzer.py` |
| Dashboard | File HTML tĩnh mở trên trình duyệt, không có authentication | `index.html` |
| Database | Không có — mọi thứ lưu file CSV / JSON | `output/` |

**Các tài sản tái sử dụng được:**
- ✅ AI Engine (`analyzer.py` — Gemini batching, cache, Việt hóa danh mục)
- ✅ Dashboard template (HTML/CSS/JS — glassmorphism, responsive, Chart.js)
- ✅ Preprocessor (`preprocess_google_data.py`)
- ✅ Schemas + Pydantic models (`schemas.py`)
- ✅ Scraper skeleton (`scraper.py` — Playwright-based Google Maps scraper)

---

## 🗺️ Tổng quan Kiến trúc Mục tiêu — 2 Pipeline xử lý tách biệt

> **Nguyên tắc cốt lõi:** QR Feedback xử lý **TỨC THÌ** (< 5 giây). OTA Reviews xử lý **BATCH** (định kỳ mỗi vài giờ). Hai luồng hoàn toàn độc lập, không được gom chung.

```
┌──────────────────────────────────────────────────────────────────────┐
│                         DATA SOURCES                                │
│                                                                      │
│  ┌─ KÊNH OTA ─────────────────┐   ┌─ KÊNH TRỰC TIẾP ───────────┐  │
│  │ Google Biz │ Booking │ Agoda  │   │ 🏨 QR Code Feedback Form │  │
│  │ Profile    │ Partner │ CSV    │   │    (Khách quét QR tại    │  │
│  │ API        │ API    │ Import │   │     phòng / lễ tân)      │  │
│  └──────┬───────┼────────┬─────┘   └────────────┬────────────┘  │
└───────┼───────┼────────┼─────────────┼─────────────┼─────────────┘
        │              │                        │
════════╬══════════════╬════════════════════════╬═════════════
        ▼                                       ▼
┌───────────────────────────────┐  ┌───────────────────────────────────┐
│  📦 PIPELINE 1: BATCH OTA    │  │  ⚡ PIPELINE 2: REALTIME QR       │
│  (Không khẩn cấp)            │  │  (Khẩn cấp — xử lý tức thì)    │
│                               │  │                                   │
│  Cron mỗi 6h:                 │  │  POST /api/feedback:              │
│  Poll API → Gom reviews mới  │  │  Nhận 1 feedback                  │
│       │                      │  │       │                          │
│       ▼                      │  │       ▼                          │
│  Dedup (text_hash)           │  │  Lưu DB ngay lập tức             │
│       │                      │  │       │                          │
│       ▼                      │  │       ▼                          │
│  Batch 25 reviews → 1 call   │  │  Gọi Gemini API NGAY (1 call)    │
│       │                      │  │       │                          │
│       ▼                      │  │       ├──→ Nếu API fail:          │
│  Lưu DB + Update dashboard   │  │       │    Queue retry 30s       │
│                               │  │       │    Max 3 lần             │
│  ⏰ Không cần nhanh.          │  │       │    Nếu vẫn fail:         │
│  Chấp nhận trễ vài giờ.      │  │       │    → Alert admin +       │
│                               │  │       │      giữ raw trong DB    │
│                               │  │       ▼                          │
│                               │  │  Push SSE → Dashboard (< 5s)     │
│                               │  │  Alert Telegram (nếu rating ≤2)  │
│                               │  │                                   │
│                               │  │  ⚠️ PHẢI xử lý xong < 10 giây  │
│                               │  │  KHÔNG được gom lại chờ batch  │
└───────────────────────────────┘  └───────────────────────────────────┘
        │                                       │
        └────────────────┬────────────────┘
                         ▼
┌──────────────────────────────────────────────────────────────────────┐
│                       PRESENTATION LAYER                             │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │           Web App (FastAPI + Jinja2)                            │ │
│  │  ┌──────────┐  ┌──────────────────┐  ┌───────────────────────┐ │ │
│  │  │  Login   │→ │  Dashboard       │  │  Admin Panel          │ │ │
│  │  │  Page    │  │  (Realtime KPIs) │  │  (Quản lý khách sạn)  │ │ │
│  │  └──────────┘  └──────────────────┘  └───────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                          │                                           │
│              ┌───────────┴───────────┐                               │
│              │   Alert System        │                               │
│              │  (Telegram / Email)   │                               │
│              └───────────────────────┘                               │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 📐 Giai đoạn 1: Backend API + Database + Authentication

> **Mục tiêu:** Chuyển dữ liệu từ file CSV sang database thực sự, dựng REST API, thêm đăng nhập để bảo vệ dashboard.

### Quyết định kiến trúc

| Quyết định | Phương án Miễn phí (Recommend cho bắt đầu) | Phương án Trả phí (Mở rộng sau) |
|---|---|---|
| **Web Framework** | **FastAPI (Python)** ← Recommend (tái sử dụng toàn bộ code Python hiện tại) | Django REST Framework |
| **Database** | **Supabase** (PostgreSQL miễn phí 500MB, Auth tích hợp sẵn) | Neon.tech / Railway PostgreSQL / AWS RDS |
| **Authentication** | **Supabase Auth** (email/password miễn phí, có sẵn Row-Level Security) | Firebase Auth / Auth0 (miễn phí 7,500 MAU) |
| **Hosting API** | **Railway.app** (miễn phí $5/tháng trial) hoặc **Render.com** (miễn phí 750h/tháng) | AWS EC2 / DigitalOcean ($5-12/tháng) |

> **Tại sao chọn FastAPI + Supabase?**
> - FastAPI viết bằng Python → **Tái sử dụng 100%** code `analyzer.py`, `schemas.py`, `preprocess_google_data.py` mà không cần viết lại.
> - Supabase cung cấp PostgreSQL + Auth + Realtime subscriptions **MIỄN PHÍ** cho 1 project. Không cần tự dựng server database.
> - Supabase Auth tự tạo sẵn trang Login/Signup — bạn không cần code giao diện đăng nhập từ đầu.

### Cấu trúc Database (PostgreSQL / Supabase)

```sql
-- Bảng Khách sạn
hotels (
  id UUID PRIMARY KEY,
  name TEXT NOT NULL,
  google_maps_url TEXT,
  booking_url TEXT,
  agoda_url TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
)

-- Bảng Đánh giá (lưu trữ vĩnh viễn mọi review)
reviews (
  id UUID PRIMARY KEY,
  hotel_id UUID REFERENCES hotels(id),
  source TEXT NOT NULL,             -- 'google_maps' | 'booking' | 'agoda' | 'qr_feedback'
  reviewer_name TEXT,
  rating INTEGER CHECK (rating BETWEEN 1 AND 5),
  review_text TEXT NOT NULL,
  review_date TEXT,
  text_hash TEXT UNIQUE NOT NULL,   -- SHA-256 để chống trùng lặp
  -- AI Analysis Results (populated by analyzer)
  sentiment TEXT,
  pain_point_flag BOOLEAN,
  category TEXT,
  summary TEXT,
  analyzed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
)

-- Bảng Báo cáo (snapshot mỗi lần chạy phân tích)
reports (
  id UUID PRIMARY KEY,
  hotel_id UUID REFERENCES hotels(id),
  report_json JSONB NOT NULL,
  total_reviews INTEGER,
  total_pain_points INTEGER,
  bhi_score REAL,
  net_sentiment REAL,
  created_at TIMESTAMPTZ DEFAULT NOW()
)

-- Bảng Users (Supabase Auth tự quản lý, chỉ cần bảng profile bổ sung)
user_profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id),
  full_name TEXT,
  role TEXT DEFAULT 'viewer',        -- 'admin' | 'manager' | 'viewer'
  hotel_id UUID REFERENCES hotels(id)
)
```

### Công việc cụ thể

- [ ] Tạo Supabase project → Thiết lập schema database ở trên
- [ ] Cài đặt Supabase Auth (email/password) + Row-Level Security (chỉ user thuộc hotel mới xem được data hotel đó)
- [ ] Tạo project FastAPI backend:
  - `POST /api/reviews/upload` — Upload CSV thủ công (giữ lại luồng cũ)
  - `POST /api/reviews/analyze` — Trigger AI phân tích (gọi `analyzer.py`)
  - `POST /api/feedback` — Nhận review từ QR Code form (public, không cần auth)
  - `GET /api/dashboard/{hotel_id}` — Lấy dữ liệu KPI cho dashboard
  - `GET /api/reviews/{hotel_id}` — Lấy danh sách reviews (phân trang, lọc)
  - `GET /api/reports/{hotel_id}` — Lấy báo cáo chiến lược
- [ ] Migrate logic `analyzer.py` thành service module gọi bởi FastAPI
- [ ] Viết middleware xác thực JWT token từ Supabase Auth

### Xác minh

- [ ] Đăng nhập qua Supabase Auth → nhận JWT token → gọi API → trả về data đúng hotel
- [ ] User không đăng nhập → bị chặn 401 Unauthorized
- [ ] Upload CSV → data vào database → gọi analyze → kết quả lưu vào DB

---

## 📐 Giai đoạn 2: Web Dashboard có xác thực (Login-Protected)

> **Mục tiêu:** Chuyển dashboard HTML tĩnh hiện tại thành web app có trang Login, chỉ user đã đăng nhập mới xem được.

### Quyết định kiến trúc

| Quyết định | Phương án A (Recommend — Đơn giản nhất) | Phương án B (Mở rộng SaaS) |
|---|---|---|
| **Frontend Framework** | **FastAPI + Jinja2 Templates** (Server-side rendering, tái sử dụng HTML/CSS hiện tại) | Next.js + React (SPA, phức tạp hơn nhưng mạnh mẽ hơn) |
| **Hosting Frontend** | Cùng server với Backend (Render / Railway) | Vercel (miễn phí cho Next.js) |
| **Realtime Updates** | **Server-Sent Events (SSE)** ← đơn giản, đủ dùng | WebSocket (socket.io — phức tạp hơn) |

> **Recommend Phương án A (FastAPI + Jinja2) vì:**
> - Tái sử dụng **gần như nguyên vẹn** HTML/CSS/JS dashboard hiện tại — chỉ cần bọc thêm template tags.
> - Không cần học thêm React/Next.js. Toàn bộ stack vẫn là Python.
> - Phù hợp cho 1-10 khách sạn. Khi cần scale lên hàng trăm khách sạn thì mới cần chuyển sang Next.js.

### Luồng hoạt động

```
[User mở website] → [Trang Login] → [Nhập email + password]
         │
         ▼
[Supabase Auth xác thực] → [Trả JWT token] → [Redirect Dashboard]
         │
         ▼
[Dashboard load] → [Gọi API /dashboard/{hotel_id}] → [Render Chart.js + KPIs]
         │
         ▼
[SSE endpoint /stream/{hotel_id}] → [Push realtime khi có review mới]
```

### Công việc cụ thể

- [ ] Chuyển `index.html` thành Jinja2 template (`templates/dashboard.html`)
- [ ] Tạo trang Login (`templates/login.html`) với form email/password
- [ ] Middleware kiểm tra session/JWT trước khi render dashboard
- [ ] Tích hợp SSE endpoint để dashboard tự cập nhật khi có review mới
- [ ] Responsive trên mobile/tablet (đã có sẵn từ giai đoạn trước)

### Xác minh

- [ ] Truy cập `/dashboard` khi chưa đăng nhập → bị redirect về `/login`
- [ ] Đăng nhập thành công → thấy dashboard đầy đủ dữ liệu
- [ ] Mở dashboard trên điện thoại → hiển thị responsive hoàn chỉnh

---

## 📐 Giai đoạn 2.5: QR Code Feedback — Kênh thu thập trực tiếp từ khách

> **Mục tiêu:** Khách đang ở khách sạn quét QR → để lại đánh giá → AI phân tích tức thì → Dashboard cập nhật real-time → Alert nếu khẩn cấp.

### Tại sao kênh này cực kỳ giá trị?

| | Review trên OTA (Google/Booking) | QR Code Feedback (Trực tiếp) |
|---|---|---|
| **Thời điểm** | Sau khi checkout (quá muộn để sửa) | **Ngay khi đang ở khách sạn** |
| **Tính chất** | Công khai — ảnh hưởng rating online | Nội bộ — chỉ khách sạn thấy |
| **Giá trị vận hành** | Biết reputation online | **Can thiệp sớm, cứu vãn trải nghiệm trước khi khách checkout** |
| **Tốc độ** | Chậm (poll mỗi vài giờ) | **Real-time** (dưới 5 giây) |
| **Sở hữu data** | Thuộc về Google/Booking | **100% thuộc khách sạn** |

### Luồng hoạt động

```
[Khách quét QR tại phòng / lễ tân / nhà hàng / bể bơi]
         │
         ▼
[Mở trang Web Form trên điện thoại — KHÔNG cần cài app]
  ┌─────────────────────────────────────┐
  │  🏨 T Home - Chia sẻ trải nghiệm   │
  │                                      │
  │  ⭐⭐⭐⭐⭐  (Chọn 1-5 sao)          │
  │                                      │
  │  [Phòng] [Vệ sinh] [Nhân viên]      │  ← Quick tag categories
  │  [F&B]  [Wifi]    [Khác]            │
  │                                      │
  │  ┌──────────────────────────────┐    │
  │  │ Chia sẻ thêm (tùy chọn)... │    │  ← Textarea
  │  └──────────────────────────────┘    │
  │                                      │
  │  Phòng số: [____]  (tùy chọn)       │
  │                                      │
  │  [  GỬI ĐÁNH GIÁ  ]                │
  └─────────────────────────────────────┘
         │
         ▼
[POST /api/feedback] → [Lưu DB] → [AI Phân tích] → [Push SSE lên Dashboard]
         │
         ▼ (nếu rating ≤ 2)
[🔴 Telegram Alert → Quản lý ca trực xử lý NGAY]
```

### Triển khai kỹ thuật

- **Frontend**: 1 trang HTML responsive tối giản (form đánh giá) — hosted cùng FastAPI, **public** (không cần login)
- **QR Code**: Tạo bằng thư viện `qrcode` (Python) hoặc free trên qr-code-generator.com
- **URL format**: `https://yourdomain.com/feedback?hotel=thome&location=room`
- **Chống spam**: Rate limiting (max 3 feedback/IP/ngày) + honeypot field
- **In QR**: Tent card đặt tại phòng, bàn nhà hàng, quầy lễ tân, bể bơi

### Công việc cụ thể

- [ ] Tạo trang web form feedback (`templates/feedback.html`) — responsive, tối giản, nhanh
- [ ] Tạo endpoint `POST /api/feedback` (public, rate-limited, không cần auth)
- [ ] Tích hợp AI phân tích tức thì khi nhận feedback → lưu DB → push SSE
- [ ] Tạo QR Code cho từng vị trí (phòng, nhà hàng, lễ tân...)
- [ ] Tích hợp alert Telegram nếu rating ≤ 2

### Xác minh

- [ ] Quét QR trên điện thoại → form hiển thị đúng, responsive
- [ ] Submit feedback → xuất hiện trên dashboard trong < 10 giây
- [ ] Rating ≤ 2 → Telegram bot gửi alert cho quản lý
- [ ] Thử submit spam 10 lần liên tục → bị chặn sau lần thứ 3

---

## 📐 Giai đoạn 3: Thu thập Reviews từ OTA (Official API — Chính thống)

> **Mục tiêu:** Tự động thu thập reviews từ Google Maps, Booking.com bằng **Official API hợp pháp**, không cần scraping vi phạm ToS.

### Phân tích nguồn dữ liệu OTA — Phương pháp chính thống

| Nguồn | Phương pháp chính thống | Real-time? | Chi phí | Điều kiện |
|---|---|---|---|---|
| **Google Maps** | **Google Business Profile API** (chủ KS đã xác minh → gọi API lấy reviews) | Poll mỗi 1-6h | ✅ Miễn phí | Phải là chủ/quản lý đã claim Google Business Profile |
| **Booking.com** | **Connectivity Partner API** (đăng ký Partner → nhận webhook khi có review mới) | ✅ Webhook real-time | ✅ Miễn phí | Đăng ký Connectivity Partner (duyệt 2-4 tuần) |
| **Agoda** | **YCS Portal** — export CSV thủ công (API chỉ mở cho Enterprise Partner) | ❌ Thủ công | ✅ Miễn phí | Có tài khoản YCS |
| **Traveloka** | Không có public API — export CSV từ Extranet | ❌ Thủ công | ✅ Miễn phí | Có tài khoản Extranet |
| **Tổng hợp tất cả** | **ReviewPro / TrustYou** (SaaS thu thập từ 100+ nguồn OTA) | ✅ Tự động | 💰 ~$100-200/tháng | Giải pháp enterprise |

> **Recommend — Ưu tiên chính thống + miễn phí:**
>
> 1. **Google Business Profile API** — Miễn phí, hợp pháp. Poll mỗi 1-6h để check review mới. Đây là nguồn review lớn nhất cho khách sạn VN.
> 2. **Booking.com Connectivity Partner** — Miễn phí sau khi được duyệt. Có webhook push khi có review mới (gần real-time).
> 3. **Agoda / Traveloka** — Tạm thời import CSV qua endpoint `POST /api/reviews/upload`. Khi scale lên thì dùng ReviewPro/TrustYou.

### Ưu điểm so với Scraping

| | Scraping (cũ) | Official API (mới) |
|---|---|---|
| **Pháp lý** | ⚠️ Vi phạm ToS | ✅ Hợp pháp 100% |
| **Ổn định** | ❌ Hỏng khi website đổi HTML | ✅ API ổn định, có versioning |
| **Bảo trì** | Cao — liên tục sửa selector | Thấp — chỉ update khi API đổi version |
| **Bị chặn** | ⚠️ Có thể bị block IP | ✅ Không bao giờ |
| **Data quality** | Phải parse HTML, nhiều noise | ✅ JSON sạch, chuẩn |

### Luồng hoạt động

```
[Cron mỗi 1-6h]
     │
     ├──→ [Gọi Google Business Profile API] → [Nhận JSON reviews]
     │
     ├──→ [Booking Webhook listener]         → [Nhận POST khi có review mới]
     │
     └──→ [Agoda/Traveloka: manual CSV]      → [Upload qua /api/reviews/upload]
             │
             ▼
[So sánh text_hash với DB: review nào mới?]
     │
     ▼
[Chỉ review MỚI] → [AI Phân tích] → [Lưu DB] → [Push Dashboard + Alert]
```

### Cơ chế chống trùng lặp (Deduplication)

Mỗi review trước khi lưu vào DB sẽ được tính `SHA-256(review_text)` → kiểm tra cột `text_hash` UNIQUE → **nếu trùng thì bỏ qua, không tốn quota AI phân tích lại**. (Cơ chế này đã được cài sẵn trong `analyzer.py` cache hiện tại, chỉ cần chuyển sang kiểm tra trong DB.)

### Lịch trình tự động (Cron Schedule)

| Tần suất | Phù hợp cho | Cách triển khai |
|---|---|---|
| **Mỗi 6h (4 lần/ngày)** ← Recommend | Khách sạn boutique 10-30 phòng | Cron job trên Railway / Render |
| Mỗi 24h | Khách sạn nhỏ, ít review/tuần | GitHub Actions (miễn phí) |
| Mỗi 1h | Khách sạn lớn hoặc chuỗi | Celery + Redis trên VPS |

### Công việc cụ thể

- [ ] Đăng ký / claim Google Business Profile cho khách sạn → lấy API credentials
- [ ] Viết module `google_reviews.py` gọi Google Business Profile API
- [ ] Đăng ký Booking.com Connectivity Partner → lấy API key
- [ ] Viết webhook listener cho Booking.com reviews
- [ ] Tích hợp deduplication bằng `text_hash` trong database
- [ ] Tạo pipeline: `poll API → dedup → analyze (chỉ review mới) → save DB → alert`
- [ ] Cài đặt cron job (APScheduler trong FastAPI hoặc GitHub Actions)

### Xác minh

- [ ] Cron chạy tự động → gọi Google API → nhận reviews mới → lưu vào DB
- [ ] Reviews trùng lặp bị bỏ qua (không tốn quota AI)
- [ ] Booking webhook nhận review mới → phân tích → hiển thị trên dashboard
- [ ] Dashboard tự cập nhật sau khi pipeline hoàn thành

---

## 📐 Giai đoạn 4: Cảnh báo Tức thời & Thông báo

> **Mục tiêu:** Gửi alert ngay lập tức cho quản lý khi phát hiện review 1-2 sao hoặc sự cố High Priority.

### Các kênh thông báo

| Kênh | Chi phí | Độ khó | Recommend |
|---|---|---|---|
| **Telegram Bot** | Miễn phí hoàn toàn | ⭐ Rất dễ | ✅ Recommend — 10 dòng code Python là xong |
| **Email (SMTP)** | Miễn phí (Gmail SMTP) hoặc SendGrid (100 email/ngày free) | ⭐⭐ Dễ | ✅ Recommend bổ sung |
| **Zalo OA** | Miễn phí (cần doanh nghiệp xác thực) | ⭐⭐⭐ Trung bình | ⚠️ Phù hợp thị trường VN nhưng API phức tạp hơn |
| Slack Webhook | Miễn phí | ⭐ Rất dễ | Phù hợp nếu team dùng Slack |

### Logic cảnh báo

```python
# Pseudo-code
if review.rating <= 2 or review.sentiment == "Negative":
    if review.category in HIGH_PRIORITY_CATEGORIES:
        send_telegram(f"🔴 KHẨN CẤP: {review.summary}")
        send_email(manager_email, subject="SLA Alert", body=...)
    else:
        send_telegram(f"🟡 Lưu ý: {review.summary}")
```

### Công việc cụ thể

- [ ] Tạo Telegram Bot (qua @BotFather) → lưu token vào `.env`
- [ ] Viết module `alerts.py` gửi thông báo qua Telegram API
- [ ] Tích hợp vào pipeline: sau bước analyze → kiểm tra severity → gửi alert
- [ ] Cấu hình email SMTP (Gmail hoặc SendGrid)

---

## 📐 Giai đoạn 5: Triển khai Production & Mở rộng

> **Mục tiêu:** Deploy toàn bộ hệ thống lên cloud, domain riêng, SSL, giám sát.

### Chi phí vận hành ước tính

| Thành phần | Phương án Miễn phí | Phương án Pro | Ghi chú |
|---|---|---|---|
| **Hosting Backend** | Render.com free tier (750h/tháng) | Railway ($5/tháng) hoặc VPS DigitalOcean ($6/tháng) | Free tier đủ cho 1-5 khách sạn |
| **Database** | Supabase free (500MB, 50K rows) | Supabase Pro ($25/tháng) hoặc Neon.tech | Free tier đủ cho ~50,000 reviews |
| **AI API (Gemini)** | Free tier (1,500 RPD) | Gói trả phí cố định (xem mục Quota bên dưới) | Dedup + batch giảm 90%+ lượng call |
| **Domain** | Không (dùng subdomain render/railway) | ~250,000đ/năm (.com) | Cần cho uy tín |
| **SSL** | Miễn phí (Let's Encrypt — tự động trên Render/Railway) | — | Bắt buộc cho website có login |
| **OTA API** | Google Business Profile (miễn phí) | ReviewPro/TrustYou (~$100-200/tháng) | Official API = không cần scraper |

### Tổng chi phí ước tính

| Gói | Chi phí / tháng | Phù hợp cho |
|---|---|---|
| **🆓 Bootstrap (Miễn phí hoàn toàn)** | **0đ** | 1 khách sạn, thử nghiệm, demo |
| **💼 Startup (Cơ bản)** | **~150,000đ - 300,000đ** (~$6-12) | 1-5 khách sạn, production |
| **🏢 Professional** | **~1,000,000đ - 2,000,000đ** (~$40-80) | 5-20 khách sạn, SaaS multi-tenant |

### Công cụ cần thiết tổng hợp

| Công cụ | Vai trò | Miễn phí? | Link |
|---|---|---|---|
| **FastAPI** | Backend API (Python) | ✅ | fastapi.tiangolo.com |
| **Supabase** | Database + Auth + Realtime | ✅ (Free tier) | supabase.com |
| **Google Business Profile API** | Lấy reviews Google Maps chính thống | ✅ | developers.google.com/my-business |
| **Gemini API** | AI phân tích review | ✅ (Free 1,500 RPD) | ai.google.dev |
| **Chart.js** | Biểu đồ dashboard | ✅ | chartjs.org |
| **Render.com** | Hosting backend + cron | ✅ (Free tier) | render.com |
| **Telegram Bot API** | Gửi alert miễn phí | ✅ | core.telegram.org |
| **SendGrid** | Email alert | ✅ (100/ngày) | sendgrid.com |
| **GitHub Actions** | CI/CD + Scheduled jobs | ✅ (2,000 phút/tháng) | github.com |
| **qrcode (Python)** | Tạo QR Code cho feedback | ✅ | pypi.org/project/qrcode |

---

## 🗓️ Timeline ước tính

| Giai đoạn | Thời gian | Prerequisite |
|---|---|---|
| **GĐ 1:** Backend + DB + Auth | 1-2 tuần | — |
| **GĐ 2:** Web Dashboard + Login | 1 tuần | GĐ 1 |
| **GĐ 2.5:** QR Code Feedback System | 3-5 ngày | GĐ 1 + GĐ 2 |
| **GĐ 3:** Auto OTA Collection (Official API) | 1-2 tuần | GĐ 1 |
| **GĐ 4:** Alert System | 2-3 ngày | GĐ 1 + GĐ 3 |
| **GĐ 5:** Deploy Production | 2-3 ngày | GĐ 1-4 |
| **Tổng cộng** | **~5-7 tuần** | |

---

## 💰 Phân tích Quota Gemini API cho Khách sạn Boutique 15 phòng

> **Nguyên tắc:** QR Feedback = **1 feedback = 1 API call tức thì** (không batch). OTA Reviews = **gom lại rồi batch** (25 reviews = 1 call). Hai luồng tính riêng.

### Ước tính lượng review/ngày cho khách sạn 15 phòng

| Nguồn | Cách tính | Ngày thường | Ngày cao điểm (100% occupancy) | Chế độ xử lý |
|---|---|---|---|---|
| **⚡ QR Code Feedback** | 15 phòng × 70-100% lấp đầy × 15-25% phản hồi | **~2-3 feedback** | **~4-5 feedback** | **REALTIME — 1 call/feedback** |
| **📦 Google Maps** | Khách sạn boutique trung bình | ~0-1 review | ~1-2 review | BATCH mỗi 6h |
| **📦 Booking.com** | Booking gửi survey sau checkout | ~0-2 review | ~2-3 review | BATCH mỗi 6h |
| **📦 Agoda / khác** | Import CSV định kỳ | ~0-1 review | ~1-2 review | BATCH khi import |

### Tính toán API call thực tế — Tách rời 2 pipeline

#### ⚡ Pipeline REALTIME (QR Feedback) — 1 call/feedback, xử lý tức thì

| Thông số | Ngày thường | Ngày cao điểm | Worst case |
|---|---|---|---|
| QR Feedbacks | 2-3 | 4-5 | 8 (mùa lễ + nhiều khách review) |
| **API calls** | **2-3 calls** | **4-5 calls** | **8 calls** |
| Token/call (~800 tokens/feedback) | ~1,600-2,400 | ~3,200-4,000 | ~6,400 |

#### 📦 Pipeline BATCH (OTA Reviews) — gom 25 reviews/call, chạy mỗi 6h

| Thông số | Ngày thường | Ngày cao điểm | Worst case |
|---|---|---|---|
| OTA reviews mới | 1-4 | 4-7 | 10 |
| **API calls** (batch 25) | **1 call** | **1 call** | **1 call** |
| Token/call (~2,000-5,000) | ~2,000 | ~5,000 | ~5,000 |

#### Tổng hợp API calls / ngày

| Kịch bản | QR (realtime) | OTA (batch) | **Tổng calls/ngày** | Free tier (1,500 RPD) |
|---|---|---|---|---|
| Ngày thường | 2-3 | 1 | **3-4 calls** | ✅ Sử dụng 0.2% quota |
| Ngày cao điểm | 4-5 | 1 | **5-6 calls** | ✅ Sử dụng 0.4% quota |
| Worst case | 8 | 1 | **9 calls** | ✅ Sử dụng 0.6% quota |
| **Tháng (30 ngày)** | ~90-150 | ~30 | **~120-180 calls** | ✅ Dư rất nhiều |

> **KẾT LUẬN: Ngay cả khi QR Feedback xử lý tức thì (1 call/feedback), tổng cộng chỉ tốn ~5-9 calls/ngày. Free tier Gemini (1,500 RPD) dư đến 99.4% quota. KHÔNG có nguy cơ hết quota giữa chừng.**

### Kịch bản stress test — Khi nào mới thiếu quota?

| Quy mô | QR calls/ngày | OTA calls/ngày | **Tổng calls** | Free tier (1,500) đủ? |
|---|---|---|---|---|
| **1 KS × 15 phòng** | ~3-8 | ~1 | **~4-9** | ✅ Dư 99%+ |
| **5 KS × 15 phòng** | ~15-40 | ~2-3 | **~17-43** | ✅ Dư 97%+ |
| **20 KS × 15 phòng** | ~60-160 | ~4-8 | **~64-168** | ✅ Dư 89%+ |
| **50 KS × 20 phòng** | ~150-400 | ~10-20 | **~160-420** | ✅ Dư 72%+ |
| **100+ KS** | ~300-800 | ~20-40 | **~320-840** | ⚠️ 44-79% — vẫn đủ nhưng nên upgrade |
| **200+ KS (SaaS lớn)** | ~600-1,600 | ~40-80 | **~640-1,680** | ❌ Vượt — BẮt buộc upgrade |

### 🛡️ Đảm bảo ZERO miss feedback — Cơ chế Fallback Queue

> **Vấn đề:** Nếu đúng lúc khách gửi feedback mà Gemini API bị lỗi (rate limit, network, downtime) thì sao? Không được để mất feedback nào.

#### Thiết kế: Lưu trước — Phân tích sau — Không bao giờ mất data

```
[Khách gửi feedback qua QR]
         │
         ▼
[BƯỚC 1: Lưu RAW vào DB NGAY LẬP TỨC]  ←←← Data AN TOÀN từ đây.
  (status = 'pending_analysis')           Dù AI crash cũng không mất.
         │
         ▼
[BƯỚC 2: Gọi Gemini API ngay lập tức]
         │
    ┌────┴────┐
    │          │
 ✅ Thành công  ❌ Thất bại
    │          │
    ▼          ▼
  Cập nhật   [FALLBACK QUEUE]
  DB với     │
  kết quả    ├─→ Retry sau 30s (lần 1)
  AI         ├─→ Retry sau 60s (lần 2)
    │        ├─→ Retry sau 120s (lần 3)
    │        │
    │        └─→ Nếu vẫn fail sau 3 lần:
    │              • Gửi Telegram cho admin:
    │                "⚠️ Feedback #123 chưa phân tích được"
    │              • Dashboard vẫn hiển thị feedback
    │                (rating + text gốc, chưa có AI summary)
    │              • status = 'analysis_failed'
    │              • Cron job quét lại mỗi 1h để retry
    ▼
  Push SSE lên Dashboard (< 10s)
  Gửi Alert Telegram (nếu rating ≤ 2)
```

**Điểm mấu chốt:**
- ✅ **ZERO data loss:** Feedback được lưu DB **TRƯỚC** khi gọi AI. Dù Gemini crash, data vẫn còn.
- ✅ **Dashboard vẫn nhận:** Rating + text gốc xuất hiện ngay trên dashboard (kể cả chưa có AI summary).
- ✅ **Alert không bị miss:** Rating ≤ 2 → alert Telegram dựa trên rating gốc, không cần đợi AI.
- ✅ **Tự hồi phục:** Cron job mỗi 1h quét `status = 'analysis_failed'` để retry tự động.

### Giải pháp chống rủi ro bảo mật — Không dùng Pay-as-you-go

> **Lo ngại của bạn hoàn toàn hợp lý.** Pay-as-you-go = nếu API key bị lộ, kẻ tấn công có thể đốt hết tiền trong tài khoản. Đây là các giải pháp thay thế:

#### ✅ Recommend: Phòng thủ nhiều lớp (Defense in Depth)

| Lớp | Giải pháp | Tác dụng |
|---|---|---|
| **Lớp 1: Free tier là đủ** | Dùng Gemini Free tier (1,500 RPD). Không cần bật billing. | Nếu key bị lộ → kẻ tấn công cũng chỉ dùng được 1,500 calls/ngày miễn phí → **KHÔNG MẤT TIỀN** |
| **Lớp 2: Budget cap** | Nếu cần upgrade: Google Cloud cho đặt **Budget Alert + Hard Spending Cap** (ví dụ: cap $5/tháng) | Vượt cap → Google **tự động ngắt** API → không charge thêm |
| **Lớp 3: API Key Restriction** | Cấu hình API key chỉ cho phép gọi từ IP server cụ thể + chỉ cho phép Gemini API | Key bị lộ cũng không dùng được từ máy khác |
| **Lớp 4: Rotate key** | Rotate API key mỗi 30-90 ngày qua Google Cloud Console | Giảm thời gian key bị lộ có hiệu lực |
| **Lớp 5: Dedicated quota cho QR** | Server tách biệt quota: dành riêng **20 calls/ngày cho QR** (không chia sẻ với OTA batch). Nếu OTA batch xài hết phần của nó, QR vẫn chạy bình thường. | **Đảm bảo QR luôn được ưu tiên** — OTA hết quota thì chờ đợt batch tiếp theo, nhưng QR không bao giờ bị ảnh hưởng |
| **Lớp 6: Rate limit ở server** | FastAPI middleware giới hạn max 50 calls/ngày tổng đến Gemini (QR: 20, OTA: 30) | Dù bị tấn công qua API server cũng không vượt 50 calls |

#### Gói đầu tư API recommend cho từng giai đoạn

| Giai đoạn | Gói | Chi phí / tháng | QR an toàn? | Lý do |
|---|---|---|---|---|
| **1 KS × 15 phòng** | **Gemini Free tier** (1,500 RPD) | **0đ** | ✅ Dư 99%+ | Dùnh riêng 20 calls/ngày cho QR. Không bao giờ hết. |
| **5 KS × 15 phòng** | **Gemini Free tier** | **0đ** | ✅ Dư 97%+ | 40 QR + 3 OTA = 43 calls/ngày. Vẫn dư. |
| **20 KS × 15 phòng** | **Gemini Free tier** | **0đ** | ✅ Dư 89%+ | 160 QR + 8 OTA = 168 calls/ngày. Vẫn trong giới hạn. |
| **50+ KS** | **Paid tier** + Budget cap $10/tháng | **~$2-5 thực tế** (~50,000-125,000đ) | ✅ | Hard cap $10 → vượt thì tự ngắt. An toàn. |

> **Tóm lại: Với 15 phòng và QR realtime, Free tier (1,500 RPD) vẫn DƯ SỨC. Bạn dùng tối đa ~9 calls/ngày = 0.6% quota. Cơ chế Dedicated Quota + Fallback Queue đảm bảo không bao giờ miss feedback quan trọng, kể cả khi Gemini API gặp sự cố.**

---

## ⚠️ Rủi ro & Lưu ý quan trọng

### Thu thập dữ liệu OTA
- Phương án chính là **Official API** (Google Business Profile + Booking Partner) — hợp pháp, ổn định.
- Với Agoda/Traveloka chưa có API mở: tạm thời import CSV thủ công, hoặc dùng dịch vụ trung gian (ReviewPro/TrustYou) khi scale.

### Bảo mật API Key & chống vượt ngân sách
- **KHÔNG dùng Pay-as-you-go mở** — luôn đặt Budget Hard Cap trên Google Cloud.
- API key phải được restrict theo IP server + chỉ cho phép Gemini API.
- File `.env` phải có trong `.gitignore`. Không commit vào Git public.
- Rotate key mỗi 30-90 ngày.

### QR Code Feedback Pipeline
- **2 pipeline tách biệt:** QR = REALTIME (1 call/feedback, < 10s). OTA = BATCH (gom lại, mỗi 6h).
- **Fallback Queue:** Lưu DB trước, AI sau. Nếu AI fail → retry 3 lần → alert admin. Data không bao giờ mất.
- **Dedicated Quota:** Dành riêng 20 calls/ngày cho QR, không chia sẻ với OTA. QR luôn được ưu tiên.
- **Alert không phụ thuộc AI:** Rating ≤ 2 → Telegram alert dựa trên rating gốc, không cần chờ AI.
- Rate limiting bắt buộc (max 3/IP/ngày) + honeypot field để chống spam.

---

## ✅ Checklist Tổng Kết

- [ ] **GĐ 1:** Supabase DB + FastAPI backend + JWT Auth hoạt động
- [ ] **GĐ 2:** Dashboard web có Login, responsive, dữ liệu realtime
- [ ] **GĐ 2.5:** QR Code Feedback form → AI phân tích real-time → Push Dashboard + Alert
- [ ] **GĐ 3:** Google Business Profile API + Booking Partner API → tự động poll reviews mới
- [ ] **GĐ 4:** Telegram bot gửi alert khi có review 1-2 sao
- [ ] **GĐ 5:** Deploy trên Render/Railway, domain + SSL, monitoring

---

> **Bước tiếp theo:** Sau khi review và đồng ý plan này, chạy `/create` hoặc `/enhance` để bắt đầu triển khai từng giai đoạn.
