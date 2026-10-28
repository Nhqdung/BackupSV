# 🛡️ Discord Anti-Nuke & Server Backup Bot

Bot Discord chuyên dụng để **Sao lưu (Backup) và Khôi phục (Restore)** cấu hình Server, giúp bạn nhanh chóng hồi sinh Server nguyên vẹn 100% trong trường hợp bị **Raid, Nuke hoặc Admin bị hack tài khoản phá hoại**.

---

## 🌟 Tính Năng Nổi Bật

1. **Sao lưu toàn diện cấu trúc Server:**
   - **Roles:** Tên, mã màu, quyền hạn chi tiết (bitwise permissions), hiển thị riêng (hoist), mentionable, thứ tự phân cấp.
   - **Categories & Channels:** Kênh văn bản (Text), Kênh đàm thoại (Voice), Stage, Diễn đàn (Forum).
   - **Phân quyền chi tiết (Permissions Overwrites):** Giữ nguyên vẹn toàn bộ thiết lập quyền riêng tư của từng kênh đối với từng Role và @everyone.
   - **Cài đặt Server:** Tên server, mức độ xác minh (Verification Level), bộ lọc nội dung, AFK channel/timeout.
   - **Danh sách Emojis.**
2. **Khôi phục nhanh chóng (Anti-Nuke Recovery):**
   - Tự động xóa các kênh/role rác do hacker/raider spam tạo ra.
   - Tái tạo lại toàn bộ danh mục, kênh, role và gán lại quyền chuẩn xác theo bản sao lưu.
   - Có cơ chế **Xác nhận 2 bước (Interactive Button)** để tránh bấm nhầm.
   - Có thanh tiến trình trực quan hiển thị % quá trình khôi phục.
3. **Bảo mật tối đa (Chống kẻ xấu lạm dụng bot):**
   - **CHỈ DUY NHẤT** **Chủ Server (Server Owner)** hoặc **Bot Owner** được phép chạy lệnh Backup / Restore.
   - Ngay cả Admin thông thường cũng **KHÔNG THỂ** sử dụng (đề phòng trường hợp Admin bị hack token phá hoại).
4. **Hỗ trợ tải Backup Offline:**
   - Lệnh `/backup download` cho phép tải file JSON về máy tính cá nhân. Dù bot bị xóa hay server bị nuke hoàn toàn, bạn vẫn giữ file dữ liệu trong tay.
5. **Tự động sao lưu định kỳ (Auto-Backup):**
   - Thiết lập tự động sao lưu mỗi 24 giờ một lần (tùy chỉnh được trong `.env`).
6. **Hỗ trợ cả Slash Commands (`/`) và Prefix Commands (`!`):**
   - Dự phòng trường hợp Discord bị nghẽn Slash Command lúc khẩn cấp.

---

## 📋 Yêu Cầu Hệ Thống

- **Python:** 3.10 trở lên.
- **Thư viện:** `discord.py` >= 2.3.0, `python-dotenv` >= 1.0.0.

---

## 🚀 Hướng Dẫn Cài Đặt Chi Tiết Từ A - Z

### Bước 1: Tạo Bot trên Discord Developer Portal

