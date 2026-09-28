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
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
import cv2

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


class LottieConverterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("단색 배경 제거 → Lottie JSON & GIF 변환기")
        self.root.geometry("720x820")
        self.root.minsize(660, 720)

        self.style = ttk.Style()
        self.style.theme_use('clam')

        self.last_generated_json = None
        self.last_generated_gif = None
        self.orig_w = 0
        self.orig_h = 0

        self._build_ui()

    def _build_ui(self):
        main_frame = ttk.Frame(self.root, padding="16 16 16 16")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title Label
        title_label = ttk.Label(
            main_frame,
            text="🎬 Video-to-Lottie & GIF 변환기",
            font=("Malgun Gothic", 16, "bold")
        )
        title_label.pack(anchor=tk.W, pady=(0, 4))

        subtitle_label = ttk.Label(
            main_frame,
            text="10초 이하 단색 배경 동영상(.mp4, .mov)을 투명 Lottie JSON 또는 GIF 애니메이션으로 변환합니다.",
            font=("Malgun Gothic", 9),
            foreground="#666666"
        )
        subtitle_label.pack(anchor=tk.W, pady=(0, 16))

        # 1. Video File Selector Frame
        file_group = ttk.LabelFrame(main_frame, text=" 1. 영상 파일 선택 및 원본 해상도 ", padding="12 12 12 12")
        file_group.pack(fill=tk.X, pady=(0, 12))

        file_select_frame = ttk.Frame(file_group)
        file_select_frame.pack(fill=tk.X, pady=(0, 4))

        self.file_path_var = tk.StringVar()
        file_entry = ttk.Entry(file_select_frame, textvariable=self.file_path_var, font=("Malgun Gothic", 10))
        file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

        btn_browse = ttk.Button(file_select_frame, text="파일 찾기...", command=self.browse_video)
        btn_browse.pack(side=tk.RIGHT)

        self.lbl_video_info = ttk.Label(
            file_group,
            text="영상 파일 선택 시 원본 Width x Height 해상도가 감지됩니다.",
            font=("Malgun Gothic", 9),
            foreground="#2563eb"
        )
        self.lbl_video_info.pack(anchor=tk.W, pady=(2, 0))

        # 2. Options Frame
        opts_group = ttk.LabelFrame(main_frame, text=" 2. 내보내기 형식 및 고급 옵션 설정 ", padding="12 12 12 12")
        opts_group.pack(fill=tk.X, pady=(0, 12))

        # Option: Export Format (Lottie / GIF / Both)
        fmt_frame = ttk.Frame(opts_group)
        fmt_frame.pack(fill=tk.X, pady=4)
        lbl_fmt = ttk.Label(fmt_frame, text="내보내기 형식 (Format):", width=22, font=("Malgun Gothic", 9, "bold"))
        lbl_fmt.pack(side=tk.LEFT)

        self.fmt_var = tk.StringVar(value="both")
        rb_both = ttk.Radiobutton(fmt_frame, text="Lottie + GIF 모두 생성 (추천)", variable=self.fmt_var, value="both")
        rb_both.pack(side=tk.LEFT, padx=(0, 8))
        rb_lottie = ttk.Radiobutton(fmt_frame, text="Lottie JSON만", variable=self.fmt_var, value="lottie")
        rb_lottie.pack(side=tk.LEFT, padx=(0, 8))
        rb_gif = ttk.Radiobutton(fmt_frame, text="투명 GIF만", variable=self.fmt_var, value="gif")
        rb_gif.pack(side=tk.LEFT)

        # Option: Mode Selection (Image vs Vector)
        mode_frame = ttk.Frame(opts_group)
        mode_frame.pack(fill=tk.X, pady=4)
        lbl_mode = ttk.Label(mode_frame, text="변환 모드:", width=22, font=("Malgun Gothic", 9))
        lbl_mode.pack(side=tk.LEFT)

        self.mode_var = tk.StringVar(value="image")
        rb_img = ttk.Radiobutton(mode_frame, text="원본 영상 이미지 텍스처 (권장)", variable=self.mode_var, value="image")
        rb_img.pack(side=tk.LEFT, padx=(0, 8))
        rb_vec = ttk.Radiobutton(mode_frame, text="단색 벡터 실루엣", variable=self.mode_var, value="vector")
        rb_vec.pack(side=tk.LEFT)

        # Option: Output Resolution / Size
        size_frame = ttk.Frame(opts_group)
        size_frame.pack(fill=tk.X, pady=4)
        lbl_size = ttk.Label(size_frame, text="아웃풋 사이즈 (Size):", width=22, font=("Malgun Gothic", 9))
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
            width=24
        )
        size_combo.pack(side=tk.LEFT, padx=(0, 8))
        size_combo.bind("<<ComboboxSelected>>", self.on_size_preset_change)

        # Custom Width & Height Entries
        self.custom_frame = ttk.Frame(opts_group)
        self.custom_frame.pack(fill=tk.X, pady=4)

        lbl_custom_w = ttk.Label(self.custom_frame, text="   └ 너비 (Width):", font=("Malgun Gothic", 9))
        lbl_custom_w.pack(side=tk.LEFT)
        self.out_width_var = tk.StringVar(value="")
        entry_w = ttk.Entry(self.custom_frame, textvariable=self.out_width_var, width=8)
        entry_w.pack(side=tk.LEFT, padx=(4, 12))

        lbl_custom_h = ttk.Label(self.custom_frame, text="높이 (Height):", font=("Malgun Gothic", 9))
        lbl_custom_h.pack(side=tk.LEFT)
        self.out_height_var = tk.StringVar(value="")
        entry_h = ttk.Entry(self.custom_frame, textvariable=self.out_height_var, width=8)
        entry_h.pack(side=tk.LEFT, padx=(4, 8))

        lbl_aspect = ttk.Label(self.custom_frame, text="(한 쪽만 입력 시 비율 자동 유지)", font=("Malgun Gothic", 8), foreground="#888888")
        lbl_aspect.pack(side=tk.LEFT)

        # Option: Background Threshold
        thresh_frame = ttk.Frame(opts_group)
        thresh_frame.pack(fill=tk.X, pady=4)
        lbl_thresh = ttk.Label(thresh_frame, text="배경 감도 (Threshold):", width=22, font=("Malgun Gothic", 9))
        lbl_thresh.pack(side=tk.LEFT)

        self.thresh_var = tk.DoubleVar(value=config.BACKGROUND_THRESHOLD)
        thresh_slider = ttk.Scale(
            thresh_frame,
            from_=10,
            to=80,
            variable=self.thresh_var,
            orient=tk.HORIZONTAL,
            command=self.update_thresh_label
        )
        thresh_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

        self.lbl_thresh_val = ttk.Label(thresh_frame, text="35", width=4, font=("Malgun Gothic", 9, "bold"))
        self.lbl_thresh_val.pack(side=tk.LEFT)

        # NEW Option: Edge Trim / Border Halo Removal (핵심: 검정/녹색 테두리 림 제거)
        trim_frame = ttk.Frame(opts_group)
        trim_frame.pack(fill=tk.X, pady=4)
        lbl_trim = ttk.Label(trim_frame, text="테두리 자르기 (Edge Trim):", width=22, font=("Malgun Gothic", 9, "bold"), foreground="#059669")
        lbl_trim.pack(side=tk.LEFT)

        self.edge_trim_var = tk.IntVar(value=config.DEFAULT_EDGE_TRIM)
        trim_spin = ttk.Spinbox(trim_frame, from_=0, to=5, textvariable=self.edge_trim_var, width=6)
        trim_spin.pack(side=tk.LEFT, padx=(0, 6))

        lbl_trim_desc = ttk.Label(
            trim_frame,
            text="px (검정/녹색 테두리 림 완벽 제거, 권장: 1~2px)",
            font=("Malgun Gothic", 8),
            foreground="#059669"
        )
        lbl_trim_desc.pack(side=tk.LEFT)

        # NEW Option: Edge Feather / Blur
        blur_frame = ttk.Frame(opts_group)
        blur_frame.pack(fill=tk.X, pady=4)
        lbl_blur = ttk.Label(blur_frame, text="테두리 부드럽게 (Feather):", width=22, font=("Malgun Gothic", 9))
        lbl_blur.pack(side=tk.LEFT)

        self.edge_blur_var = tk.IntVar(value=config.DEFAULT_EDGE_BLUR)
        blur_spin = ttk.Spinbox(blur_frame, from_=0, to=7, textvariable=self.edge_blur_var, width=6)
        blur_spin.pack(side=tk.LEFT, padx=(0, 6))

        lbl_blur_desc = ttk.Label(blur_frame, text="px (가장자리 블렌딩 페더링)", font=("Malgun Gothic", 8), foreground="#888888")
        lbl_blur_desc.pack(side=tk.LEFT)

        # Option: Target FPS
        fps_frame = ttk.Frame(opts_group)
        fps_frame.pack(fill=tk.X, pady=4)
        lbl_fps = ttk.Label(fps_frame, text="초당 프레임 (FPS):", width=22, font=("Malgun Gothic", 9))
        lbl_fps.pack(side=tk.LEFT)

        self.fps_var = tk.StringVar(value="30")
        fps_combo = ttk.Combobox(
            fps_frame,
            textvariable=self.fps_var,
            values=["12", "15", "24", "30", "60"],
            state="normal",
            width=10
        )
        fps_combo.pack(side=tk.LEFT)

        lbl_fps_desc = ttk.Label(
            fps_frame,
            text=" (기본값: 30 FPS, 직접 숫자 입력 가능)",
            font=("Malgun Gothic", 8),
            foreground="#888888"
        )
        lbl_fps_desc.pack(side=tk.LEFT, padx=4)

        # 3. Execution & Progress
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, pady=(4, 8))

        self.btn_convert = ttk.Button(
            action_frame,
            text="🚀 Lottie & GIF 변환 시작",
            command=self.start_conversion_thread
        )
        self.btn_convert.pack(fill=tk.X, ipady=6)

        self.progress_bar = ttk.Progressbar(main_frame, mode="indeterminate")
        self.progress_bar.pack(fill=tk.X, pady=(0, 8))

        # Log Text Box
        log_frame = ttk.LabelFrame(main_frame, text=" 진행 상황 로그 ", padding="8 8 8 8")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        self.log_text = tk.Text(
            log_frame,
            height=6,
            font=("Consolas", 9),
            bg="#1e1e1e",
            fg="#d4d4d4",
            wrap=tk.WORD
        )
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)

        # 4. Result Actions Frame (Download & Open Folder)
        self.result_frame = ttk.Frame(main_frame)
        self.result_frame.pack(fill=tk.X)

        self.btn_open_folder = ttk.Button(
            self.result_frame,
            text="📁 lottie-output 폴더 열기",
            command=self.open_output_folder
        )
        self.btn_open_folder.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))

        self.btn_download_json = ttk.Button(
            self.result_frame,
            text="💾 Lottie JSON 저장",
            command=self.download_lottie_file,
            state=tk.DISABLED
        )
        self.btn_download_json.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 2))

        self.btn_download_gif = ttk.Button(
            self.result_frame,
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

    def browse_video(self):
        filename = filedialog.askopenfilename(
            title="동영상 파일 선택",
            filetypes=[
                ("Video Files", "*.mp4 *.mov *.avi *.mkv"),
                ("MP4 Videos", "*.mp4"),
                ("MOV Videos", "*.mov"),
                ("All Files", "*.*")
            ]
        )
        if filename:
            self.file_path_var.set(filename)
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

    def log(self, text: str):
        self.log_text.insert(tk.END, text + "\n")
        self.log_text.see(tk.END)

    def start_conversion_thread(self):
        video_path = self.file_path_var.get().strip()
        if not video_path or not os.path.exists(video_path):
            messagebox.showerror("오류", "올바른 동영상 파일을 선택해 주세요.")
            return

        self.btn_convert.config(state=tk.DISABLED)
        self.btn_download_json.config(state=tk.DISABLED)
        self.btn_download_gif.config(state=tk.DISABLED)
        self.progress_bar.start(10)
        self.log_text.delete("1.0", tk.END)

        thread = threading.Thread(target=self.run_conversion, daemon=True)
        thread.start()

    def run_conversion(self):
        video_path = self.file_path_var.get().strip()
        fmt = self.fmt_var.get()
        mode = self.mode_var.get()
        target_fps = float(self.fps_var.get())
        threshold = float(self.thresh_var.get())
        edge_trim = int(self.edge_trim_var.get())
        edge_blur = int(self.edge_blur_var.get())

        target_w_str = self.out_width_var.get().strip()
        target_h_str = self.out_height_var.get().strip()
        target_w = int(target_w_str) if target_w_str.isdigit() else None
        target_h = int(target_h_str) if target_h_str.isdigit() else None

        base_name = os.path.splitext(os.path.basename(video_path))[0]
        output_dir = os.path.abspath(config.OUTPUT_DIR)
        os.makedirs(output_dir, exist_ok=True)

        try:
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

            self.log(f"[3/6] 배경 제거 마스크 처리 중 (Threshold: {threshold}, Edge Trim: {edge_trim}px)...")
            remover = BackgroundRemover(
                threshold=threshold,
                edge_trim=edge_trim,
                edge_blur=edge_blur
            )

            sampled_rgba_frames = []
            all_frame_contours = []

            self.log("[4/6] 프레임별 배경 제거 & 테두리 림 자르기 적용 중...")
            for frame_idx, timestamp, frame in reader.extract_sampled_frames(target_fps=target_fps):
                rgba = remover.extract_rgba_foreground(
                    frame, bg_color, threshold=threshold, soft=True, edge_trim=edge_trim, edge_blur=edge_blur
                )
                sampled_rgba_frames.append(rgba)
                if mode == "vector" and fmt in ["lottie", "both"]:
                    mask = remover.process_frame(frame, bg_color, threshold=threshold, edge_trim=edge_trim, edge_blur=edge_blur)
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
                self.last_generated_gif = gif_path
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
                self.last_generated_json = lottie_path
                self.log(f"  - Lottie JSON 내보내기 완료: {lottie_path}")

            self.log("\n[6/6] ✅ 변환 성공!")
            self.log(f"lottie-output 저장 위치: {output_dir}")

            self.root.after(0, self.on_conversion_success, exported_json, exported_gif)

        except Exception as e:
            self.log(f"\n❌ 오류 발생: {e}")
            self.root.after(0, self.on_conversion_error, str(e))

    def on_conversion_success(self, json_path, gif_path):
        self.progress_bar.stop()
        self.btn_convert.config(state=tk.NORMAL)
        if json_path:
            self.btn_download_json.config(state=tk.NORMAL)
        if gif_path:
            self.btn_download_gif.config(state=tk.NORMAL)

        msg = "변환 작업이 성공적으로 완료되었습니다!\n\nlottie-output 폴더에 저장됨:"
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
        output_dir = os.path.abspath(config.OUTPUT_DIR)
        os.makedirs(output_dir, exist_ok=True)
        if sys.platform == 'win32':
            os.startfile(output_dir)
        elif sys.platform == 'darwin':
            subprocess.run(["open", output_dir])
        else:
            subprocess.run(["xdg-open", output_dir])

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
    root = tk.Tk()
    app = LottieConverterGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
