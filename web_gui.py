"""
Web GUI Server for Video to Lottie JSON and Animated GIF Converter.
Uses Python Standard Library http.server (No Flask/Django required).
Supports Edge Trim (halo removal), Output Format (Lottie JSON / GIF / Both) and Output Dimensions.
Serves web interface at http://localhost:5000
"""

import os
import sys
import json
import urllib.parse
import shutil
import base64
from http.server import HTTPServer, BaseHTTPRequestHandler
import email.message

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

PORT = 5000

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Lottie & GIF Converter Web GUI</title>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/lottie-web/5.12.2/lottie.min.js"></script>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #121214; color: #e4e4e7; padding: 24px; display: flex; flex-direction: column; align-items: center; }
    .card { background: #18181b; border: 1px solid #27272a; border-radius: 16px; width: 100%; max-width: 780px; padding: 24px; margin-bottom: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }
    h1 { font-size: 1.6rem; color: #fff; margin-bottom: 6px; }
    p.sub { font-size: 0.9rem; color: #a1a1aa; margin-bottom: 20px; }
    .form-group { margin-bottom: 16px; }
    label { display: block; font-size: 0.88rem; color: #d4d4d8; margin-bottom: 6px; font-weight: 600; }
    input[type="file"], select, input[type="number"], input[type="text"] { width: 100%; padding: 10px 12px; background: #27272a; border: 1px solid #3f3f46; border-radius: 8px; color: #fff; font-size: 0.95rem; }
    .row { display: flex; gap: 12px; }
    .row > div { flex: 1; }
    button { width: 100%; background: #2563eb; color: #fff; font-size: 1rem; font-weight: 600; padding: 12px; border: none; border-radius: 8px; cursor: pointer; transition: background 0.2s; margin-top: 8px; }
    button:hover { background: #1d4ed8; }
    button:disabled { background: #3f3f46; cursor: not-allowed; }
    #log { background: #09090b; border: 1px solid #27272a; border-radius: 8px; padding: 12px; font-family: monospace; font-size: 0.85rem; color: #10b981; height: 150px; overflow-y: auto; white-space: pre-wrap; margin-top: 16px; display: none; }
    .preview-box { width: 100%; height: 360px; border-radius: 12px; border: 2px dashed #3f3f46; display: flex; justify-content: center; align-items: center; background-image: linear-gradient(45deg, #1f1f23 25%, transparent 25%), linear-gradient(-45deg, #1f1f23 25%, transparent 25%), linear-gradient(45deg, transparent 75%, #1f1f23 75%), linear-gradient(-45deg, transparent 75%, #1f1f23 75%); background-size: 20px 20px; background-position: 0 0, 0 10px, 10px -10px, -10px 0px; margin-top: 16px; }
    .btn-group { display: flex; gap: 10px; margin-top: 12px; }
    .download-btn { flex: 1; text-decoration: none; text-align: center; color: #fff; font-weight: 600; padding: 12px; border-radius: 8px; background: #059669; }
    .download-btn:hover { background: #047857; }
    .download-btn.gif-btn { background: #d97706; }
    .download-btn.gif-btn:hover { background: #b45309; }
    .highlight-label { color: #34d399 !important; }
  </style>
</head>
<body>
  <div class="card">
    <h1>🎬 Lottie & GIF 변환 Web GUI</h1>
    <p class="sub">동영상 배경을 제거하고 테두리 림(Rim)을 자른 깔끔한 투명 Lottie/GIF로 변환합니다.</p>

    <form id="convert-form">
      <div class="form-group">
        <label>1. 동영상 파일 선택 (.mp4, .mov)</label>
        <input type="file" id="video-file" accept=".mp4,.mov" required>
      </div>

      <div class="row">
        <div class="form-group">
          <label>2. 내보내기 형식 (Format)</label>
          <select id="format">
            <option value="both" selected>Lottie + GIF 모두 생성 (추천)</option>
            <option value="lottie">Lottie JSON만 생성</option>
            <option value="gif">투명 GIF만 생성</option>
          </select>
        </div>

        <div class="form-group">
          <label>3. 아웃풋 Width (너비 px)</label>
          <input type="number" id="out-width" placeholder="원본 유지 (예: 512)">
        </div>

        <div class="form-group">
          <label>4. 아웃풋 Height (높이 px)</label>
          <input type="number" id="out-height" placeholder="비율 자동 계산">
        </div>
      </div>

      <div class="row">
        <div class="form-group">
          <label class="highlight-label">5. 테두리 자르기 (Edge Trim px)</label>
          <input type="number" id="edge-trim" value="1" min="0" max="5" placeholder="검정 테두리 자르기 (권장: 1~2px)">
        </div>

        <div class="form-group">
          <label>6. 배경 감도 (Threshold)</label>
          <input type="number" id="threshold" value="35" min="10" max="80">
        </div>

        <div class="form-group">
          <label>7. 초당 프레임 (FPS)</label>
          <input type="number" id="fps" value="30" min="1" max="60" placeholder="기본 30 (숫자 입력 가능)">
        </div>
      </div>

      <button type="submit" id="submit-btn">🚀 Lottie & GIF 변환 시작</button>
    </form>

    <div id="log"></div>
    <div id="lottie-preview-wrapper" style="display:none;">
      <p style="font-size:0.85rem; color:#a1a1aa; margin-top:12px;">Lottie 실시간 애니메이션 미리보기:</p>
      <div class="preview-box"><div id="lottie-container" style="width:100%; height:100%;"></div></div>
    </div>
    <div id="gif-preview-wrapper" style="display:none;">
      <p style="font-size:0.85rem; color:#a1a1aa; margin-top:12px;">투명 GIF 애니메이션 미리보기:</p>
      <div class="preview-box"><img id="gif-img" style="max-width:100%; max-height:100%;"></div>
    </div>

    <div class="btn-group" id="download-group" style="display:none;">
      <a id="dl-lottie-btn" class="download-btn" download style="display:none;">📥 Lottie JSON 다운로드</a>
      <a id="dl-gif-btn" class="download-btn gif-btn" download style="display:none;">📥 GIF 애니메이션 다운로드</a>
    </div>
  </div>

  <script>
    let anim = null;
    const form = document.getElementById('convert-form');
    const submitBtn = document.getElementById('submit-btn');
    const logBox = document.getElementById('log');
    const lottieWrapper = document.getElementById('lottie-preview-wrapper');
    const gifWrapper = document.getElementById('gif-preview-wrapper');
    const gifImg = document.getElementById('gif-img');
    const downloadGroup = document.getElementById('download-group');
    const dlLottieBtn = document.getElementById('dl-lottie-btn');
    const dlGifBtn = document.getElementById('dl-gif-btn');

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const fileInput = document.getElementById('video-file');
      if (!fileInput.files.length) return alert('동영상 파일을 선택해 주세요.');

      const file = fileInput.files[0];
      const formData = new FormData();
      formData.append('video', file);
      formData.append('format', document.getElementById('format').value);
      formData.append('fps', document.getElementById('fps').value);
      formData.append('threshold', document.getElementById('threshold').value);
      formData.append('edgeTrim', document.getElementById('edge-trim').value);
      formData.append('mode', 'image');
      formData.append('outWidth', document.getElementById('out-width').value);
      formData.append('outHeight', document.getElementById('out-height').value);

      submitBtn.disabled = true;
      submitBtn.textContent = '⏳ 변환 진행 중...';
      logBox.style.display = 'block';
      logBox.textContent = '[1/6] 파일 업로드 및 분석 중...\\n';
      lottieWrapper.style.display = 'none';
      gifWrapper.style.display = 'none';
      downloadGroup.style.display = 'none';

      try {
        const res = await fetch('/api/convert', { method: 'POST', body: formData });
        const data = await res.json();

        if (!res.ok) throw new Error(data.error || '변환 실패');

        logBox.textContent += `[2/6] 해상도: ${data.orig_w}x${data.orig_h} -> ${data.out_w}x${data.out_h} px\\n`;
        logBox.textContent += `[3/6] 배경 검출 완료: RGB(${data.bg_rgb.join(',')})\\n`;
        logBox.textContent += `[4/6] 마스크 처리 & 테두리 자르기(${data.edge_trim}px) 완료\\n[5/6] 내보내기 파일 생성 완료\\n[6/6] lottie-output 폴더 저장 완료!\\n`;

        downloadGroup.style.display = 'flex';

        if (data.lottie_json) {
          lottieWrapper.style.display = 'block';
          if (anim) anim.destroy();
          anim = lottie.loadAnimation({
            container: document.getElementById('lottie-container'),
            renderer: 'svg',
            loop: true,
            autoplay: true,
            animationData: data.lottie_json
          });

          const jsonBlob = new Blob([JSON.stringify(data.lottie_json, null, 2)], { type: 'application/json' });
          dlLottieBtn.href = URL.createObjectURL(jsonBlob);
          dlLottieBtn.download = data.json_filename;
          dlLottieBtn.style.display = 'block';
        } else {
          dlLottieBtn.style.display = 'none';
        }

        if (data.gif_b64) {
          gifWrapper.style.display = 'block';
          gifImg.src = `data:image/gif;base64,${data.gif_b64}`;
          dlGifBtn.href = `data:image/gif;base64,${data.gif_b64}`;
          dlGifBtn.download = data.gif_filename;
          dlGifBtn.style.display = 'block';
        } else {
          dlGifBtn.style.display = 'none';
        }

      } catch (err) {
        logBox.textContent += `\\n❌ 오류: ${err.message}`;
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = '🚀 Lottie & GIF 변환 시작';
      }
    });
  </script>
</body>
</html>
"""


class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode('utf-8'))
        else:
            self.send_error(404, "File not found")

    def do_POST(self):
        if self.path == '/api/convert':
            content_type = self.headers.get('Content-Type', '')
            if not content_type.startswith('multipart/form-data'):
                self.send_json_error(400, "Expected multipart/form-data")
                return

            try:
                boundary = content_type.split("boundary=")[1].encode()
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length)

                parts = body.split(b'--' + boundary)
                fields = {}
                file_bytes = None
                filename = "uploaded.mp4"

                for part in parts:
                    if not part or part == b'--\r\n':
                        continue
                    if b'\r\n\r\n' not in part:
                        continue
                    headers_part, content_part = part.split(b'\r\n\r\n', 1)
                    content_part = content_part.rsplit(b'\r\n', 1)[0]

                    msg = email.message_from_bytes(headers_part)
                    disp = msg.get('Content-Disposition', '')
                    if 'name="' in disp:
                        name = disp.split('name="')[1].split('"')[0]
                        if 'filename="' in disp:
                            filename = disp.split('filename="')[1].split('"')[0]
                            file_bytes = content_part
                        else:
                            fields[name] = content_part.decode('utf-8')

                if not file_bytes:
                    self.send_json_error(400, "No video file provided.")
                    return

                os.makedirs(config.INPUT_DIR, exist_ok=True)
                temp_input_path = os.path.join(config.INPUT_DIR, f"web_upload_{filename}")
                with open(temp_input_path, "wb") as f:
                    f.write(file_bytes)

                fps = float(fields.get('fps', 15))
                threshold = float(fields.get('threshold', 35))
                edge_trim = int(fields.get('edgeTrim', 1))
                mode = fields.get('mode', 'image')
                fmt = fields.get('format', 'both')
                out_w_str = fields.get('outWidth', '').strip()
                out_h_str = fields.get('outHeight', '').strip()

                target_w = int(out_w_str) if out_w_str.isdigit() else None
                target_h = int(out_h_str) if out_h_str.isdigit() else None

                reader = VideoReader(temp_input_path)
                video_info = reader.get_info()

                out_w, out_h = FrameProcessor.compute_target_dimensions(
                    video_info["width"], video_info["height"], target_w, target_h
                )

                detector = BackgroundDetector()
                bg_color, is_consistent = detector.validate_multi_frame_background(reader)

                remover = BackgroundRemover(threshold=threshold, edge_trim=edge_trim)

                sampled_rgba_frames = []
                all_frame_contours = []

                for f_idx, ts, frame in reader.extract_sampled_frames(target_fps=fps):
                    rgba = remover.extract_rgba_foreground(frame, bg_color, threshold=threshold, soft=True, edge_trim=edge_trim)
                    sampled_rgba_frames.append(rgba)
                    if mode == "vector" and fmt in ["lottie", "both"]:
                        mask = remover.process_frame(frame, bg_color, threshold=threshold, edge_trim=edge_trim)
                        extractor = ContourExtractor()
                        contours = extractor.extract_and_simplify(mask)
                        all_frame_contours.append(contours)

                reader.release()

                base_name = os.path.splitext(filename)[0]
                output_dir = os.path.abspath(config.OUTPUT_DIR)
                os.makedirs(output_dir, exist_ok=True)

                lottie_dict = None
                json_name = None
                gif_b64 = None
                gif_name = None

                if fmt in ["gif", "both"]:
                    gif_name = f"{base_name}.gif"
                    gif_path = os.path.join(output_dir, gif_name)
                    GifWriter.save_gif(sampled_rgba_frames, gif_path, fps=fps, target_width=out_w, target_height=out_h)
                    with open(gif_path, "rb") as gf:
                        gif_b64 = base64.b64encode(gf.read()).decode('ascii')

                if fmt in ["lottie", "both"]:
                    json_name = f"{base_name}.json"
                    json_path = os.path.join(output_dir, json_name)
                    writer = LottieWriter(width=out_w, height=out_h, fps=fps)
                    if mode == "image":
                        lottie_dict = writer.create_image_lottie_dict(sampled_rgba_frames)
                    else:
                        converter = LottiePathConverter(scale_x=out_w / video_info["width"], scale_y=out_h / video_info["height"])
                        lottie_dict = writer.create_lottie_dict(all_frame_contours, converter)
                    writer.save_lottie_json(lottie_dict, json_path)

                response_data = {
                    "success": True,
                    "json_filename": json_name,
                    "gif_filename": gif_name,
                    "gif_b64": gif_b64,
                    "orig_w": video_info["width"],
                    "orig_h": video_info["height"],
                    "out_w": out_w,
                    "out_h": out_h,
                    "edge_trim": edge_trim,
                    "bg_rgb": bg_color["rgb"].tolist(),
                    "lottie_json": lottie_dict
                }

                self.send_response(200)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode('utf-8'))

            except Exception as e:
                self.send_json_error(500, str(e))

    def send_json_error(self, code, message):
        self.send_response(code)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps({"error": message}, ensure_ascii=False).encode('utf-8'))


def main():
    server = HTTPServer(('localhost', PORT), RequestHandler)
    print(f"==================================================")
    print(f" Lottie & GIF Converter Web GUI Server Started!")
    print(f" Open in Browser: http://localhost:{PORT}")
    print(f" Output Folder: {os.path.abspath(config.OUTPUT_DIR)}")
    print(f"==================================================")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nWeb GUI Server stopped.")


if __name__ == "__main__":
    main()
