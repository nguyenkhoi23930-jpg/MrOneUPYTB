========================================
  MrOneUPYTB  —  Auto upload YouTube
========================================

CÀI ĐẶT:
  1. Python 3.10+ (tick Add to PATH)
  2. Chạy BAM_VAO_DAY.bat

KEY:
  - Key chủ (mọi máy): MrOne781933
  - Mỗi máy có mã máy + key gắn máy (hiện khi mở app lần đầu)
  - Key lưu tại data/license.json

GOOGLE CLOUD (1 lần):
  - Bật YouTube Data API v3
  - OAuth Desktop client → client_secret.json cạnh app.py
  - Test users: thêm Gmail của bạn

CHỦ ĐỀ + TAG:
  - Chọn chủ đề (Truyện ma, Ngôn tình, Tiên hiệp…)
  - Bấm "Random 10 tag" → 10 tag mới theo chủ đề
  - Vẫn sửa tay được ô Tags

TẬP PHIM:
  - Tick "Ưu tiên tập 1→10"
  - Tên file có "Tập 1", "Ep 02", "Tap 3"… → đăng theo thứ tự, không random
  - Không có số tập → random như cũ

THUMB:
  VIDEO+Thumb.jpg hoặc VIDEO.jpg cạnh file mp4
  Có thể đè chữ tên truyện lên ảnh

UPDATE GITHUB:
  Nút "Cập nhật GitHub" — sửa GITHUB_VERSION_URL / GITHUB_ZIP_URL trong app.py
  cho đúng repo của bạn trước khi dùng.

QUOTA:
  ~6 video/ngày/project (mặc định Google). Xin tăng quota nếu cần.
