# LarkSync – User Guide / Hướng Dẫn Sử Dụng

> **LarkSync** — Sync Lark Drive to Google Drive, automatically.  
> Đồng bộ Lark Drive sang Google Drive một cách tự động.

---

## Table of Contents / Mục Lục

1. [Installation / Cài Đặt](#installation)
2. [First Launch & Setup Wizard / Khởi Động Lần Đầu & Trình Cài Đặt](#setup-wizard)
3. [Creating a Lark App / Tạo Lark App](#creating-a-lark-app)
4. [Getting Google OAuth Credentials / Lấy Google OAuth Credentials](#google-credentials)
5. [Using the Menu Bar / Sử Dụng Menu Bar](#menu-bar)
6. [Settings Window / Cửa Sổ Cài Đặt](#settings)
7. [Schedule Configuration / Cấu Hình Lịch Đồng Bộ](#schedule)
8. [Troubleshooting / Xử Lý Sự Cố](#troubleshooting)

---

## 1. Installation / Cài Đặt {#installation}

### English

1. Download the latest `LarkSync.dmg` from the [Releases page](https://github.com/khiemledev/larksync/releases).
2. Open the DMG and drag **LarkSync.app** into your **Applications** folder.
3. **First launch:** macOS Gatekeeper will block unsigned apps. Right-click (or Control-click) `LarkSync.app` in Applications, select **Open**, then click **Open** in the security dialog.
4. LarkSync will appear as an icon in your **menu bar** (top-right area of your screen).

> **System Requirements:** macOS 12 Monterey or later (Apple Silicon and Intel supported).

### Tiếng Việt

1. Tải file `LarkSync.dmg` mới nhất từ [trang Releases](https://github.com/khiemledev/larksync/releases).
2. Mở file DMG và kéo **LarkSync.app** vào thư mục **Applications**.
3. **Lần đầu mở:** macOS sẽ chặn app chưa được xác thực. Nhấp chuột phải (hoặc Control-click) vào `LarkSync.app` trong Applications, chọn **Open**, sau đó chọn **Open** trong hộp thoại bảo mật.
4. LarkSync sẽ xuất hiện dưới dạng biểu tượng trên **menu bar** (góc trên bên phải màn hình).

> **Yêu cầu hệ thống:** macOS 12 Monterey trở lên (hỗ trợ cả Apple Silicon và Intel).

---

## 2. First Launch & Setup Wizard / Khởi Động Lần Đầu & Trình Cài Đặt {#setup-wizard}

### English

On first launch, the **Setup Wizard** will open automatically. Complete all steps before using the app.

**Step 1 – Lark App Credentials**
- Enter your **Lark App ID** (e.g., `cli_xxxxxxxxx`).
- Enter your **Lark App Secret**.
- See [Section 3](#creating-a-lark-app) for how to obtain these.

**Step 2 – Google Drive Credentials**
- Click **Browse** and select your `credentials.json` file downloaded from Google Cloud Console.
- Click **Authenticate with Google** — a browser window will open asking you to sign in and grant permission.
- See [Section 4](#google-credentials) for how to obtain this file.

**Step 3 – Folder Configuration**
- **Lark Folder Token:** The token of the Lark Drive folder you want to sync (found in the folder's URL: `https://…/drive/folder/<FOLDER_TOKEN>`).
- **Google Drive Folder ID:** The ID of the destination folder on Google Drive (found in the folder's URL: `https://drive.google.com/drive/folders/<FOLDER_ID>`).

**Step 4 – Sync Schedule**
- Choose a schedule: **Manual**, **Daily**, or **Weekly**.
- For Daily/Weekly, set the preferred sync time.
- Click **Finish** to save settings and start the app.

### Tiếng Việt

Lần đầu khởi động, **Setup Wizard** sẽ tự động mở ra. Hoàn thành tất cả các bước trước khi sử dụng app.

**Bước 1 – Thông tin xác thực Lark App**
- Nhập **Lark App ID** (ví dụ: `cli_xxxxxxxxx`).
- Nhập **Lark App Secret**.
- Xem [Mục 3](#creating-a-lark-app) để biết cách lấy thông tin này.

**Bước 2 – Google Drive Credentials**
- Nhấn **Browse** và chọn file `credentials.json` đã tải từ Google Cloud Console.
- Nhấn **Authenticate with Google** — trình duyệt sẽ mở ra để bạn đăng nhập và cấp quyền.
- Xem [Mục 4](#google-credentials) để biết cách lấy file này.

**Bước 3 – Cấu hình thư mục**
- **Lark Folder Token:** Token của thư mục Lark Drive muốn đồng bộ (tìm trong URL thư mục: `https://…/drive/folder/<FOLDER_TOKEN>`).
- **Google Drive Folder ID:** ID của thư mục đích trên Google Drive (tìm trong URL: `https://drive.google.com/drive/folders/<FOLDER_ID>`).

**Bước 4 – Lịch đồng bộ**
- Chọn lịch: **Manual** (thủ công), **Daily** (hàng ngày), hoặc **Weekly** (hàng tuần).
- Với Daily/Weekly, chọn thời điểm đồng bộ mong muốn.
- Nhấn **Finish** để lưu cài đặt và khởi động app.

---

## 3. Creating a Lark App / Tạo Lark App {#creating-a-lark-app}

### English

1. Go to the [Lark Open Platform](https://open.larksuite.com/app) (or [open.feishu.cn/app](https://open.feishu.cn/app) for Feishu).
2. Click **Create App** → choose **Custom App**.
3. Give your app a name (e.g., "LarkSync"), add a description, and click **Confirm**.
4. Navigate to **Credentials & Basic Info** — copy the **App ID** and **App Secret**.
5. Under **Permissions & Scopes**, add the following scopes:
   - `drive:drive:readonly` — Read Lark Drive files
   - `drive:file:readonly` — Read file metadata
6. Under **Version Management & Release**, publish the app version (even for internal/custom apps, a version must be published for scopes to activate).
7. If your organization requires it, have the app approved by your Lark workspace admin.

> **Important:** The Lark App must have access to the specific folder you want to sync. Go to the folder in Lark Drive, click **Share**, and add your app as a member with at least **Viewer** permission.

### Tiếng Việt

1. Truy cập [Lark Open Platform](https://open.larksuite.com/app) (hoặc [open.feishu.cn/app](https://open.feishu.cn/app) nếu dùng Feishu).
2. Nhấn **Create App** → chọn **Custom App**.
3. Đặt tên app (ví dụ: "LarkSync"), thêm mô tả, nhấn **Confirm**.
4. Vào **Credentials & Basic Info** — sao chép **App ID** và **App Secret**.
5. Vào **Permissions & Scopes**, thêm các quyền sau:
   - `drive:drive:readonly` — Đọc file từ Lark Drive
   - `drive:file:readonly` — Đọc metadata file
6. Vào **Version Management & Release**, xuất bản phiên bản app (kể cả app nội bộ cũng cần xuất bản để kích hoạt quyền).
7. Nếu tổ chức yêu cầu, hãy nhờ admin workspace Lark phê duyệt app.

> **Quan trọng:** Lark App phải có quyền truy cập vào thư mục bạn muốn đồng bộ. Vào thư mục trong Lark Drive, nhấn **Share**, thêm app của bạn với quyền **Viewer** trở lên.

---

## 4. Getting Google OAuth Credentials / Lấy Google OAuth Credentials {#google-credentials}

### English

1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (e.g., "LarkSync") or select an existing one.
3. Enable the **Google Drive API**: navigate to **APIs & Services → Library**, search for "Google Drive API", click it, and click **Enable**.
4. Go to **APIs & Services → Credentials**, click **Create Credentials → OAuth client ID**.
5. If prompted, configure the **OAuth consent screen** first:
   - User Type: **External** (or Internal if using Google Workspace)
   - Fill in App name, support email, and developer contact.
6. For Application type, choose **Desktop app**. Give it a name and click **Create**.
7. Click **Download JSON** — save this file as `credentials.json` in a secure location.
8. In the Setup Wizard, browse to this file.

> **Note:** On first authentication, Google will show a warning ("This app isn't verified"). Click **Advanced → Go to [app name] (unsafe)** to proceed. This is normal for personal/developer OAuth apps.

### Tiếng Việt

1. Truy cập [Google Cloud Console](https://console.cloud.google.com/).
2. Tạo project mới (ví dụ: "LarkSync") hoặc chọn project hiện có.
3. Bật **Google Drive API**: vào **APIs & Services → Library**, tìm "Google Drive API", nhấn vào và chọn **Enable**.
4. Vào **APIs & Services → Credentials**, nhấn **Create Credentials → OAuth client ID**.
5. Nếu được yêu cầu, cấu hình **OAuth consent screen** trước:
   - User Type: **External** (hoặc Internal nếu dùng Google Workspace)
   - Điền tên app, email hỗ trợ, và thông tin liên hệ nhà phát triển.
6. Chọn Application type là **Desktop app**, đặt tên và nhấn **Create**.
7. Nhấn **Download JSON** — lưu file này với tên `credentials.json` ở nơi an toàn.
8. Trong Setup Wizard, duyệt đến file này.

> **Lưu ý:** Lần xác thực đầu tiên, Google sẽ hiển thị cảnh báo ("This app isn't verified"). Nhấn **Advanced → Go to [app name] (unsafe)** để tiếp tục. Đây là hành vi bình thường với OAuth app cá nhân/nhà phát triển.

---

## 5. Using the Menu Bar / Sử Dụng Menu Bar {#menu-bar}

### English

**Click once** on the LarkSync icon (⟳) in your menu bar to open the menu. **Click again** on the icon to close it.

| Menu Item | Description |
|-----------|-------------|
| **Sync Now** | Start a manual sync immediately |
| **Cancel Sync** | Appears during an active sync — click to stop it |
| **Last sync:** `<time>` | Shows the timestamp of the last successful sync |
| **Next sync:** `<time>` | Shows the next scheduled sync time (if scheduled) |
| **Settings…** | Opens the Settings window |
| **View Log…** | Opens the sync log window to review activity and errors |
| **Quit LarkSync** | Exits the application |

The menu bar icon changes state:
- **Solid icon** — Idle / waiting
- **Dimmed icon** — Sync in progress

### Tiếng Việt

**Nhấp một lần** vào biểu tượng LarkSync (⟳) trên menu bar để mở menu. **Nhấp lần nữa** vào biểu tượng để đóng menu.

| Mục Menu | Mô Tả |
|----------|-------|
| **Sync Now** | Bắt đầu đồng bộ thủ công ngay lập tức |
| **Cancel Sync** | Xuất hiện khi đang đồng bộ — nhấp để dừng |
| **Last sync:** `<thời gian>` | Hiển thị thời điểm đồng bộ thành công gần nhất |
| **Next sync:** `<thời gian>` | Hiển thị thời điểm đồng bộ tiếp theo (nếu đã lên lịch) |
| **Settings…** | Mở cửa sổ Cài đặt |
| **View Log…** | Mở cửa sổ nhật ký để xem hoạt động và lỗi |
| **Quit LarkSync** | Thoát ứng dụng |

Biểu tượng menu bar thay đổi trạng thái:
- **Biểu tượng đậm** — Đang chờ
- **Biểu tượng mờ** — Đang đồng bộ

---

## 6. Settings Window / Cửa Sổ Cài Đặt {#settings}

### English

Open **Settings…** from the menu bar menu (or press **⌘,** on macOS).

**Smart button behaviour:**
- **Cancel** button starts dimmed. It activates as soon as you change any field, allowing you to close without saving.
- **Sync Now** saves your settings and immediately starts a sync.
- While syncing, the button turns red and reads **Cancel Sync**. Click it to stop the sync.
- After sync completes, a "✓ Sync complete" status appears at the bottom.

> If Settings is already open, clicking "Settings…" again will bring the existing window to the front rather than opening a second one.

**Security — hidden credential fields:**
All sensitive fields (App ID, App Secret, Google Drive Folder ID, Lark Chat ID) are hidden by default. Click the 👁 icon on the right side of each field to reveal its value.

---

## 7. Schedule Configuration / Cấu Hình Lịch Đồng Bộ {#schedule}

### English

Open **Settings → General** to configure automatic syncing.

| Mode | Behavior |
|------|----------|
| **Every week (recommended)** | Syncs once per week on the specified day and time |
| **Every day** | Syncs once per day at the specified time |
| **Manual only** | Sync only when you click "Sync Now" |

- Changes take effect immediately after clicking **Sync Now** or closing Settings.
- The app must be running (menu bar icon visible) for scheduled syncs to occur. LarkSync does not run as a background service when quit.
- To start LarkSync automatically at login, go to **Settings → General** and enable **Launch at Login**.

### Tiếng Việt

Mở **Settings → General** để cấu hình đồng bộ tự động.

**Hành vi nút bấm thông minh:**
- Nút **Cancel** ban đầu bị mờ. Nó sẽ sáng lên khi bạn thay đổi bất kỳ trường nào, cho phép đóng mà không lưu.
- Nút **Sync Now** lưu cài đặt và bắt đầu đồng bộ ngay lập tức.
- Trong khi đồng bộ, nút chuyển sang màu đỏ và hiện **Cancel Sync**. Nhấp để dừng đồng bộ.
- Sau khi hoàn tất, trạng thái "✓ Sync complete" hiện ở dưới cùng.

> Nếu Settings đang mở, nhấp "Settings…" lần nữa sẽ đưa cửa sổ hiện tại lên trước thay vì mở thêm cửa sổ mới.

**Bảo mật — trường thông tin bị ẩn:**
Tất cả trường nhạy cảm (App ID, App Secret, Google Drive Folder ID, Lark Chat ID) được ẩn theo mặc định. Nhấp biểu tượng 👁 ở bên phải mỗi trường để hiện giá trị.

---

### Sync Schedule

| Chế Độ | Hành Vi |
|--------|---------|
| **Every week** | Đồng bộ một lần mỗi tuần vào ngày và giờ đã chọn |
| **Every day** | Đồng bộ một lần mỗi ngày vào giờ đã chọn |
| **Manual only** | Chỉ đồng bộ khi bạn nhấn "Sync Now" |

- App phải đang chạy (biểu tượng hiển thị trên menu bar) để lịch đồng bộ hoạt động. LarkSync không chạy nền khi đã thoát.
- Để tự động khởi động LarkSync khi đăng nhập, vào **Settings → General** và bật **Launch at Login**.

---

## 8. Troubleshooting / Xử Lý Sự Cố {#troubleshooting}

### English

**Error: "Export 400" or "Failed to export file"**
- The most common cause is that the Lark App does not have permission to access the file.
- Go to Lark Drive, find the file, click **Share**, and ensure your Lark App (or the account used) has at least **Viewer** access.
- Some file types (e.g., Lark Docs, Lark Sheets) require the app to have explicit document-level access.

**Error: "invalid_grant" or Google token expired**
- Your Google OAuth token has expired or been revoked.
- Go to **Settings → Google Account → Re-authenticate** and sign in again.

**Error: "App not installed" or Lark 403 error**
- The Lark App may not be published or approved in your workspace.
- Re-check the app status on [open.larksuite.com/app](https://open.larksuite.com/app).

**Sync completes but some files are missing**
- Files that are natively Lark format (Docs, Sheets, Mindnotes) are exported to Google-compatible formats (Docx, Xlsx, PDF). Some formatting may not transfer perfectly.
- Check **View Log** for individual file errors.

**LarkSync doesn't appear in the menu bar**
- Check if the app is running in **Activity Monitor**.
- Try right-clicking the app in Applications and choosing Open.
- Check macOS System Settings → Privacy & Security for any blocked items.

**macOS says the app is damaged**
- Run this command in Terminal: `xattr -cr /Applications/LarkSync.app`
- Then try opening again.

### Tiếng Việt

**Lỗi: "Export 400" hoặc "Failed to export file"**
- Nguyên nhân phổ biến nhất là Lark App không có quyền truy cập file.
- Vào Lark Drive, tìm file, nhấn **Share**, đảm bảo Lark App (hoặc tài khoản đang dùng) có quyền **Viewer** trở lên.
- Một số loại file (ví dụ: Lark Docs, Lark Sheets) yêu cầu app phải được cấp quyền ở cấp độ tài liệu.

**Lỗi: "invalid_grant" hoặc Google token hết hạn**
- Token Google OAuth đã hết hạn hoặc bị thu hồi.
- Vào **Settings → Google Account → Re-authenticate** và đăng nhập lại.

**Lỗi: "App not installed" hoặc Lỗi Lark 403**
- Lark App có thể chưa được xuất bản hoặc phê duyệt trong workspace.
- Kiểm tra lại trạng thái app tại [open.larksuite.com/app](https://open.larksuite.com/app).

**Đồng bộ xong nhưng thiếu một số file**
- Các file định dạng Lark gốc (Docs, Sheets, Mindnotes) sẽ được xuất sang định dạng tương thích Google (Docx, Xlsx, PDF). Một số định dạng có thể không chuyển đổi hoàn hảo.
- Kiểm tra **View Log** để xem lỗi từng file.

**LarkSync không xuất hiện trên menu bar**
- Kiểm tra xem app có đang chạy trong **Activity Monitor** không.
- Thử nhấp chuột phải vào app trong Applications và chọn Open.
- Kiểm tra macOS System Settings → Privacy & Security xem có mục nào bị chặn không.

**macOS báo app bị hỏng**
- Chạy lệnh sau trong Terminal: `xattr -cr /Applications/LarkSync.app`
- Sau đó thử mở lại.

---

*For additional support, contact: [khiem@kstudy.edu.vn](mailto:khiem@kstudy.edu.vn) or visit [www.kstudy.edu.vn](https://www.kstudy.edu.vn)*  
*Để được hỗ trợ thêm, liên hệ: [khiem@kstudy.edu.vn](mailto:khiem@kstudy.edu.vn) hoặc truy cập [www.kstudy.edu.vn](https://www.kstudy.edu.vn)*
