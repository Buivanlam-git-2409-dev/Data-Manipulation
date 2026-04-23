# VietnamNet News Data Hub

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![Status](https://img.shields.io/badge/Status-Ready-brightgreen)
![License](https://img.shields.io/badge/License-MIT-yellow)

## Mô tả dự án

Ứng dụng Streamlit thu thập, lưu trữ và khai thác dữ liệu đa phương thức (text + image) từ VietnamNet.vn. Hệ thống hỗ trợ cấu hình crawler, theo dõi tiến độ, tra cứu dữ liệu, xem ảnh thumbnail và xuất dữ liệu ra CSV/ZIP.

---

## Tính năng chính

- Crawler đa luồng (`ThreadPoolExecutor`) để tăng tốc độ thu thập bài viết.
- Cơ chế fallback `Selenium` -> `Requests` để ổn định khi trang tải chậm hoặc JavaScript không render.
- Lưu metadata vào SQLite; lưu text và image vào thư mục `data/`.
- Dashboard gồm thống kê, Data Explorer, Image Gallery và Export Center.
- Logging có cấu trúc; hiển thị lỗi thân thiện trong UI.

---

## Công nghệ sử dụng

| Công nghệ | Phiên bản | Mục đích |
|---|---:|---|
| Streamlit | 1.37.1 | UI ứng dụng |
| Selenium | 4.22.0 | Truy cập trang động |
| BeautifulSoup | 4.12.3 | Phân tích HTML |
| Requests | 2.32.3 | HTTP fallback + tải ảnh |
| SQLite | Built-in | Lưu metadata |
| Pandas | 2.2.2 | Dataframe + export |
| Pillow | 10.4.0 | Xử lý ảnh |
| tqdm | 4.66.4 | Progress bar |

---

## Cấu trúc dự án

```
Data-Manipulation/
├── app.py                  # Streamlit UI (entry point)
├── requirements.txt        # Dependencies
├── .env.example            # Mẫu cấu hình
├── data/
│   ├── vn_news.db          # SQLite database (tạo khi khởi chạy)
│   ├── texts/              # File .txt lưu nội dung bài viết
│   └── images/             # Thumbnail images
└── src/
    ├── crawler.py          # Thu thập + fallback + đa luồng
    ├── database.py         # SQLite CRUD
    ├── processor.py        # Clean text
    ├── config.py           # Env config
    └── logger.py           # Structured logging
```

---

## Cài đặt và chạy

### 1. Di chuyển vào thư mục dự án

```bash
cd "..\Data-Manipulation"
```

### 2. Tạo virtual environment (khuyến nghị)

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Cài phụ thuộc

```bash
pip install -r requirements.txt
```

### 4. Cấu hình biến môi trường

Sao chép file `.env.example` thành `.env` và chỉnh sửa nếu cần:

### 5. Chạy ứng dụng

```bash
streamlit run app.py
```
Ứng dụng mở tại: `http://localhost:8501`

---

## Cách sử dụng

1. Chọn số trang cần crawl và chuyên mục ở sidebar.
2. Bấm "Start Crawling" để bắt đầu thu thập.
3. Theo dõi tiến độ ở Dashboard.
4. Dùng Data Explorer để tìm theo tiêu đề/tác giả.
5. Xem thumbnail trong Image Gallery.
6. Xuất CSV hoặc ZIP (text + image) tại Export Center.

---

## Thống kê dữ liệu (Data Statistics)

- Tổng số bài viết đã thu thập.
- Tác giả có nhiều bài viết nhất.
- Bảng tổng hợp top authors.

---

## Ghi chú

- Nếu `Selenium` gặp lỗi, hệ thống tự động fallback sang `Requests`.
- Nếu không có ảnh, trường `image_path` sẽ để trống.
- Logging theo dạng `key=value` để dễ theo dõi.

---

## License

MIT License - Tự do sử dụng và chỉnh sửa.