1. Truy cập [Discord Developer Portal](https://discord.com/developers/applications) và đăng nhập.
2. Bấm **"New Application"**, đặt tên cho bot (ví dụ: `Server Backup Guard`) và bấm **Create**.
3. Vào mục **"Bot"** ở menu bên trái:
   - Bấm **"Reset Token"** -> Sao chép chuỗi **Token** (Lưu giữ cẩn thận, không chia sẻ cho ai).
   - Kéo xuống phần **"Privileged Gateway Intents"**, **BẬT (ON)** 3 mục sau:
     - ✅ **Presence Intent**
     - ✅ **Server Members Intent** (Rất quan trọng để bot đọc danh sách role & thành viên)
     - ✅ **Message Content Intent** (Dùng cho lệnh tiền tố `!`)
   - Bấm **"Save Changes"**.

### Bước 2: Mời Bot vào Server của bạn

1. Vào mục **"OAuth2"** -> **"URL Generator"** ở menu bên trái.
2. Tại bảng **SCOPES**, tích chọn:
   - ✅ `bot`
   - ✅ `applications.commands`
3. Tại bảng **BOT PERMISSIONS**, tích chọn:
   - ✅ **Administrator** (Quản trị viên) - *Bắt buộc để bot có quyền tạo lại kênh và role*.
4. Sao chép đường link ở đáy trang (Generated URL), dán vào trình duyệt và mời bot vào Server cần bảo vệ.

> [!IMPORTANT]
> **VỊ TRÍ ROLE CỦA BOT TRÊN SERVER:**
> Sau khi mời bot vào server, vào **Server Settings (Cài đặt máy chủ) -> Roles (Vai trò)**.
> **Kéo Role của Bot lên vị trí cao nhất có thể** (chỉ đứng dưới quyền của Chủ Server). Nếu để role của bot ở dưới các role khác, bot sẽ không thể quản lý hoặc gán quyền cho các role đó theo quy tắc phân cấp của Discord!

---

### Bước 3: Cấu hình mã nguồn Bot

1. Mở terminal tại thư mục dự án này.
2. Tạo file cấu hình `.env` từ file mẫu `.env.example`:
   ```bash
   cp .env.example .env
   ```
3. Mở file `.env` và điền các thông tin:
   ```env
   # Dán Token bot bạn vừa lấy ở Bước 1 vào đây
   DISCORD_TOKEN=MTA5xxxxxxxxxxxxxxxxxxxxxxxxxxx

   # Tiền tố cho lệnh khẩn cấp (mặc định là !)
   BOT_PREFIX=!

   # Discord ID của bạn (Bật Developer Mode trên Discord -> Chuột phải vào tên bạn -> Copy ID)
   BOT_OWNER_IDS=123456789012345678

   # Bật tính năng tự động sao lưu mỗi ngày
   AUTO_BACKUP_ENABLED=True
   AUTO_BACKUP_INTERVAL_HOURS=24
   MAX_BACKUPS_PER_GUILD=10
   ```

4. Cài đặt các thư viện cần thiết:
   ```bash
   pip install -r requirements.txt
   ```

---

### Bước 4: Khởi Chạy Bot

Chạy lệnh:
```bash
python3 main.py
```

Khi bot khởi động thành công, màn hình sẽ hiển thị:
```text
[INFO] backup_bot: Đã nạp Cog thành công: cogs.backup_commands
[INFO] backup_bot: Đã nạp Cog thành công: cogs.auto_backup
[INFO] backup_bot: Đã đồng bộ thành công X lệnh Slash!
[INFO] backup_bot: === Bot đã sẵn sàng! Đăng nhập với tên: BackupBot#0000 ===
```

---

## 📖 Hướng Dẫn Sử Dụng Lệnh

### 1. Slash Commands (`/`) - Ưu tiên sử dụng:

| Lệnh | Ý nghĩa |
| :--- | :--- |
| `/backup create [ghi_chú]` | Tạo ngay một bản sao lưu toàn bộ server (VD: `/backup create note:Trước khi tuyển Mod`) |
| `/backup list` | Hiển thị danh sách các bản sao lưu đang có cùng thời gian tạo |
| `/backup load <mã_backup>` | Khôi phục server về trạng thái bản sao lưu (Có nút bấm xác nhận 2 lớp) |
| `/backup download <mã_backup>` | Gửi file `.json` riêng tư cho bạn để tải về máy tính lưu offline |
| `/backup delete <mã_backup>` | Xóa bớt bản sao lưu cũ không dùng đến |

### 2. Prefix Commands (`!`) - Dự phòng khẩn cấp:

| Lệnh | Ý nghĩa |
| :--- | :--- |
| `!backup create [ghi chú]` | Tạo bản sao lưu khẩn cấp |
| `!backup list` | Xem danh sách bản sao lưu |
| `!backup load <mã_backup>` | Khôi phục server |
| `!backup download <mã_backup>`| Tải file bản sao lưu |
| `!backup delete <mã_backup>` | Xóa bản sao lưu |

---

## 💡 Lưu Ý Quan Trọng Khi Bị Raid / Nuke

1. **Nếu Server đang bị Nuke (bị bot lạ hoặc hacker phá):**
   - **Lập tức đá/ban (Kick/Ban)** bot lạ hoặc tài khoản phá hoại ra khỏi server.
   - Thu hồi quyền Administrator của các tài khoản bị nghi ngờ bị lộ mật khẩu/token.
   - Chạy lệnh `/backup load <mã_gần_nhất>` hoặc `!backup load <mã_gần_nhất>`.
   - Bot sẽ tự động dọn dẹp các kênh spam và dựng lại toàn bộ phòng ốc, quyền hạn như cũ trong vòng 1-2 phút!

2. **Về Tin Nhắn Cũ (Message History):**
   - Discord API **không cho phép** bất kỳ con bot nào khôi phục tin nhắn cũ của người dùng với đúng tên và mốc thời gian gốc (do chính sách chống giả mạo của Discord).
   - Do đó, mục tiêu cốt lõi của Backup Bot là khôi phục 100% **Cấu trúc server, Phân quyền, Danh mục, Kênh, và Roles** – thứ tốn nhiều thời gian và công sức xây dựng nhất.

---

## 🛠️ Chạy Bot Nền 24/7 trên Linux (Tùy chọn)

Để bot chạy liên tục trên VPS ngay cả khi tắt terminal:

### Dùng PM2:
```bash
sudo npm install -g pm2
pm2 start main.py --name "discord-backup-bot" --interpreter python3
pm2 save
pm2 startup
```

### Dùng Screen / Nohup:
```bash
nohup python3 main.py > bot.log 2>&1 &
```
