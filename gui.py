"""
GUI Application for Solid Background Removal to Lottie JSON and Animated GIF Converter.
Built with Python standard library Tkinter.
Supports Edge Trim (halo removal), Format Selection, Output Resolution, and Modes.
"""

import os
import sys
import threading
import subprocess
import shutil
import queue
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
import cv2

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    HAS_DND = True
except ImportError:
    HAS_DND = False

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import config
from video.reader import VideoReader
from video.frame_processor import FrameProcessor
from background.detector import BackgroundDetector
from mask.processor import BackgroundRemover
from contour.extractor import ContourExtractor
from lottie.path import LottiePathConverter
from lottie.writer import LottieWriter
from gif.writer import GifWriter

# Ensure cwd is not root '/' when launched as a macOS .app bundle
if os.getcwd() == '/':
    try:
        os.chdir(os.path.expanduser("~"))
    except Exception:
        pass

FONT_FAMILY = "Apple SD Gothic Neo" if sys.platform == "darwin" else "Malgun Gothic"


def get_default_output_dir():
    return os.path.join(os.path.expanduser("~"), "Downloads", "lottie-output")


def parse_dropped_files(data_str: str) -> list:
    """Parses Drag-and-Drop file path string, safely handling braces and spaces."""
    if not data_str:
        return []
    pattern = r'\{([^}]+)\}|(\S+)'
    matches = re.findall(pattern, data_str.strip())
    return [m[0] or m[1] for m in matches if (m[0] or m[1])]


