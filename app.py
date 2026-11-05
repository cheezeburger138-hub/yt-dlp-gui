import sys
import os
import re
import json
from pathlib import Path
from PySide6.QtCore import Qt, QProcess, QProcessEnvironment
from PySide6.QtGui import QIcon, QFont, QColor
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QCheckBox, QComboBox, QProgressBar,
    QTextEdit, QFileDialog, QGroupBox, QGridLayout, QMessageBox,
    QSplitter, QScrollArea, QFrame, QSizePolicy
)

CONFIG_PATH = Path("D:/yt-dlp-gui/config.json")
DEFAULT_FFMPEG_DIR = r"C:\Users\banhm\AppData\Local\ffmpegio\ffmpeg-downloader\ffmpeg\bin"
DEFAULT_DENO_DIR = r"C:\Users\banhm\AppData\Local\Microsoft\WinGet\Packages\DenoLand.Deno_Microsoft.Winget.Source_8wekyb3d8bbwe"
DEFAULT_SAVE_DIR = "D:/Video"

class YtDlpApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("yt-dlp Studio - Tải Video Nhanh")
        self.resize(960, 820)
        self.setMinimumSize(820, 600)

        self.process = None
        self.current_action = ""
        self.is_format_query = False
        self.captured_format_lines = []

        self.load_config()
        self.init_ui()
        self.apply_theme()

    def load_config(self):
        self.config = {
            "save_dir": DEFAULT_SAVE_DIR,
            "cookie_source": "firefox",
            "no_playlist": True,
            "embed_subs": False,
            "ffmpeg_path": DEFAULT_FFMPEG_DIR,
            "deno_path": DEFAULT_DENO_DIR
        }
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    self.config.update(saved)
            except Exception:
                pass
        os.makedirs(self.config["save_dir"], exist_ok=True)

    def save_config(self):
        try:
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            self.log(f"[Cảnh báo] Không thể lưu cài đặt: {e}")

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(6)

        # 1. Header (Luôn cố định trên cùng)
        header_layout = QHBoxLayout()
        title_label = QLabel("⚡ yt-dlp Studio")
        title_label.setObjectName("headerTitle")
        header_layout.addWidget(title_label)

        sub_title = QLabel("Tải Video Đa Nền Tảng (Full HD, MP3, Playlist)")
        sub_title.setStyleSheet("color: #7f848e; margin-left: 10px; font-size: 12px;")
        header_layout.addWidget(sub_title)

        header_layout.addStretch()

        self.btn_update = QPushButton("🔄 Cập nhật yt-dlp")
        self.btn_update.setObjectName("secondaryBtn")
        self.btn_update.clicked.connect(self.action_update_ytdlp)
        header_layout.addWidget(self.btn_update)
        root_layout.addLayout(header_layout)

        # Dùng QSplitter chia giữa bảng điều khiển và bảng log
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setChildrenCollapsible(False)

        # Vùng cuộn ScrollArea cho các điều khiển (Không bao giờ bị chèn ép)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setObjectName("controlsScrollArea")

        controls_container = QWidget()
        controls_layout = QVBoxLayout(controls_container)
        controls_layout.setContentsMargins(4, 4, 10, 4)
        controls_layout.setSpacing(12)

        # --- MỤC 1: NHẬP URL ---
        url_group = QGroupBox("1. Đường dẫn Video / Playlist")
        url_layout = QVBoxLayout(url_group)
        url_layout.setContentsMargins(12, 14, 12, 12)
        url_layout.setSpacing(8)

        url_input_layout = QHBoxLayout()
        self.txt_url = QLineEdit()
        self.txt_url.setPlaceholderText("Dán link YouTube, Facebook, TikTok hoặc link danh sách phát vào đây...")
        self.txt_url.setClearButtonEnabled(True)
        self.txt_url.setMinimumHeight(36)
        url_input_layout.addWidget(self.txt_url)

        self.btn_paste = QPushButton("📋 Dán Link")
        self.btn_paste.setMinimumHeight(36)
        self.btn_paste.clicked.connect(self.paste_clipboard)
        url_input_layout.addWidget(self.btn_paste)

        self.btn_clear_url = QPushButton("✖ Xóa")
        self.btn_clear_url.setMinimumHeight(36)
        self.btn_clear_url.clicked.connect(lambda: self.txt_url.clear())
        url_input_layout.addWidget(self.btn_clear_url)

        url_layout.addLayout(url_input_layout)
        controls_layout.addWidget(url_group)

        # --- MỤC 2: CÀI ĐẶT & NGUỒN COOKIE ---
        options_group = QGroupBox("2. Cài đặt tải & Nguồn Cookie tài khoản")
        options_layout = QVBoxLayout(options_group)
        options_layout.setContentsMargins(12, 14, 12, 12)
        options_layout.setSpacing(10)

        # Hàng 1: Thư mục lưu
        dir_layout = QHBoxLayout()
        lbl_dir = QLabel("Thư mục lưu:")
        lbl_dir.setMinimumWidth(110)
        dir_layout.addWidget(lbl_dir)

        self.txt_dir = QLineEdit(self.config["save_dir"])
        self.txt_dir.setReadOnly(True)
        self.txt_dir.setMinimumHeight(32)
        dir_layout.addWidget(self.txt_dir, stretch=1)

        self.btn_browse = QPushButton("📁 Chọn...")
        self.btn_browse.setMinimumHeight(32)
        self.btn_browse.clicked.connect(self.choose_directory)
        dir_layout.addWidget(self.btn_browse)

        self.btn_open_folder = QPushButton("📂 Mở thư mục")
        self.btn_open_folder.setMinimumHeight(32)
        self.btn_open_folder.clicked.connect(self.open_save_directory)
        dir_layout.addWidget(self.btn_open_folder)
        options_layout.addLayout(dir_layout)

        # Hàng 2: Chọn Cookie Trình duyệt
        cookie_row = QHBoxLayout()
        lbl_cookie = QLabel("🌐 Nguồn Cookie:")
        lbl_cookie.setMinimumWidth(110)
        cookie_row.addWidget(lbl_cookie)

        self.cbo_cookies = QComboBox()
        self.cbo_cookies.setMinimumHeight(32)
        self.cbo_cookies.addItem("🦊 Mozilla Firefox (Khuyên dùng - Không bị khóa file)", "firefox")
        self.cbo_cookies.addItem("🌐 Microsoft Edge (Default)", "edge")
        self.cbo_cookies.addItem("🔵 Google Chrome (Default)", "chrome")
        self.cbo_cookies.addItem("⚪ Không dùng Cookie (Tải công khai)", "none")

        current_cookie = self.config.get("cookie_source", "firefox")
        index = self.cbo_cookies.findData(current_cookie)
        if index != -1:
            self.cbo_cookies.setCurrentIndex(index)
        self.cbo_cookies.currentIndexChanged.connect(self.on_cookie_changed)
        cookie_row.addWidget(self.cbo_cookies, stretch=1)
        options_layout.addLayout(cookie_row)

        # Hàng 3: Checkbox tùy chọn
        check_row = QHBoxLayout()
        self.chk_no_playlist = QCheckBox("🎯 Chỉ tải 1 video (Bỏ qua playlist)")
        self.chk_no_playlist.setChecked(self.config.get("no_playlist", True))
        self.chk_no_playlist.setMinimumHeight(24)
        self.chk_no_playlist.toggled.connect(self.on_option_changed)
        check_row.addWidget(self.chk_no_playlist)

        self.chk_embed_subs = QCheckBox("📝 Tải kèm phụ đề (Vietsub & Engsub nhúng vào video)")
        self.chk_embed_subs.setChecked(self.config.get("embed_subs", False))
        self.chk_embed_subs.setMinimumHeight(24)
        self.chk_embed_subs.toggled.connect(self.on_option_changed)
        check_row.addWidget(self.chk_embed_subs)
        check_row.addStretch()
        options_layout.addLayout(check_row)

        # Hàng 4: Cắt đoạn
        cut_row = QHBoxLayout()
        self.chk_cut = QCheckBox("✂️ Cắt một đoạn:")
        self.chk_cut.setMinimumHeight(24)
        self.chk_cut.toggled.connect(self.toggle_cut_inputs)
        cut_row.addWidget(self.chk_cut)

        cut_row.addWidget(QLabel("Từ:"))
        self.txt_cut_start = QLineEdit("00:01:00")
        self.txt_cut_start.setMaximumWidth(90)
        self.txt_cut_start.setMinimumHeight(28)
        self.txt_cut_start.setEnabled(False)
        cut_row.addWidget(self.txt_cut_start)

        cut_row.addWidget(QLabel("Đến:"))
        self.txt_cut_end = QLineEdit("00:02:30")
        self.txt_cut_end.setMaximumWidth(90)
        self.txt_cut_end.setMinimumHeight(28)
        self.txt_cut_end.setEnabled(False)
        cut_row.addWidget(self.txt_cut_end)
        cut_row.addStretch()
        options_layout.addLayout(cut_row)

        controls_layout.addWidget(options_group)

        # --- MỤC 3: CÁC NÚT TẢI NHANH ---
        actions_group = QGroupBox("3. Tải nhanh theo nhu cầu phổ biến")
        actions_layout = QGridLayout(actions_group)
        actions_layout.setContentsMargins(12, 14, 12, 12)
        actions_layout.setHorizontalSpacing(10)
        actions_layout.setVerticalSpacing(10)

        self.btn_fhd = QPushButton("🎬 TẢI FULL HD (1080p MP4)")
        self.btn_fhd.setObjectName("primaryBtn")
        self.btn_fhd.setMinimumHeight(40)
        self.btn_fhd.setToolTip("Ưu tiên tải video độ phân giải Full HD 1080p MP4")
        self.btn_fhd.clicked.connect(self.action_download_fhd)
        actions_layout.addWidget(self.btn_fhd, 0, 0)

        self.btn_max = QPushButton("🌟 Tải Chất Lượng Tối Đa (4K / 2K)")
        self.btn_max.setObjectName("actionBtn")
        self.btn_max.setMinimumHeight(40)
        self.btn_max.setToolTip("Tải độ phân giải cao nhất video cung cấp và ghép MP4")
        self.btn_max.clicked.connect(self.action_download_max)
        actions_layout.addWidget(self.btn_max, 0, 1)

        self.btn_720p = QPushButton("⚡ Tải Tiết Kiệm (720p MP4)")
        self.btn_720p.setObjectName("actionBtn")
        self.btn_720p.setMinimumHeight(40)
        self.btn_720p.clicked.connect(self.action_download_720p)
        actions_layout.addWidget(self.btn_720p, 0, 2)

        self.btn_mp3 = QPushButton("🎵 Tải Nhạc MP3 (320kbps + Bìa)")
        self.btn_mp3.setObjectName("musicBtn")
        self.btn_mp3.setMinimumHeight(40)
        self.btn_mp3.setToolTip("Trích xuất MP3 chất lượng tốt nhất + nhúng ảnh bìa và metadata bài hát")
        self.btn_mp3.clicked.connect(self.action_download_mp3)
        actions_layout.addWidget(self.btn_mp3, 1, 0)

        self.btn_playlist = QPushButton("📁 Tải Toàn Bộ Playlist (Full HD)")
        self.btn_playlist.setObjectName("actionBtn")
        self.btn_playlist.setMinimumHeight(40)
        self.btn_playlist.setToolTip("Tải trọn bộ danh sách phát kèm đánh số thứ tự")
        self.btn_playlist.clicked.connect(self.action_download_playlist)
        actions_layout.addWidget(self.btn_playlist, 1, 1)

        self.btn_cancel = QPushButton("⛔ Dừng Tác Vụ")
        self.btn_cancel.setObjectName("dangerBtn")
        self.btn_cancel.setMinimumHeight(40)
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel_download)
        actions_layout.addWidget(self.btn_cancel, 1, 2)

        controls_layout.addWidget(actions_group)

        # --- MỤC 4: Ô TRA CỨU & TẢI THEO ĐỊNH DẠNG ---
        format_group = QGroupBox("4. Tra cứu & Chọn định dạng video (Format Explorer)")
        format_group.setObjectName("formatGroup")
        format_layout = QVBoxLayout(format_group)
        format_layout.setContentsMargins(12, 14, 12, 12)
        format_layout.setSpacing(10)

        format_top_row = QHBoxLayout()
        self.btn_fetch_formats = QPushButton("🔍 Liệt kê các định dạng có thể tải")
        self.btn_fetch_formats.setObjectName("inspectBtn")
        self.btn_fetch_formats.setMinimumHeight(36)
        self.btn_fetch_formats.clicked.connect(self.action_inspect_formats)
        format_top_row.addWidget(self.btn_fetch_formats)

        self.lbl_format_status = QLabel("Chưa quét định dạng")
        self.lbl_format_status.setStyleSheet("color: #abb2bf; font-style: italic;")
        format_top_row.addWidget(self.lbl_format_status)
        format_top_row.addStretch()
        format_layout.addLayout(format_top_row)

        format_select_row = QHBoxLayout()
        format_select_row.addWidget(QLabel("Chọn định dạng:"))
        self.cbo_formats = QComboBox()
        self.cbo_formats.addItem("Hãy bấm nút 'Liệt kê các định dạng' ở trên để quét...", "")
        self.cbo_formats.setEnabled(False)
        self.cbo_formats.setMinimumHeight(34)
        format_select_row.addWidget(self.cbo_formats, stretch=1)

        self.btn_download_custom_format = QPushButton("⬇️ Tải định dạng này")
        self.btn_download_custom_format.setObjectName("primaryBtn")
        self.btn_download_custom_format.setEnabled(False)
        self.btn_download_custom_format.setMinimumHeight(34)
        self.btn_download_custom_format.clicked.connect(self.action_download_custom_format)
        format_select_row.addWidget(self.btn_download_custom_format)

        self.btn_view_raw_formats = QPushButton("📄 Bảng chi tiết (-F)")
        self.btn_view_raw_formats.setEnabled(False)
        self.btn_view_raw_formats.setMinimumHeight(34)
        self.btn_view_raw_formats.clicked.connect(self.show_raw_format_table)
        format_select_row.addWidget(self.btn_view_raw_formats)

        format_layout.addLayout(format_select_row)
        controls_layout.addWidget(format_group)

        # --- TIẾN ĐỘ TẢI ---
        progress_box = QWidget()
        progress_layout = QVBoxLayout(progress_box)
        progress_layout.setContentsMargins(0, 4, 0, 4)
        progress_layout.setSpacing(4)

        status_row = QHBoxLayout()
        self.lbl_status = QLabel("Sẵn sàng.")
        self.lbl_status.setObjectName("statusLabel")
        status_row.addWidget(self.lbl_status)

        status_row.addStretch()

        self.lbl_speed = QLabel("")
        self.lbl_speed.setObjectName("speedLabel")
        status_row.addWidget(self.lbl_speed)
        progress_layout.addLayout(status_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setMinimumHeight(20)
        progress_layout.addWidget(self.progress_bar)

        controls_layout.addWidget(progress_box)
        scroll_area.setWidget(controls_container)
        splitter.addWidget(scroll_area)

        # --- MỤC 5: KHUNG LOG TERMINAL ---
        log_container = QWidget()
        log_layout = QVBoxLayout(log_container)
        log_layout.setContentsMargins(4, 4, 4, 4)
        log_layout.setSpacing(6)

        log_header = QHBoxLayout()
        log_header.addWidget(QLabel("Nhật ký chi tiết (Terminal Log):"))
        log_header.addStretch()
        
        btn_clear_log = QPushButton("Xóa log")
        btn_clear_log.setMaximumWidth(80)
        btn_clear_log.setMinimumHeight(26)
        btn_clear_log.clicked.connect(lambda: self.txt_log.clear())
        log_header.addWidget(btn_clear_log)
        log_layout.addLayout(log_header)

        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setObjectName("terminalLog")
        self.txt_log.setMinimumHeight(120)
        log_layout.addWidget(self.txt_log)

        splitter.addWidget(log_container)

        # Tỉ lệ phân chia ban đầu: 70% điều khiển, 30% log
        splitter.setStretchFactor(0, 7)
        splitter.setStretchFactor(1, 3)

        root_layout.addWidget(splitter)

    def apply_theme(self):
        style = """
            QMainWindow {
                background-color: #1e1e24;
            }
            QWidget {
                color: #e0e0e0;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 13px;
            }
            #headerTitle {
                font-size: 20px;
                font-weight: bold;
                color: #61afef;
            }
            #controlsScrollArea {
                background-color: transparent;
            }
            QGroupBox {
                border: 1px solid #3e4451;
                border-radius: 8px;
                margin-top: 14px;
                padding-top: 14px;
                font-weight: bold;
                color: #abb2bf;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 14px;
                top: 2px;
                padding: 0 6px;
                background-color: #1e1e24;
            }
            #formatGroup {
                border: 1px solid #4f5b66;
                background-color: #23272e;
            }
            #formatGroup::title {
                background-color: #23272e;
            }
            QLineEdit, QComboBox {
                background-color: #282c34;
                border: 1px solid #4b5263;
                border-radius: 6px;
                padding: 4px 10px;
                color: #ffffff;
                selection-background-color: #3b82f6;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #61afef;
            }
            QComboBox QAbstractItemView {
                background-color: #282c34;
                color: #ffffff;
                selection-background-color: #3b82f6;
                selection-color: #ffffff;
                border: 1px solid #4b5263;
            }
            QPushButton {
                background-color: #333842;
                border: 1px solid #4b5263;
                border-radius: 6px;
                padding: 6px 14px;
                color: #ffffff;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #404754;
                border-color: #61afef;
            }
            QPushButton:pressed {
                background-color: #21252b;
            }
            QPushButton:disabled {
                background-color: #24272e;
                color: #5c6370;
                border-color: #31353f;
            }
            #primaryBtn {
                background-color: #2563eb;
                border: 1px solid #3b82f6;
                font-weight: bold;
            }
            #primaryBtn:hover {
                background-color: #1d4ed8;
            }
            #actionBtn {
                background-color: #2a313d;
                border: 1px solid #3e4858;
                font-weight: 600;
            }
            #actionBtn:hover {
                background-color: #374151;
                border-color: #60a5fa;
            }
            #musicBtn {
                background-color: #1e3a2f;
                border: 1px solid #059669;
                font-weight: bold;
                color: #6ee7b7;
            }
            #musicBtn:hover {
                background-color: #047857;
                color: #ffffff;
            }
            #inspectBtn {
                background-color: #4338ca;
                border: 1px solid #6366f1;
                font-weight: bold;
                color: #e0e7ff;
            }
            #inspectBtn:hover {
                background-color: #4f46e5;
                color: #ffffff;
            }
            #dangerBtn {
                background-color: #7f1d1d;
                border: 1px solid #dc2626;
                color: #fca5a5;
            }
            #dangerBtn:hover {
                background-color: #991b1b;
                color: #ffffff;
            }
            #secondaryBtn {
                background-color: #2c313a;
                border: 1px solid #3e4451;
                font-size: 12px;
            }
            QCheckBox {
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #4b5263;
                border-radius: 4px;
                background-color: #282c34;
            }
            QCheckBox::indicator:checked {
                background-color: #2563eb;
                border-color: #3b82f6;
            }
            QProgressBar {
                background-color: #282c34;
                border: 1px solid #3e4451;
                border-radius: 6px;
                text-align: center;
                height: 20px;
                color: #ffffff;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #38bdf8);
                border-radius: 5px;
            }
            #terminalLog {
                background-color: #181a1f;
                border: 1px solid #282c34;
                border-radius: 6px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
                color: #98c379;
                padding: 6px;
            }
            #statusLabel {
                font-weight: bold;
                color: #e5c07b;
            }
            #speedLabel {
                color: #61afef;
                font-weight: 500;
            }
            QSplitter::handle {
                background-color: #2d3139;
                height: 4px;
            }
            QScrollBar:vertical {
                border: none;
                background: #1e1e24;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #3e4451;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: #61afef;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """
        self.setStyleSheet(style)

    def paste_clipboard(self):
        clipboard = QApplication.clipboard()
        text = clipboard.text().strip()
        if text:
            self.txt_url.setText(text)

    def choose_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Chọn thư mục lưu video", self.txt_dir.text())
        if directory:
            self.txt_dir.setText(directory)
            self.config["save_dir"] = directory
            self.save_config()

    def open_save_directory(self):
        path = self.txt_dir.text()
        if os.path.exists(path):
            os.startfile(path)
        else:
            QMessageBox.warning(self, "Lỗi", "Thư mục không tồn tại!")

    def on_cookie_changed(self):
        self.config["cookie_source"] = self.cbo_cookies.currentData()
        self.save_config()

    def on_option_changed(self):
        self.config["no_playlist"] = self.chk_no_playlist.isChecked()
        self.config["embed_subs"] = self.chk_embed_subs.isChecked()
        self.save_config()

    def toggle_cut_inputs(self, checked):
        self.txt_cut_start.setEnabled(checked)
        self.txt_cut_end.setEnabled(checked)

    def log(self, text):
        self.txt_log.append(text)
        cursor = self.txt_log.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.txt_log.setTextCursor(cursor)

    def set_ui_busy(self, is_busy):
        self.btn_fhd.setEnabled(not is_busy)
        self.btn_max.setEnabled(not is_busy)
        self.btn_720p.setEnabled(not is_busy)
        self.btn_mp3.setEnabled(not is_busy)
        self.btn_playlist.setEnabled(not is_busy)
        self.btn_fetch_formats.setEnabled(not is_busy)
        self.btn_update.setEnabled(not is_busy)
        self.btn_cancel.setEnabled(is_busy)
        if not is_busy:
            self.lbl_speed.setText("")
            if self.cbo_formats.count() > 0 and self.cbo_formats.currentData():
                self.btn_download_custom_format.setEnabled(True)
                self.btn_view_raw_formats.setEnabled(True)

    def get_url(self):
        url = self.txt_url.text().strip()
        if not url:
            QMessageBox.warning(self, "Chưa điền link", "⚠️ Bạn chưa điền link video!\nVui lòng dán link video vào ô trên trước.")
            return None
        return url

    def build_common_flags(self):
        flags = []
        
        # FFmpeg location
        if os.path.exists(DEFAULT_FFMPEG_DIR):
            flags.extend(["--ffmpeg-location", DEFAULT_FFMPEG_DIR])

        # Cookie source
        cookie_type = self.cbo_cookies.currentData()
        if cookie_type == "firefox":
            flags.extend(["--cookies-from-browser", "firefox"])
        elif cookie_type == "edge":
            flags.extend(["--cookies-from-browser", "edge:Default"])
        elif cookie_type == "chrome":
            flags.extend(["--cookies-from-browser", "chrome:Default"])

        # Subtitles
        if self.chk_embed_subs.isChecked():
            flags.extend(["--write-subs", "--write-auto-subs", "--sub-langs", "vi,en", "--embed-subs"])

        # Section cut
        if self.chk_cut.isChecked():
            start = self.txt_cut_start.text().strip()
            end = self.txt_cut_end.text().strip()
            if start and end:
                flags.extend(["--download-sections", f"*{start}-{end}"])

        # Windows filenames safe
        flags.append("--windows-filenames")

        return flags

    def run_ytdlp_process(self, args, action_desc="Đang tải...", is_query=False):
        if self.process is not None:
            QMessageBox.warning(self, "Đang bận", "Có một tác vụ đang chạy. Hãy đợi hoàn tất hoặc bấm 'Dừng Tác Vụ'!")
            return

        self.current_action = action_desc
        self.is_format_query = is_query
        self.captured_format_lines = []

        self.lbl_status.setText(action_desc)
        self.lbl_status.setStyleSheet("color: #e5c07b;")
        self.progress_bar.setValue(0)
        self.set_ui_busy(True)

        self.log(f"\n==================================================")
        self.log(f"▶ BẮT ĐẦU: {action_desc}")
        cmd_str = "python -m yt_dlp " + " ".join([f'"{a}"' if " " in a else a for a in args])
        self.log(f"💻 LỆNH: {cmd_str}\n")

        self.process = QProcess(self)
        self.process.setProgram(sys.executable)
        self.process.setArguments(["-m", "yt_dlp"] + args)

        # Inject Deno and FFmpeg into PATH
        env = QProcessEnvironment.systemEnvironment()
        extra_path = f"{DEFAULT_DENO_DIR};{DEFAULT_FFMPEG_DIR}"
        current_path = env.value("PATH", "")
        env.insert("PATH", f"{extra_path};{current_path}")
        self.process.setProcessEnvironment(env)

        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.finished.connect(self.process_finished)
        self.process.start()

    def handle_stdout(self):
        data = self.process.readAllStandardOutput().data().decode("utf-8", errors="ignore")
        self.process_output(data)

    def handle_stderr(self):
        data = self.process.readAllStandardError().data().decode("utf-8", errors="ignore")
        self.process_output(data, is_error=True)

    def process_output(self, data, is_error=False):
        for line in data.splitlines():
            clean_line = line.strip()
            if not clean_line:
                continue

            if self.is_format_query:
                self.captured_format_lines.append(clean_line)

            match = re.search(r'\[download\]\s+([\d\.]+)%\s+of\s+([~]?\s*[\d\.]+[KMG]?i?B)(?:\s+at\s+([\d\.]+[KMG]?i?B/s))?(?:\s+ETA\s+([\d:]+))?', clean_line)
            if match:
                pct = float(match.group(1))
                size = match.group(2).strip()
                speed = match.group(3) or ""
                eta = match.group(4) or ""
                
                self.progress_bar.setValue(int(pct))
                status_text = f"Đang tải: {pct:.1f}% ({size})"
                self.lbl_status.setText(status_text)
                
                info = []
                if speed: info.append(f"⚡ {speed}")
                if eta: info.append(f"⏱ Còn: {eta}")
                self.lbl_speed.setText("  |  ".join(info))
            elif "[Merger]" in clean_line or "[ffmpeg]" in clean_line:
                self.lbl_status.setText("⚙️ Đang ghép video và âm thanh...")
                self.progress_bar.setValue(98)
            elif "[ExtractAudio]" in clean_line:
                self.lbl_status.setText("🎵 Đang trích xuất MP3...")
                self.progress_bar.setValue(95)

            if "Could not copy Chrome cookie database" in clean_line or "database is locked" in clean_line:
                self.log("\n⚠️ CẢNH BÁO KHÓA COOKIE: Trình duyệt đang chạy và giữ khóa file dữ liệu.")
                self.log("💡 KHUYÊN DÙNG: Hãy chọn '🦊 Mozilla Firefox' ở mục 2 phía trên!\n")

            self.log(clean_line)

    def process_finished(self, exit_code, exit_status):
        self.set_ui_busy(False)
        self.process = None

        if exit_code == 0:
            self.progress_bar.setValue(100)
            self.lbl_status.setText("✅ Hoàn thành!")
            self.lbl_status.setStyleSheet("color: #98c379;")
            self.log(f"\n✅ [{self.current_action}] THÀNH CÔNG!")

            if self.is_format_query:
                self.parse_and_populate_formats()
        else:
            self.lbl_status.setText("❌ Thao tác gặp lỗi!")
            self.lbl_status.setStyleSheet("color: #e06c75;")
            self.log(f"\n❌ [{self.current_action}] KẾT THÚC VỚI MÃ LỖI: {exit_code}")
            if self.is_format_query:
                self.lbl_format_status.setText("❌ Không thể lấy định dạng (xem log bên dưới)")

    def cancel_download(self):
        if self.process is not None:
            self.log("\n⚠️ Người dùng đã yêu cầu dừng tác vụ...")
            self.lbl_status.setText("Đang dừng...")
            self.process.kill()

    # ==========================
    # CÁC HÀNH ĐỘNG TẢI NHANH
    # ==========================

    def action_download_fhd(self):
        """Ưu tiên Full HD 1080p MP4"""
        url = self.get_url()
        if not url: return

        save_dir = self.txt_dir.text()
        args = [
            "-P", save_dir,
            "-o", "%(title)s [%(id)s].%(ext)s",
            "-f", "bv*[height<=1080]+ba/b[height<=1080]",
            "--merge-output-format", "mp4"
        ]
        if self.chk_no_playlist.isChecked():
            args.append("--no-playlist")
        args.extend(self.build_common_flags())
        args.append(url)

        self.run_ytdlp_process(args, "Tải Video Full HD 1080p MP4")

    def action_download_max(self):
        """Tải chất lượng cao nhất (4K / 2K / Best)"""
        url = self.get_url()
        if not url: return

        save_dir = self.txt_dir.text()
        args = [
            "-P", save_dir,
            "-o", "%(title)s [%(id)s].%(ext)s",
            "-f", "bv*+ba/b",
            "--merge-output-format", "mp4"
        ]
        if self.chk_no_playlist.isChecked():
            args.append("--no-playlist")
        args.extend(self.build_common_flags())
        args.append(url)

        self.run_ytdlp_process(args, "Tải Video Chất Lượng Cao Nhất")

    def action_download_720p(self):
        """Tải bản nhẹ 720p"""
        url = self.get_url()
        if not url: return

        save_dir = self.txt_dir.text()
        args = [
            "-P", save_dir,
            "-o", "%(title)s [%(id)s].%(ext)s",
            "-f", "bv*[height<=720]+ba/b[height<=720]",
            "--merge-output-format", "mp4"
        ]
        if self.chk_no_playlist.isChecked():
            args.append("--no-playlist")
        args.extend(self.build_common_flags())
        args.append(url)

        self.run_ytdlp_process(args, "Tải Video 720p")

    def action_download_mp3(self):
        """Trích xuất MP3 320kbps + Bìa + Metadata"""
        url = self.get_url()
        if not url: return

        save_dir = self.txt_dir.text()
        args = [
            "-P", save_dir,
            "-o", "%(title)s [%(id)s].%(ext)s",
            "-x",
            "--audio-format", "mp3",
            "--audio-quality", "0",
            "--embed-metadata",
            "--embed-thumbnail"
        ]
        if self.chk_no_playlist.isChecked():
            args.append("--no-playlist")
        args.extend(self.build_common_flags())
        args.append(url)

        self.run_ytdlp_process(args, "Tải Nhạc MP3 320kbps (Kèm Bìa)")

    def action_download_playlist(self):
        """Tải toàn bộ Playlist Full HD"""
        url = self.get_url()
        if not url: return

        save_dir = self.txt_dir.text()
        archive_path = os.path.join(save_dir, "da_tai.txt")
        args = [
            "--yes-playlist",
            "-P", save_dir,
            "-o", "%(playlist_title)s/%(playlist_index)03d - %(title)s [%(id)s].%(ext)s",
            "-f", "bv*[height<=1080]+ba/b[height<=1080]",
            "--merge-output-format", "mp4",
            "--download-archive", archive_path
        ]
        args.extend(self.build_common_flags())
        args.append(url)

        self.run_ytdlp_process(args, "Tải Toàn Bộ Playlist (Full HD)")

    # ==========================
    # KHUNG LIỆT KÊ & CHỌN ĐỊNH DẠNG
    # ==========================

    def action_inspect_formats(self):
        """Liệt kê các định dạng có sẵn của link"""
        url = self.get_url()
        if not url: return

        self.cbo_formats.clear()
        self.cbo_formats.addItem("Đang quét định dạng từ YouTube...", "")
        self.cbo_formats.setEnabled(False)
        self.btn_download_custom_format.setEnabled(False)
        self.btn_view_raw_formats.setEnabled(False)
        self.lbl_format_status.setText("⏳ Đang phân tích video...")

        args = ["-F", "--no-playlist"]
        cookie_type = self.cbo_cookies.currentData()
        if cookie_type == "firefox":
            args.extend(["--cookies-from-browser", "firefox"])
        elif cookie_type == "edge":
            args.extend(["--cookies-from-browser", "edge:Default"])
        elif cookie_type == "chrome":
            args.extend(["--cookies-from-browser", "chrome:Default"])

        args.append(url)
        self.run_ytdlp_process(args, "Quét danh sách định dạng video (-F)", is_query=True)

    def parse_and_populate_formats(self):
        self.cbo_formats.clear()
        found_formats = []

        is_table = False
        for line in self.captured_format_lines:
            if "ID" in line and "EXT" in line and "RESOLUTION" in line:
                is_table = True
                continue
            if is_table and line.startswith("---"):
                continue
            if is_table and line:
                parts = line.split()
                if len(parts) >= 3:
                    fmt_id = parts[0]
                    ext = parts[1]
                    res = parts[2]
                    
                    if ext == "mhtml" or "storyboard" in line:
                        continue

                    desc = f"ID [{fmt_id}] | {res.upper()} ({ext.upper()})"
                    if "audio only" in line:
                        desc = f"🎵 ID [{fmt_id}] | Âm thanh riêng ({ext.upper()})"
                    elif "x" in res or "p" in res:
                        size_match = re.search(r'([\d\.]+[KMG]i?B)', line)
                        size_str = f" ~ {size_match.group(1)}" if size_match else ""
                        desc = f"🎬 ID [{fmt_id}] | {res} ({ext.upper()}){size_str}"

                    found_formats.append((fmt_id, desc, res))

        if found_formats:
            found_formats.reverse()
            for fmt_id, desc, res in found_formats:
                self.cbo_formats.addItem(desc, fmt_id)
            
            self.cbo_formats.setEnabled(True)
            self.btn_download_custom_format.setEnabled(True)
            self.btn_view_raw_formats.setEnabled(True)
            self.lbl_format_status.setText(f"✅ Tìm thấy {len(found_formats)} định dạng có thể tải!")
        else:
            self.cbo_formats.addItem("Không phân tích được định dạng (Xem log bên dưới)", "")
            self.lbl_format_status.setText("⚠️ Không tìm thấy bảng định dạng.")

    def action_download_custom_format(self):
        """Tải đúng định dạng người dùng đã chọn trong ComboBox"""
        url = self.get_url()
        if not url: return

        selected_id = self.cbo_formats.currentData()
        if not selected_id:
            QMessageBox.warning(self, "Chưa chọn", "Vui lòng chọn một định dạng trong danh sách thả xuống!")
            return

        save_dir = self.txt_dir.text()
        desc = self.cbo_formats.currentText()
        if "🎵" in desc or "audio" in desc.lower():
            format_spec = selected_id
            merge_flag = []
        else:
            format_spec = f"{selected_id}+ba/b"
            merge_flag = ["--merge-output-format", "mp4"]

        args = [
            "-P", save_dir,
            "-o", "%(title)s [%(id)s].%(ext)s",
            "-f", format_spec
        ]
        args.extend(merge_flag)
        if self.chk_no_playlist.isChecked():
            args.append("--no-playlist")
        args.extend(self.build_common_flags())
        args.append(url)

        self.run_ytdlp_process(args, f"Tải theo định dạng đã chọn (ID: {selected_id})")

    def show_raw_format_table(self):
        """Cuộn nhật ký tới vị trí bảng định dạng -F"""
        cursor = self.txt_log.textCursor()
        cursor.movePosition(cursor.MoveOperation.Start)
        self.txt_log.setTextCursor(cursor)
        self.txt_log.find("Available formats for")
        QMessageBox.information(self, "Bảng Định Dạng Chi Tiết", "Toàn bộ bảng định dạng chuẩn của yt-dlp đã được hiển thị trong khung Nhật ký bên dưới!")

    def action_update_ytdlp(self):
        """Cập nhật yt-dlp lên bản mới nhất"""
        self.lbl_status.setText("Đang cập nhật yt-dlp...")
        self.set_ui_busy(True)
        self.log("\n▶ Đang kiểm tra và cập nhật yt-dlp...")

        self.process = QProcess(self)
        self.process.setProgram(sys.executable)
        self.process.setArguments(["-m", "pip", "install", "-U", "yt-dlp[default]"])
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.finished.connect(self.process_finished)
        self.process.start()

def main():
    app = QApplication(sys.argv)
    window = YtDlpApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
