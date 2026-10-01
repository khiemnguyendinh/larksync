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

1. Download the latest `LarkSync.dmg` from the [Releases page](https://github.com/khiemnguyendinh/larksync/releases).
2. Open the DMG and drag **LarkSync.app** into your **Applications** folder.
3. **First launch:** macOS Gatekeeper will block unsigned apps. Right-click (or Control-click) `LarkSync.app` in Applications, select **Open**, then click **Open** in the security dialog.
4. LarkSync will appear as an icon in your **menu bar** (top-right area of your screen).

> **System Requirements:** macOS 12 Monterey or later. The published DMG is built for Apple Silicon unless the release notes say otherwise; on an Intel Mac, build from source (see the Developer Guide).

**Windows 10 / 11 (64-bit):** download `LarkSync-Setup-<version>.exe` from the Releases page and run it (no administrator rights needed; optional "start when I sign in" checkbox). Prefer a portable copy? Download `LarkSync-<version>-Windows.zip`, extract it and run `LarkSync.exe`. Windows SmartScreen may warn about an unsigned app: click **More info → Run anyway**. LarkSync then lives in the system tray — see [Windows guide](../Windows_Readme.md).

### Tiếng Việt

1. Tải file `LarkSync.dmg` mới nhất từ [trang Releases](https://github.com/khiemnguyendinh/larksync/releases).
2. Mở file DMG và kéo **LarkSync.app** vào thư mục **Applications**.
3. **Lần đầu mở:** macOS sẽ chặn app chưa được xác thực. Nhấp chuột phải (hoặc Control-click) vào `LarkSync.app` trong Applications, chọn **Open**, sau đó chọn **Open** trong hộp thoại bảo mật.
4. LarkSync sẽ xuất hiện dưới dạng biểu tượng trên **menu bar** (góc trên bên phải màn hình).

> **Yêu cầu hệ thống:** macOS 12 Monterey trở lên. File DMG phát hành được build cho Apple Silicon trừ khi ghi chú phát hành nói khác; với Mac Intel, hãy build từ mã nguồn (xem Developer Guide).

**Windows 10 / 11 (64-bit):** tải `LarkSync-Setup-<phiên bản>.exe` từ trang Releases và chạy (không cần quyền administrator; có tùy chọn "tự khởi động khi đăng nhập"). Muốn bản portable? Tải `LarkSync-<phiên bản>-Windows.zip`, giải nén và chạy `LarkSync.exe`. Windows SmartScreen có thể cảnh báo app chưa ký: bấm **More info → Run anyway**. LarkSync nằm ở khay hệ thống — xem [Hướng dẫn Windows](../Windows_Readme.md).

---

## 2. First Launch & Setup Wizard / Khởi Động Lần Đầu & Trình Cài Đặt {#setup-wizard}

### English

On first launch, the **Setup Wizard** will open automatically. Complete all steps before using the app.

**Step 1 – Connect Lark Drive**
- Enter your **Lark App ID** (e.g., `cli_xxxxxxxxx`) and **App Secret**.
- Click **Authorize Lark →**: your browser opens, you approve access, and the wizard shows **✓ Connected**. The wizard stays responsive while you sign in.
- See [Section 3](#creating-a-lark-app) for how to obtain the credentials. Click **? How to get credentials** for a short checklist.

**Step 2 – Connect Google Drive**
- Click **Browse** and select your `credentials.json` file downloaded from Google Cloud Console.
- Optionally paste the **Destination Folder ID** (leave blank for the root of My Drive; Shared Drive folders work too).
- Click **Authorize Google →** — your browser opens to sign in and grant permission.
- See [Section 4](#google-credentials) for how to obtain this file.

**Step 3 – Sync Preferences**
- Choose a schedule: **Every week**, **Every day** or **Manual only**; for scheduled modes pick the day and hour.
- Choose what happens to files that already exist in Google Drive (**Overwrite** or **Skip**), and optionally a Lark group chat ID for notifications.

**Step 4 – Done**
- Review the summary and click **Start LarkSync**. If Lark or Google is not connected yet, LarkSync warns you before finishing — it cannot sync until both are authorized.

### Tiếng Việt

Lần đầu khởi động, **Setup Wizard** sẽ tự động mở ra. Hoàn thành tất cả các bước trước khi sử dụng app.

**Bước 1 – Kết nối Lark Drive**
- Nhập **Lark App ID** (ví dụ: `cli_xxxxxxxxx`) và **App Secret**.
- Nhấn **Authorize Lark →**: trình duyệt mở ra, bạn cấp quyền, wizard hiển thị **✓ Connected**. Wizard vẫn dùng được trong lúc bạn đăng nhập.
- Xem [Mục 3](#creating-a-lark-app) để biết cách lấy thông tin. Nhấn **? How to get credentials** để xem checklist ngắn.

**Bước 2 – Kết nối Google Drive**
- Nhấn **Browse** và chọn file `credentials.json` đã tải từ Google Cloud Console.
- Có thể dán **Destination Folder ID** (để trống = gốc My Drive; thư mục trong Shared Drive cũng dùng được).
- Nhấn **Authorize Google →** — trình duyệt mở ra để bạn đăng nhập và cấp quyền.
- Xem [Mục 4](#google-credentials) để biết cách lấy file này.

**Bước 3 – Tùy chọn đồng bộ**
- Chọn lịch: **Every week**, **Every day** hoặc **Manual only**; với lịch tự động chọn ngày và giờ.
- Chọn cách xử lý file đã có trên Google Drive (**Overwrite** hoặc **Skip**) và (tùy chọn) Chat ID nhóm Lark để nhận thông báo.

**Bước 4 – Hoàn tất**
- Xem lại tóm tắt và nhấn **Start LarkSync**. Nếu Lark hoặc Google chưa kết nối, LarkSync sẽ cảnh báo trước khi kết thúc — chưa đồng bộ được cho đến khi cả hai đã được cấp quyền.

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
6. Under **Security Settings → Redirect URLs**, add exactly `http://localhost:8080/callback` (without it, "Authorize Lark" fails with a redirect error).
7. Under **Version Management & Release**, publish the app version (even for internal/custom apps, a version must be published for scopes to activate).
8. If your organization requires it, have the app approved by your Lark workspace admin.

> **Important:** The Lark App must have access to the specific folder you want to sync. Go to the folder in Lark Drive, click **Share**, and add your app as a member with at least **Viewer** permission.

### Tiếng Việt

1. Truy cập [Lark Open Platform](https://open.larksuite.com/app) (hoặc [open.feishu.cn/app](https://open.feishu.cn/app) nếu dùng Feishu).
2. Nhấn **Create App** → chọn **Custom App**.
3. Đặt tên app (ví dụ: "LarkSync"), thêm mô tả, nhấn **Confirm**.
4. Vào **Credentials & Basic Info** — sao chép **App ID** và **App Secret**.
5. Vào **Permissions & Scopes**, thêm các quyền sau:
   - `drive:drive:readonly` — Đọc file từ Lark Drive
   - `drive:file:readonly` — Đọc metadata file
6. Vào **Security Settings → Redirect URLs**, thêm chính xác `http://localhost:8080/callback` (thiếu bước này, "Authorize Lark" sẽ báo lỗi redirect).
7. Vào **Version Management & Release**, xuất bản phiên bản app (kể cả app nội bộ cũng cần xuất bản để kích hoạt quyền).
8. Nếu tổ chức yêu cầu, hãy nhờ admin workspace Lark phê duyệt app.

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

**On Windows** the icon lives in the system tray (near the clock — click the **^** arrow if it is hidden). **Right-click** it to open the same menu (plus **About LarkSync**); **left-click** opens Settings. The icon is blue while idle and orange while syncing.

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

**Trên Windows**, biểu tượng nằm ở khay hệ thống (gần đồng hồ — bấm mũi tên **^** nếu bị ẩn). **Nhấp chuột phải** để mở menu tương tự (có thêm **About LarkSync**); **nhấp chuột trái** để mở Settings. Biểu tượng màu xanh khi rảnh và màu cam khi đang đồng bộ.

---

## 6. Settings Window / Cửa Sổ Cài Đặt {#settings}

### English

Open **Settings…** from the menu bar menu (or press **⌘,** on macOS).

**Buttons:**
- **Cancel** starts dimmed. It activates as soon as you change any field, allowing you to close without saving.
- **Save** stores your settings and closes the window — no sync is started.
- **Sync Now** saves your settings and immediately starts a sync.
- While syncing, the button turns red and reads **Cancel Sync**. Click it to stop; it shows "Cancelling…" until the sync has really stopped.
- When the sync ends, the status line at the bottom shows the outcome (complete, cancelled, finished with errors, or the error message).
- **Re-authorize Lark / Google** opens your browser; the window stays usable while you sign in.

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

- Changes take effect after you click **Save** or **Sync Now**. Changing the schedule restarts the countdown — it will not fire an "overdue" sync the moment you save.
- The app must be running (icon visible) for scheduled syncs to occur. LarkSync does not run as a background service when quit.
- **Missed a slot?** If the computer was asleep or switched off at the scheduled time, LarkSync catches up within a minute of the app running again (a manual sync after the slot also counts). If a scheduled sync fails because you are offline or a sign-in expired, it is retried automatically after 15 minutes, then 30, 60… and gives up until the next slot after 6 failed attempts in a row.
- A new installation never starts a surprise full sync: the first scheduled run is the next scheduled slot (or press **Sync Now**).
- To start LarkSync automatically at login, go to **Settings → General** and enable **Launch at Login**.

### Tiếng Việt

Mở **Settings → General** để cấu hình đồng bộ tự động.

**Các nút bấm:**
- Nút **Cancel** ban đầu bị mờ. Nó sẽ sáng lên khi bạn thay đổi bất kỳ trường nào, cho phép đóng mà không lưu.
- Nút **Save** lưu cài đặt rồi đóng cửa sổ — không bắt đầu đồng bộ.
- Nút **Sync Now** lưu cài đặt và bắt đầu đồng bộ ngay lập tức.
- Trong khi đồng bộ, nút chuyển sang màu đỏ và hiện **Cancel Sync**. Nhấp để dừng; nút hiện "Cancelling…" cho đến khi đồng bộ thực sự dừng.
- Khi kết thúc, dòng trạng thái ở dưới cùng cho biết kết quả (hoàn tất, đã hủy, có lỗi, hoặc nội dung lỗi).
- **Re-authorize Lark / Google** mở trình duyệt; cửa sổ vẫn dùng được trong lúc bạn đăng nhập.

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

- Thay đổi có hiệu lực sau khi bấm **Save** hoặc **Sync Now**. Đổi lịch sẽ đặt lại bộ đếm — app không đồng bộ bù ngay lúc bạn lưu.
- App phải đang chạy (biểu tượng hiển thị trên menu bar) để lịch đồng bộ hoạt động. LarkSync không chạy nền khi đã thoát.
- **Lỡ lịch?** Nếu máy ngủ hoặc tắt đúng giờ hẹn, LarkSync tự đồng bộ bù trong vòng 1 phút sau khi app chạy lại (đồng bộ thủ công sau giờ hẹn cũng được tính). Nếu đồng bộ theo lịch thất bại do mất mạng hoặc hết hạn đăng nhập, app tự thử lại sau 15 phút, rồi 30, 60… và dừng đến mốc lịch kế tiếp sau 6 lần thất bại liên tiếp.
- Cài mới sẽ không tự chạy đồng bộ toàn bộ bất ngờ: lần chạy theo lịch đầu tiên là mốc lịch kế tiếp (hoặc bấm **Sync Now**).
- Để tự động khởi động LarkSync khi đăng nhập, vào **Settings → General** và bật **Launch at Login**.

---

## 8. Troubleshooting / Xử Lý Sự Cố {#troubleshooting}

### English

**Error: "Export 400" or "Failed to export file"**
- The most common cause is that the Lark App does not have permission to access the file.
- Go to Lark Drive, find the file, click **Share**, and ensure your Lark App (or the account used) has at least **Viewer** access.
- Some file types (e.g., Lark Docs, Lark Sheets) require the app to have explicit document-level access.

**Error: "invalid_grant" or Google token expired**
- Your Google OAuth token has expired or been revoked. (If your Google Cloud OAuth consent screen is in **Testing** status, Google expires the sign-in every 7 days — publish the app to "In production" or re-authorize weekly.)
- LarkSync now reports this clearly instead of failing silently. Go to **Settings → Google Drive → Re-authorize Google** and sign in again.

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

**Port 8080 is in use (Lark sign-in)**
- Lark's redirect URL is fixed to `http://localhost:8080/callback`. Close the program that is using port 8080 (a dev server, another app) and click **Authorize / Re-authorize Lark** again.

**Where is my data? / Cannot find the log**
- macOS: `~/Library/Application Support/LarkSync/` (in Finder: **Go → Go to Folder…**). Windows: `%APPDATA%\LarkSync\` (paste into the Explorer address bar).
- Upgrading from v1.0.x? Your settings, tokens, credentials and sync history are copied there automatically on first launch; the old `~/Documents/lark_gdrive_sync` folder is left untouched and can be deleted once you confirm everything works. It contains your App Secret and tokens, so do delete it rather than leaving it in a cloud-synced Documents folder.

### Tiếng Việt

**Lỗi: "Export 400" hoặc "Failed to export file"**
- Nguyên nhân phổ biến nhất là Lark App không có quyền truy cập file.
- Vào Lark Drive, tìm file, nhấn **Share**, đảm bảo Lark App (hoặc tài khoản đang dùng) có quyền **Viewer** trở lên.
- Một số loại file (ví dụ: Lark Docs, Lark Sheets) yêu cầu app phải được cấp quyền ở cấp độ tài liệu.

**Lỗi: "invalid_grant" hoặc Google token hết hạn**
- Token Google OAuth đã hết hạn hoặc bị thu hồi. (Nếu màn hình đồng ý OAuth trên Google Cloud đang ở trạng thái **Testing**, Google sẽ làm hết hạn đăng nhập sau 7 ngày — hãy chuyển app sang "In production" hoặc đăng nhập lại hằng tuần.)
- LarkSync giờ báo rõ lỗi này thay vì thất bại âm thầm. Vào **Settings → Google Drive → Re-authorize Google** và đăng nhập lại.

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

**Cổng 8080 đang bị chiếm (đăng nhập Lark)**
- Redirect URL của Lark cố định là `http://localhost:8080/callback`. Hãy tắt chương trình đang dùng cổng 8080 (dev server, app khác) rồi bấm lại **Authorize / Re-authorize Lark**.

**Dữ liệu nằm ở đâu? / Không tìm thấy log**
- macOS: `~/Library/Application Support/LarkSync/` (trong Finder: **Go → Go to Folder…**). Windows: `%APPDATA%\LarkSync\` (dán vào thanh địa chỉ Explorer).
- Nâng cấp từ v1.0.x? Cài đặt, token, credentials và lịch sử đồng bộ được tự sao chép sang đó ở lần mở đầu tiên; thư mục cũ `~/Documents/lark_gdrive_sync` được giữ nguyên và có thể xóa khi bạn đã kiểm tra mọi thứ chạy tốt. Thư mục cũ chứa App Secret và token, nên hãy xóa thay vì để trong thư mục Documents có đồng bộ đám mây.

---

*For additional support, contact: [khiem@kstudy.edu.vn](mailto:khiem@kstudy.edu.vn) or visit [www.kstudy.edu.vn](https://www.kstudy.edu.vn)*  
*Để được hỗ trợ thêm, liên hệ: [khiem@kstudy.edu.vn](mailto:khiem@kstudy.edu.vn) hoặc truy cập [www.kstudy.edu.vn](https://www.kstudy.edu.vn)*