class LottieConverterGUI:

    def __init__(self, root):
        self.root = root
        self.root.title("단색 배경 제거 → Lottie JSON & GIF 변환기")
        self.root.geometry("1060x560")
        self.root.minsize(980, 520)

        self.style = ttk.Style()
        self.style.theme_use('clam')

        self.last_generated_json = None
        self.last_generated_gif = None
        self.orig_w = 0
        self.orig_h = 0
        self.user_customized_output_dir = False

        # Thread-safe message queue for background worker updates
        self.msg_queue = queue.Queue()
        self._start_queue_poller()

        self._build_ui()
        self._setup_drag_and_drop()


    def _start_queue_poller(self):
        """Polls messages from background threads safely on the main GUI thread."""
        def _poll():
            try:
                while True:
                    msg_type, data = self.msg_queue.get_nowait()
                    if msg_type == "log":
                        self.log_text.insert(tk.END, data + "\n")
                        self.log_text.see(tk.END)
                    elif msg_type == "success":
                        json_path, gif_path = data
                        self.on_conversion_success(json_path, gif_path)
                    elif msg_type == "error":
                        self.on_conversion_error(data)
            except queue.Empty:
                pass
            finally:
                self.root.after(50, _poll)
        self.root.after(50, _poll)


    def _build_ui(self):
        main_frame = ttk.Frame(self.root, padding="14 10 14 10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 0. Compact Header
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 8))

        title_label = ttk.Label(
            header_frame,
            text="🎬 Video-to-Lottie & GIF 변환기",
            font=(FONT_FAMILY, 15, "bold")
        )
        title_label.pack(side=tk.LEFT)

        subtitle_label = ttk.Label(
            header_frame,
            text=" (10초 이하 단색 배경 영상 → 투명 Lottie JSON & GIF 변환)",
            font=(FONT_FAMILY, 9),
            foreground="#666666"
        )
        subtitle_label.pack(side=tk.LEFT, padx=(6, 0), pady=(3, 0))

        # Two-Column Container Frame
        cols_container = ttk.Frame(main_frame)
        cols_container.pack(fill=tk.BOTH, expand=True)

        cols_container.columnconfigure(0, weight=1)
        cols_container.columnconfigure(1, weight=1)
        cols_container.rowconfigure(0, weight=1)

        left_col = ttk.Frame(cols_container)
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        right_col = ttk.Frame(cols_container)
        right_col.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        # ==========================================
        # LEFT COLUMN: Inputs & Settings
        # ==========================================

        # 1. Video File & Output Directory Selector Frame
        file_group = ttk.LabelFrame(left_col, text=" 1. 영상 파일 및 저장 위치 선택 ", padding="8 8 8 8")
        file_group.pack(fill=tk.X, pady=(0, 6))

        # Modern Drag & Drop Zone Box
        self.drop_zone_frame = ttk.Frame(file_group, padding="8 8 8 8", relief="groove")
        self.drop_zone_frame.pack(fill=tk.X, pady=(0, 6))
        self.drop_zone_frame.bind("<Button-1>", lambda e: self.browse_video())

        self.lbl_drop_title = ttk.Label(
            self.drop_zone_frame,
            text="📂 동영상 파일 끌어다 놓기 (Drag & Drop)",
            font=(FONT_FAMILY, 9, "bold"),
            foreground="#2563eb",
            cursor="pointinghand"
        )
        self.lbl_drop_title.pack(anchor=tk.CENTER)
        self.lbl_drop_title.bind("<Button-1>", lambda e: self.browse_video())

        self.lbl_drop_hint = ttk.Label(
            self.drop_zone_frame,
            text="여기에 .mp4, .mov 파일을 끌어다 놓거나 클릭하여 선택",
            font=(FONT_FAMILY, 8),
            foreground="#666666",
            cursor="pointinghand"
        )
        self.lbl_drop_hint.pack(anchor=tk.CENTER, pady=(2, 0))
        self.lbl_drop_hint.bind("<Button-1>", lambda e: self.browse_video())

        # Video File Path Row
        lbl_video = ttk.Label(file_group, text="입력 영상 경로:", font=(FONT_FAMILY, 8, "bold"))
        lbl_video.pack(anchor=tk.W, pady=(0, 2))

        file_select_frame = ttk.Frame(file_group)
        file_select_frame.pack(fill=tk.X, pady=(0, 2))

        self.file_path_var = tk.StringVar()
        self.file_entry = ttk.Entry(file_select_frame, textvariable=self.file_path_var, font=(FONT_FAMILY, 9))
        self.file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        btn_browse = ttk.Button(file_select_frame, text="파일 찾기...", command=self.browse_video)
        btn_browse.pack(side=tk.RIGHT)

        self.lbl_video_info = ttk.Label(
            file_group,
            text="영상 파일 선택 시 원본 해상도가 감지됩니다.",
            font=(FONT_FAMILY, 8),
            foreground="#2563eb"
        )
        self.lbl_video_info.pack(anchor=tk.W, pady=(0, 4))


        # Output Directory Row
        lbl_out = ttk.Label(file_group, text="결과 저장 폴더:", font=(FONT_FAMILY, 9, "bold"))
        lbl_out.pack(anchor=tk.W, pady=(0, 2))

        out_select_frame = ttk.Frame(file_group)
        out_select_frame.pack(fill=tk.X)

        self.output_dir_var = tk.StringVar(value=get_default_output_dir())
        out_entry = ttk.Entry(out_select_frame, textvariable=self.output_dir_var, font=(FONT_FAMILY, 9))
        out_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        btn_browse_out = ttk.Button(out_select_frame, text="폴더 변경...", command=self.browse_output_dir)
        btn_browse_out.pack(side=tk.RIGHT)

        # 2. Options Frame
        opts_group = ttk.LabelFrame(left_col, text=" 2. 내보내기 형식 및 고급 옵션 ", padding="8 8 8 8")
        opts_group.pack(fill=tk.BOTH, expand=True)

        # Option: Export Format (Lottie / GIF / Both)
        fmt_frame = ttk.Frame(opts_group)
        fmt_frame.pack(fill=tk.X, pady=2)
        lbl_fmt = ttk.Label(fmt_frame, text="내보내기 형식:", width=18, font=(FONT_FAMILY, 9, "bold"))
        lbl_fmt.pack(side=tk.LEFT)

        self.fmt_var = tk.StringVar(value="both")
        rb_both = ttk.Radiobutton(fmt_frame, text="Lottie+GIF (추천)", variable=self.fmt_var, value="both")
        rb_both.pack(side=tk.LEFT, padx=(0, 6))
        rb_lottie = ttk.Radiobutton(fmt_frame, text="Lottie만", variable=self.fmt_var, value="lottie")
        rb_lottie.pack(side=tk.LEFT, padx=(0, 6))
        rb_gif = ttk.Radiobutton(fmt_frame, text="GIF만", variable=self.fmt_var, value="gif")
        rb_gif.pack(side=tk.LEFT)

        # Option: Mode Selection (Image vs Vector)
        mode_frame = ttk.Frame(opts_group)
        mode_frame.pack(fill=tk.X, pady=2)
        lbl_mode = ttk.Label(mode_frame, text="변환 모드:", width=18, font=(FONT_FAMILY, 9))
        lbl_mode.pack(side=tk.LEFT)

        self.mode_var = tk.StringVar(value="image")
        rb_img = ttk.Radiobutton(mode_frame, text="원본 텍스처 (권장)", variable=self.mode_var, value="image")
        rb_img.pack(side=tk.LEFT, padx=(0, 6))
        rb_vec = ttk.Radiobutton(mode_frame, text="단색 벡터 실루엣", variable=self.mode_var, value="vector")
        rb_vec.pack(side=tk.LEFT)

        # Option: Output Resolution / Size
        size_frame = ttk.Frame(opts_group)
        size_frame.pack(fill=tk.X, pady=2)
        lbl_size = ttk.Label(size_frame, text="아웃풋 사이즈:", width=18, font=(FONT_FAMILY, 9))
        lbl_size.pack(side=tk.LEFT)

        self.size_preset_var = tk.StringVar(value="원본 유지 (100%)")
        size_combo = ttk.Combobox(
            size_frame,
            textvariable=self.size_preset_var,
            values=[
                "원본 유지 (100%)",
                "512 px 너비 (웹/모바일 추천)",
                "720 px 너비 (HD)",
                "1080 px 너비 (Full HD)",
                "직접 입력 (Custom)"
            ],
            state="readonly",
            width=22
        )
        size_combo.pack(side=tk.LEFT, padx=(0, 6))
        size_combo.bind("<<ComboboxSelected>>", self.on_size_preset_change)

        # Custom Width & Height Entries
        self.custom_frame = ttk.Frame(opts_group)
        self.custom_frame.pack(fill=tk.X, pady=2)

        lbl_custom_w = ttk.Label(self.custom_frame, text="   └ 너비:", font=(FONT_FAMILY, 9))
        lbl_custom_w.pack(side=tk.LEFT)
        self.out_width_var = tk.StringVar(value="")
        entry_w = ttk.Entry(self.custom_frame, textvariable=self.out_width_var, width=7)
        entry_w.pack(side=tk.LEFT, padx=(2, 8))

        lbl_custom_h = ttk.Label(self.custom_frame, text="높이:", font=(FONT_FAMILY, 9))
        lbl_custom_h.pack(side=tk.LEFT)
        self.out_height_var = tk.StringVar(value="")
        entry_h = ttk.Entry(self.custom_frame, textvariable=self.out_height_var, width=7)
        entry_h.pack(side=tk.LEFT, padx=(2, 6))

        lbl_aspect = ttk.Label(self.custom_frame, text="(한 쪽만 입력 시 비율 유지)", font=(FONT_FAMILY, 8), foreground="#888888")
        lbl_aspect.pack(side=tk.LEFT)

        # Option: Background Threshold
        thresh_frame = ttk.Frame(opts_group)
        thresh_frame.pack(fill=tk.X, pady=2)
        lbl_thresh = ttk.Label(thresh_frame, text="배경 감도 (Threshold):", width=18, font=(FONT_FAMILY, 9))
        lbl_thresh.pack(side=tk.LEFT)

        self.thresh_var = tk.DoubleVar(value=config.BACKGROUND_THRESHOLD)
        thresh_slider = ttk.Scale(
            thresh_frame,
            from_=5,
            to=80,
            variable=self.thresh_var,
            orient=tk.HORIZONTAL,
            command=self.update_thresh_label
        )
        thresh_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        self.lbl_thresh_val = ttk.Label(thresh_frame, text=str(int(config.BACKGROUND_THRESHOLD)), width=3, font=(FONT_FAMILY, 9, "bold"))
        self.lbl_thresh_val.pack(side=tk.LEFT)

        # NEW Option: Outer Background Only Checkbox (Default: True)
        outer_frame = ttk.Frame(opts_group)
        outer_frame.pack(fill=tk.X, pady=2)
        lbl_outer = ttk.Label(outer_frame, text="외곽만 제거 (추천):", width=18, font=(FONT_FAMILY, 9, "bold"), foreground="#2563eb")
        lbl_outer.pack(side=tk.LEFT)

        self.outer_only_var = tk.BooleanVar(value=getattr(config, "DEFAULT_OUTER_ONLY", True))
        chk_outer = ttk.Checkbutton(
            outer_frame,
            text="외곽 배경만 제거 (내부 동일 색상/디테일 보호)",
            variable=self.outer_only_var
        )
        chk_outer.pack(side=tk.LEFT)

        # NEW Option: Edge Trim / Border Halo Removal
        trim_frame = ttk.Frame(opts_group)
        trim_frame.pack(fill=tk.X, pady=2)
        lbl_trim = ttk.Label(trim_frame, text="테두리 자르기 (Trim):", width=18, font=(FONT_FAMILY, 9, "bold"), foreground="#059669")
        lbl_trim.pack(side=tk.LEFT)

        self.edge_trim_var = tk.IntVar(value=config.DEFAULT_EDGE_TRIM)
        trim_spin = ttk.Spinbox(trim_frame, from_=0, to=5, textvariable=self.edge_trim_var, width=5)
        trim_spin.pack(side=tk.LEFT, padx=(0, 6))

        lbl_trim_desc = ttk.Label(
            trim_frame,
            text="px (테두리 림 완벽 제거, 권장: 1~2px)",
            font=(FONT_FAMILY, 8),
            foreground="#059669"
        )
        lbl_trim_desc.pack(side=tk.LEFT)

        # NEW Option: Edge Feather / Blur
        blur_frame = ttk.Frame(opts_group)
        blur_frame.pack(fill=tk.X, pady=2)
        lbl_blur = ttk.Label(blur_frame, text="테두리 블렌딩 (Feather):", width=18, font=(FONT_FAMILY, 9))
        lbl_blur.pack(side=tk.LEFT)

        self.edge_blur_var = tk.IntVar(value=config.DEFAULT_EDGE_BLUR)
        blur_spin = ttk.Spinbox(blur_frame, from_=0, to=7, textvariable=self.edge_blur_var, width=5)
        blur_spin.pack(side=tk.LEFT, padx=(0, 6))

        lbl_blur_desc = ttk.Label(blur_frame, text="px (가장자리 페더링)", font=(FONT_FAMILY, 8), foreground="#888888")
        lbl_blur_desc.pack(side=tk.LEFT)

        # Option: Target FPS
        fps_frame = ttk.Frame(opts_group)
        fps_frame.pack(fill=tk.X, pady=2)
        lbl_fps = ttk.Label(fps_frame, text="초당 프레임 (FPS):", width=18, font=(FONT_FAMILY, 9))
        lbl_fps.pack(side=tk.LEFT)

        self.fps_var = tk.StringVar(value="30")
        fps_combo = ttk.Combobox(
            fps_frame,
            textvariable=self.fps_var,
            values=["12", "15", "24", "30", "60"],
            state="normal",
            width=8
        )
        fps_combo.pack(side=tk.LEFT)

        lbl_fps_desc = ttk.Label(
            fps_frame,
            text=" (기본값: 30 FPS)",
            font=(FONT_FAMILY, 8),
            foreground="#888888"
        )
        lbl_fps_desc.pack(side=tk.LEFT, padx=4)

        # ==========================================
        # RIGHT COLUMN: Execution, Log & Results
        # ==========================================

        # 3. Execution & Progress
        exec_group = ttk.LabelFrame(right_col, text=" 3. 변환 실행 ", padding="8 8 8 8")
        exec_group.pack(fill=tk.X, pady=(0, 8))

        self.btn_convert = ttk.Button(
            exec_group,
            text="🚀 Lottie & GIF 변환 시작",
            command=self.start_conversion_thread
        )
        self.btn_convert.pack(fill=tk.X, ipady=6)

        self.progress_bar = ttk.Progressbar(exec_group, mode="indeterminate")
        self.progress_bar.pack(fill=tk.X, pady=(6, 2))

        # 4. Log Text Box (Expands to fill vertical space)
        log_group = ttk.LabelFrame(right_col, text=" 4. 진행 상황 실시간 로그 ", padding="6 6 6 6")
        log_group.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        self.log_text = tk.Text(
            log_group,
            height=8,
            font=("Consolas", 9),
            bg="#1e1e1e",
            fg="#d4d4d4",
            wrap=tk.WORD
        )
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(log_group, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)

        # 5. Result Actions Frame (Download & Open Folder)
        result_group = ttk.LabelFrame(right_col, text=" 5. 결과 파일 관리 및 열기 ", padding="8 8 8 8")
        result_group.pack(fill=tk.X)

        self.btn_open_folder = ttk.Button(
            result_group,
            text="📁 저장 폴더 열기",
            command=self.open_output_folder
        )
        self.btn_open_folder.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))

        self.btn_download_json = ttk.Button(
            result_group,
            text="💾 Lottie JSON 저장",
            command=self.download_lottie_file,
            state=tk.DISABLED
        )
        self.btn_download_json.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 2))

        self.btn_download_gif = ttk.Button(
            result_group,
            text="💾 GIF 저장",
            command=self.download_gif_file,
            state=tk.DISABLED
        )
        self.btn_download_gif.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(2, 0))


    def on_size_preset_change(self, event):
        val = self.size_preset_var.get()
        if "512" in val:
            self.out_width_var.set("512")
            self.out_height_var.set("")
        elif "720" in val:
            self.out_width_var.set("720")
            self.out_height_var.set("")
        elif "1080" in val:
            self.out_width_var.set("1080")
            self.out_height_var.set("")
        elif "원본" in val:
            self.out_width_var.set("")
            self.out_height_var.set("")

    def update_thresh_label(self, val):
        self.lbl_thresh_val.config(text=f"{int(float(val))}")

    def load_video(self, filename: str):
        if not filename or not os.path.exists(filename):
            return

        valid_exts = ('.mp4', '.mov', '.avi', '.mkv', '.webm')
        ext = os.path.splitext(filename)[1].lower()
        if ext not in valid_exts:
            messagebox.showwarning(
                "지원하지 않는 형식",
                f"지원되는 동영상 파일(.mp4, .mov 등)을 선택해 주세요.\n선택된 파일: {os.path.basename(filename)}"
            )
            return

        self.file_path_var.set(filename)

        # If user hasn't customized the output folder, set it next to the input video
        if not self.user_customized_output_dir:
            video_dir = os.path.dirname(os.path.abspath(filename))
            self.output_dir_var.set(os.path.join(video_dir, "lottie-output"))

        # Update visual drop zone text
        short_name = os.path.basename(filename)
        if hasattr(self, 'lbl_drop_title'):
            self.lbl_drop_title.config(
                text=f"🎬 선택된 영상: {short_name}",
                foreground="#059669"
            )
        if hasattr(self, 'lbl_drop_hint'):
            self.lbl_drop_hint.config(
                text="다른 영상을 끌어다 놓거나 클릭하여 변경 가능"
            )

        try:
            reader = VideoReader(filename)
            info = reader.get_info()
            reader.release()
            self.orig_w = info['width']
            self.orig_h = info['height']
            self.lbl_video_info.config(
                text=f"🎥 감지된 원본 해상도: Width={info['width']}px, Height={info['height']}px (재생시간: {info['duration']}초, FPS: {info['fps']})",
                foreground="#059669"
            )
        except Exception as e:
            self.lbl_video_info.config(text=f"⚠️ 영상 읽기 오류: {e}", foreground="#dc2626")

    def browse_video(self):
        filename = filedialog.askopenfilename(
            title="동영상 파일 선택",
            filetypes=[
                ("Video Files", "*.mp4 *.mov *.avi *.mkv *.webm"),
                ("MP4 Videos", "*.mp4"),
                ("MOV Videos", "*.mov"),
                ("All Files", "*.*")
            ]
        )
        if filename:
            self.load_video(filename)

    def _setup_drag_and_drop(self):
        """Registers OS drag-and-drop file target on the window and widgets."""
        if not HAS_DND:
            return

        def handle_drop(event):
            raw_data = getattr(event, 'data', '')
            paths = parse_dropped_files(raw_data)
            if not paths:
                return

            video_exts = ('.mp4', '.mov', '.avi', '.mkv', '.webm')
            target_file = None
            for p in paths:
                if os.path.exists(p) and p.lower().endswith(video_exts):
                    target_file = p
                    break

            if target_file:
                self.load_video(target_file)
            else:
                first_name = os.path.basename(paths[0]) if paths else "파일"
                messagebox.showwarning(
                    "지원하지 않는 파일",
                    f"동영상 파일(.mp4, .mov, .avi, .mkv, .webm)을 끌어다 놓아주세요.\n드롭된 파일: {first_name}"
                )

        # Register drop target across root window, drop zone box, and file entry
        targets = [self.root]
        for attr in ['drop_zone_frame', 'lbl_drop_title', 'lbl_drop_hint', 'file_entry']:
            w = getattr(self, attr, None)
            if w is not None:
                targets.append(w)

        for target in targets:
            try:
                target.drop_target_register(DND_FILES)
                target.dnd_bind('<<Drop>>', handle_drop)
            except Exception:
                pass


    def browse_output_dir(self):
        cur_dir = self.output_dir_var.get().strip() or os.path.expanduser("~")
        if not os.path.exists(cur_dir):
            parent = os.path.dirname(cur_dir)
            cur_dir = parent if os.path.exists(parent) else os.path.expanduser("~")
        selected_dir = filedialog.askdirectory(
            title="저장할 폴더 선택",
            initialdir=cur_dir
        )
        if selected_dir:
            self.output_dir_var.set(selected_dir)
            self.user_customized_output_dir = True

    def log(self, text: str):
        # Put into thread-safe queue; main GUI thread will consume and render
        self.msg_queue.put(("log", str(text)))

    def start_conversion_thread(self):
        video_path = self.file_path_var.get().strip()
        if not video_path or not os.path.exists(video_path):
            messagebox.showerror("오류", "올바른 동영상 파일을 선택해 주세요.")
            return

        # Read all UI variables safely on the MAIN THREAD
        output_dir = self.output_dir_var.get().strip()
        if not output_dir:
            video_dir = os.path.dirname(os.path.abspath(video_path))
            output_dir = os.path.join(video_dir, "lottie-output")
            self.output_dir_var.set(output_dir)

        fmt = self.fmt_var.get()
        mode = self.mode_var.get()
        try:
            target_fps = float(self.fps_var.get())
        except (ValueError, TypeError):
            target_fps = 30.0

        try:
            threshold = float(self.thresh_var.get())
        except (ValueError, TypeError):
            threshold = float(config.BACKGROUND_THRESHOLD)

        try:
            edge_trim = int(self.edge_trim_var.get())
        except (ValueError, TypeError):
            edge_trim = int(config.DEFAULT_EDGE_TRIM)

        try:
            edge_blur = int(self.edge_blur_var.get())
        except (ValueError, TypeError):
            edge_blur = int(config.DEFAULT_EDGE_BLUR)

        outer_only = bool(self.outer_only_var.get())

        target_w_str = self.out_width_var.get().strip()
        target_h_str = self.out_height_var.get().strip()
        target_w = int(target_w_str) if target_w_str.isdigit() else None
        target_h = int(target_h_str) if target_h_str.isdigit() else None

        params = {
            "video_path": video_path,
            "output_dir": output_dir,
            "fmt": fmt,
            "mode": mode,
            "target_fps": target_fps,
            "threshold": threshold,
            "edge_trim": edge_trim,
            "edge_blur": edge_blur,
            "outer_only": outer_only,
            "target_w": target_w,
            "target_h": target_h,
        }

        self.btn_convert.config(state=tk.DISABLED)
        self.btn_download_json.config(state=tk.DISABLED)
        self.btn_download_gif.config(state=tk.DISABLED)
        self.progress_bar.start(10)
        self.log_text.delete("1.0", tk.END)

        thread = threading.Thread(target=self.run_conversion, args=(params,), daemon=True)
        thread.start()

    def run_conversion(self, params: dict):
        try:
            video_path = params["video_path"]
            output_dir = params["output_dir"]
            fmt = params["fmt"]
            mode = params["mode"]
            target_fps = params["target_fps"]
            threshold = params["threshold"]
            edge_trim = params["edge_trim"]
            edge_blur = params["edge_blur"]
            outer_only = params.get("outer_only", True)
            target_w = params["target_w"]
            target_h = params["target_h"]

            base_name = os.path.splitext(os.path.basename(video_path))[0]

            try:
                os.makedirs(output_dir, exist_ok=True)
            except Exception as e:
                err = f"저장 폴더를 생성할 수 없습니다 ({output_dir}): {e}"
                self.log(f"❌ {err}")
                self.msg_queue.put(("error", err))
                return

            self.log(f"[1/6] 영상 읽기 중: {video_path}")
            reader = VideoReader(video_path)
            info = reader.get_info()

            out_w, out_h = FrameProcessor.compute_target_dimensions(
                info['width'], info['height'], target_w, target_h
            )

            self.log(f"  - 원본 해상도: {info['width']}x{info['height']} px")
            self.log(f"  - 지정 아웃풋 해상도: {out_w}x{out_h} px (FPS: {target_fps})")

            self.log("[2/6] 배경색 자동 검출 중...")
            detector = BackgroundDetector()
            bg_color, is_consistent = detector.validate_multi_frame_background(reader)
            rgb = bg_color["rgb"]
            self.log(f"  - 검출된 배경색: RGB({rgb[0]}, {rgb[1]}, {rgb[2]})")

            outer_desc = "외곽만 제거 (내부 보호)" if outer_only else "전체 색상 제거"
            self.log(f"[3/6] 배경 마스크 처리 (Threshold: {threshold}, Trim: {edge_trim}px, {outer_desc})...")
            remover = BackgroundRemover(
                threshold=threshold,
                edge_trim=edge_trim,
                edge_blur=edge_blur,
                outer_only=outer_only
            )

            sampled_rgba_frames = []
            all_frame_contours = []

            self.log("[4/6] 프레임별 배경 제거 & 테두리 림 자르기 적용 중...")
            for frame_idx, timestamp, frame in reader.extract_sampled_frames(target_fps=target_fps):
                rgba = remover.extract_rgba_foreground(
                    frame, bg_color, threshold=threshold, soft=True, edge_trim=edge_trim, edge_blur=edge_blur, outer_only=outer_only
                )
                sampled_rgba_frames.append(rgba)
                if mode == "vector" and fmt in ["lottie", "both"]:
                    mask = remover.process_frame(frame, bg_color, threshold=threshold, edge_trim=edge_trim, edge_blur=edge_blur, outer_only=outer_only)
                    extractor = ContourExtractor()
                    contours = extractor.extract_and_simplify(mask)
                    all_frame_contours.append(contours)

            reader.release()

            self.log("[5/6] 내보내기 파일 생성 중...")
            exported_json = None
            exported_gif = None

            if fmt in ["gif", "both"]:
                gif_path = os.path.join(output_dir, f"{base_name}.gif")
                GifWriter.save_gif(sampled_rgba_frames, gif_path, fps=target_fps, target_width=out_w, target_height=out_h)
                exported_gif = gif_path
                self.log(f"  - GIF 내보내기 완료: {gif_path}")

            if fmt in ["lottie", "both"]:
                lottie_path = os.path.join(output_dir, f"{base_name}.json")
                writer = LottieWriter(width=out_w, height=out_h, fps=target_fps)
                if mode == "image":
                    lottie_dict = writer.create_image_lottie_dict(sampled_rgba_frames)
                else:
                    converter = LottiePathConverter(scale_x=out_w/info['width'], scale_y=out_h/info['height'])
                    lottie_dict = writer.create_lottie_dict(all_frame_contours, converter)
                writer.save_lottie_json(lottie_dict, lottie_path)
                exported_json = lottie_path
                self.log(f"  - Lottie JSON 내보내기 완료: {lottie_path}")

            self.log("\n[6/6] ✅ 변환 성공!")
            self.log(f"저장 위치: {output_dir}")

            self.msg_queue.put(("success", (exported_json, exported_gif)))

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.log(f"\n❌ 오류 발생: {e}")
            self.msg_queue.put(("error", str(e)))

    def on_conversion_success(self, json_path, gif_path):
        self.last_generated_json = json_path
        self.last_generated_gif = gif_path
        self.progress_bar.stop()
        self.btn_convert.config(state=tk.NORMAL)
        if json_path:
            self.btn_download_json.config(state=tk.NORMAL)
        if gif_path:
            self.btn_download_gif.config(state=tk.NORMAL)

        save_folder = os.path.dirname(json_path or gif_path)
        msg = f"변환 작업이 성공적으로 완료되었습니다!\n\n저장 폴더:\n{save_folder}\n\n생성된 파일:"
        if json_path:
            msg += f"\n- {os.path.basename(json_path)}"
        if gif_path:
            msg += f"\n- {os.path.basename(gif_path)}"

        messagebox.showinfo("변환 완료", msg)


    def on_conversion_error(self, err_msg):
        self.progress_bar.stop()
        self.btn_convert.config(state=tk.NORMAL)
        messagebox.showerror("변환 실패", f"작업 중 오류가 발생했습니다:\n{err_msg}")

    def open_output_folder(self):
        output_dir = self.output_dir_var.get().strip() or get_default_output_dir()
        try:
            os.makedirs(output_dir, exist_ok=True)
            if sys.platform == 'win32':
                os.startfile(output_dir)
            elif sys.platform == 'darwin':
                subprocess.run(["open", output_dir])
            else:
                subprocess.run(["xdg-open", output_dir])
        except Exception as e:
            messagebox.showerror("오류", f"폴더를 열 수 없습니다: {e}")


    def download_lottie_file(self):
        if not self.last_generated_json or not os.path.exists(self.last_generated_json):
            messagebox.showwarning("경고", "다운로드할 Lottie JSON 파일이 없습니다.")
            return

        default_name = os.path.basename(self.last_generated_json)
        save_path = filedialog.asksaveasfilename(
            title="Lottie JSON 파일 저장",
            initialfile=default_name,
            defaultextension=".json",
            filetypes=[("Lottie JSON Files", "*.json"), ("All Files", "*.*")]
        )
        if save_path:
            shutil.copy2(self.last_generated_json, save_path)
            messagebox.showinfo("저장 완료", f"Lottie 파일이 저장되었습니다:\n{save_path}")

    def download_gif_file(self):
        if not self.last_generated_gif or not os.path.exists(self.last_generated_gif):
            messagebox.showwarning("경고", "다운로드할 GIF 애니메이션 파일이 없습니다.")
            return

        default_name = os.path.basename(self.last_generated_gif)
        save_path = filedialog.asksaveasfilename(
            title="GIF 애니메이션 파일 저장",
            initialfile=default_name,
            defaultextension=".gif",
            filetypes=[("Animated GIF Files", "*.gif"), ("All Files", "*.*")]
        )
        if save_path:
            shutil.copy2(self.last_generated_gif, save_path)
            messagebox.showinfo("저장 완료", f"GIF 파일이 저장되었습니다:\n{save_path}")


def main():
    if HAS_DND:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    app = LottieConverterGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
