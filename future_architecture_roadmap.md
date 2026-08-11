# 🚀 LỘ TRÌNH NÂNG CẤP HỆ THỐNG PHÂN TÍCH TRẢI NGHIỆM KHÁCH HÀNG REAL-TIME & 360° FEEDBACK

Tài liệu thiết kế kiến trúc và hướng đi tương lai cho Hệ thống Trí tuệ Trải nghiệm Khách hàng (Customer Intelligence Platform) dành cho Khách sạn Boutique.

---

## 📌 1. TỔNG QUAN ĐỊNH HƯỚNG TƯƠNG LAI

Chuyển đổi hệ thống hiện tại từ mô hình **Phân tích thủ công theo đợt (Manual Batch Processing)** sang mô hình **Tự động hóa Real-Time 100% (Real-Time Automated Data Pipeline)**, đồng thời mở rộng phân tích toàn diện **360° tất cả ý kiến phản hồi của khách hàng** (Khen ngợi, Góp ý xây dựng, Khiếu nại, Rating từ 1* đến 5*).

---

## 🏗️ 2. KIẾN TRÚC LUỒNG DỮ LIỆU REAL-TIME (REAL-TIME PIPELINE)

Thay vì nhập file CSV và gõ lệnh thủ công, hệ thống tương lai sẽ tự động hóa từ khâu tiếp nhận đến hiển thị:

```text
[KÊNH THU THẬP FEEDBACK]
  ├── Form QR Code đặt tại phòng / Lễ tân (Web App)
  ├── Email / SMS Khảo sát tự động sau khi Checkout
  └── Worker cào tự động OTA (Google Maps, Agoda, Booking.com)
          │
          ▼
[API GATEWAY (FastAPI / Node.js)]
          │ (Đẩy dữ liệu vào Hàng đợi xử lý bất đồng bộ)
          ▼
[MESSAGE QUEUE (Redis Pub/Sub / RabbitMQ)]
          │ (Micro-batching: Xử lý tức thì trong 2-5 giây)
          ▼
[AI WORKER (Gemini API 3.1 Flash Lite)]
  ➔ Phân loại 360°: 🟢 Khen | 🟡 Góp ý | 🔴 Khiếu nại
          │
          ▼
[DATABASE (PostgreSQL / Firebase Realtime)]
          │ (Bắn tín hiệu WebSockets / SSE)
          ▼
[LIVE WEB DASHBOARD 📊]
  ➔ Tự động cập nhật đồ thị thời gian thực
  ➔ Tự động kích hoạt chuông cảnh báo 🔔 khi có sự cố 🔴 High SLA
```

### Các thành phần chính:
1. **API Gateway:** Tiếp nhận dữ liệu phản hồi tức thì từ các ứng dụng QR Code / Website.
2. **Message Queue:** Đảm bảo hệ thống không bị nghẽn khi có hàng trăm phản hồi cùng lúc.
3. **AI Worker Engine:** Gọi mô hình Gemini để bóc tách ý kiến trong 2-3 giây.
4. **Live WebSockets Dashboard:** Dashboard tự nhảy đồ thị và chỉ số KPI thời gian thực mà không cần ấn F5 reload trang.
5. **Cảnh báo Instant Alert:** Bắn thông báo Zalo OA / Telegram Bot cho Lễ tân / Quản lý khi có đánh giá 1-2* để xử lý ngay lập tức trước khi khách checkout.

---

## 🧠 3. MÔ HÌNH PHÂN TÍCH 360° (KHEN, GÓP Ý & KHIẾU NẠI)

AI Agent mở rộng phân tích toàn bộ 3 nhóm cảm xúc và mọi mức điểm Rating từ 1* đến 5*:

### 🟢 Nhóm 1: KHEN NGỢI (Positive Feedback - Rating 4* & 5*)
- **Mục tiêu AI:** Bóc tách các điểm sáng nổi bật nhất được khách hàng yêu thích (nhân viên thân thiện, view đẹp, nệm giường êm, vị trí thuận tiện...).
- **Hành động vận hành:** 
  - Tuyên dương và thưởng nóng cho nhân viên/bộ phận được khen đích danh.
  - Trích xuất từ khóa được khen nhiều nhất làm tư liệu quảng cáo Marketing / Sales.

### 🟡 Nhóm 2: GÓP Ý & ĐỀ XUẤT (Constructive Suggestions - Rating 3* & 4*)
- **Mục tiêu AI:** Bóc tách các mong muốn nâng cấp trải nghiệm (Nice-to-have) (ví dụ: bổ sung máy sấy tóc công suất lớn, thêm trà túi lọc cao cấp, kéo dài giờ mở cửa bể bơi...).
- **Hành động vận hành:** 
  - Chuyển cho Ban Giám Đốc lập ngân sách mua sắm, nâng cấp tiện ích cho mùa tiếp theo.
  - Tăng tỷ lệ chuyển đổi khách hàng từ 3-4* lên 5*.

### 🔴 Nhóm 3: KHIẾU NẠI & SỰ CỐ (Negative Complaints - Rating 1* & 2*)
- **Mục tiêu AI:** Bóc tách các điểm nghẽn nghiêm trọng (Deal-breaker) ảnh hưởng trực tiếp đến uy tín (máy lạnh hỏng, vệ sinh kém, thái độ vô lễ...).
- **Hành động vận hành:**
  - Kích hoạt quy trình SLA xử lý khẩn cấp (🔴 High: < 3 giờ, 🟡 Medium: < 24 giờ).
  - Bắn cảnh báo tự động về điện thoại quản lý ca trực.

---

## 🚦 4. LỘ TRÌNH TRIỂN KHAI 4 GIAI ĐOẠN (IMPLEMENTATION ROADMAP)

### 🔹 Giai đoạn 1: Chuẩn hóa Core Engine (ĐÃ HOÀN THÀNH)
- Xây dựng mô hình AI Agent phân tích lô (`gemini-3.1-flash-lite`).
- Tạo Web Dashboard trực quan hóa tương tác (Chart.js).
- Tự động nhận diện bảng mã UTF-8/CP1258 cho dữ liệu tiếng Việt.

### 🔹 Giai đoạn 2: Xây dựng Backend API & Database (Tiếp theo)
- Chuyển đổi dữ liệu lưu từ file CSV sang Cơ sở dữ liệu (PostgreSQL / MongoDB).
- Viết Backend RESTful API bằng **FastAPI (Python)** để nhận feedback trực tuyến.

### 🔹 Giai đoạn 3: Hệ thống QR Code & Live WebSockets Dashboard
- Tạo trang Web App nhẹ để khách quét mã QR tại phòng / nhà hàng gửi phản hồi.
- Kết nối WebSockets đẩy dữ liệu phân tích lên Web Dashboard thời gian thực.

### 🔹 Giai đoạn 4: Tích hợp Đa kênh & Cảnh báo Zalo/Telegram
- Kết nối API tự động cào dữ liệu từ các kênh OTA (Google Maps, Agoda, Booking.com).
- Tích hợp Bot Zalo OA / Telegram tự động gửi thông báo khẩn cấp cho Quản lý khi phát sinh sự cố.
