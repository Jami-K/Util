import os
import shutil
from tkinter import Tk, Button, Label, Frame, filedialog, StringVar, Radiobutton
from tkinter import font as tkFont
from PIL import Image, ImageTk, ImageDraw, ImageFont

# 폴더 내 이미지를 분류하는 프로그램입니다.

class ImageClassifier:
    def __init__(self, root):
        self.root = root
        self.root.title("이미지 분류기 (Space: 이미지 이동 / 화살표: 유형 변경 / p: 통과 / z: 실행취소)")

        self.image_paths = []
        self.current_index = 0
        self.selected_folder = ""
        # history item: dict(original_img, moved_img, original_txt, moved_txt, prev_index)
        self.history = []

        self.status = StringVar(value="OK")  # 기본 선택값
        self.custom_font = tkFont.Font(family="NanumGothic", size=16)

        # 경로 선택 버튼
        self.select_button = Button(root, text="이미지 폴더 선택", command=self.select_folder, font=self.custom_font)
        self.select_button.pack()

        # 이미지 라벨
        self.image_label = Label(root, font=self.custom_font)
        self.image_label.pack()

        # 라벨 텍스트(라벨 파일 상태 등) 표시용
        self.label_info = Label(root, text="", font=self.custom_font)
        self.label_info.pack()

        # 라디오 버튼을 가로로 정렬할 프레임 생성
        self.radio_frame = Frame(root)
        self.radio_frame.pack()

        # 라디오 버튼 (OK / NG) - 한 줄에 표시
        self.ok_radio = Radiobutton(self.radio_frame, text="OK (←)", variable=self.status, value="OK", font=self.custom_font)
        self.ng_radio = Radiobutton(self.radio_frame, text="NG (→)", variable=self.status, value="NG", font=self.custom_font)
        self.ok_radio.pack(in_=self.radio_frame, side="left", padx=50)
        self.ng_radio.pack(in_=self.radio_frame, side="left", padx=50)

        # 되돌리기 버튼
        self.undo_button = Button(root, text="되돌리기", command=self.undo_last, font=self.custom_font)
        self.undo_button.pack()

        # 진행률 라벨
        self.progress_label = Label(root, text="")
        self.progress_label.pack()

        # 키보드 바인딩
        self.root.bind("<space>", self.classify_image)
        self.root.bind("<Left>", lambda e: self.status.set("OK"))
        self.root.bind("<Right>", lambda e: self.status.set("NG"))
        self.root.bind("q", lambda e: self.root.destroy())
        self.root.bind("p", lambda e: self.skip_image())
        self.root.bind("z", lambda e: self.undo_last())

        # PIL에서 글꼴(라벨 텍스트) 표시용: 실패하면 기본 폰트 사용
        self.pil_font = None
        try:
            # 시스템에 따라 경로가 다를 수 있어서, 없으면 기본 폰트로 fallback
            self.pil_font = ImageFont.truetype("NanumGothic.ttf", 24)
        except Exception:
            self.pil_font = ImageFont.load_default()

        # 라벨 표시 on/off (원하면 나중에 토글 키 추가 가능)
        self.show_labels = True

    def select_folder(self):
        self.selected_folder = filedialog.askdirectory()
        if not self.selected_folder:
            return

        self.image_paths = [
            os.path.join(self.selected_folder, f)
            for f in os.listdir(self.selected_folder)
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif"))
        ]
        self.image_paths.sort()
        self.current_index = 0
        self.history = []

        os.makedirs(os.path.join(self.selected_folder, "OK"), exist_ok=True)
        os.makedirs(os.path.join(self.selected_folder, "NG"), exist_ok=True)

        self.load_image()

    def _get_label_path(self, image_path: str) -> str:
        base, _ = os.path.splitext(image_path)
        return base + ".txt"

    def _parse_yolo_labels(self, txt_path: str):
        """
        YOLO txt format: class x_center y_center width height  (normalized 0~1)
        return list of tuples: (cls, xc, yc, w, h)
        """
        labels = []
        try:
            with open(txt_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split()
                    if len(parts) < 5:
                        continue
                    cls = parts[0]
                    vals = parts[1:5]
                    try:
                        xc, yc, w, h = map(float, vals)
                        labels.append((cls, xc, yc, w, h))
                    except ValueError:
                        continue
        except Exception:
            # 파일 읽기 실패 시 그냥 라벨 없는 것으로 처리
            return []
        return labels

    def _draw_labels(self, img: Image.Image, labels):
        """
        img: already resized image (display size)
        labels: list of (cls, xc, yc, w, h) in normalized coords (default)
        """
        if not labels:
            return img

        draw = ImageDraw.Draw(img)
        W, H = img.size

        # 휴리스틱: 값이 1보다 크면 "픽셀좌표"일 가능성도 있으니 대응
        # (완벽히 보장하진 않지만, 오류로 망가지기보다는 안전하게)
        normalized = True
        for (_, xc, yc, w, h) in labels:
            if xc > 1.5 or yc > 1.5 or w > 1.5 or h > 1.5:
                normalized = False
                break

        for (cls, xc, yc, w, h) in labels:
            if normalized:
                x1 = (xc - w / 2) * W
                y1 = (yc - h / 2) * H
                x2 = (xc + w / 2) * W
                y2 = (yc + h / 2) * H
            else:
                # 픽셀 좌표로 들어왔다고 가정
                x1 = xc - w / 2
                y1 = yc - h / 2
                x2 = xc + w / 2
                y2 = yc + h / 2

            # 경계 보정
            x1 = max(0, min(W - 1, x1))
            y1 = max(0, min(H - 1, y1))
            x2 = max(0, min(W - 1, x2))
            y2 = max(0, min(H - 1, y2))

            # 박스
            draw.rectangle([x1, y1, x2, y2], outline="red", width=3)

            # 텍스트 배경 + 텍스트
            text = str(cls)
            # 텍스트 크기 측정(버전에 따라 textbbox가 없는 경우도 있어 fallback)
            try:
                bbox = draw.textbbox((0, 0), text, font=self.pil_font)
                tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            except Exception:
                tw, th = draw.textsize(text, font=self.pil_font)

            tx1, ty1 = x1, max(0, y1 - th - 6)
            tx2, ty2 = x1 + tw + 10, ty1 + th + 6
            draw.rectangle([tx1, ty1, tx2, ty2], fill="red")
            draw.text((tx1 + 5, ty1 + 3), text, fill="white", font=self.pil_font)

        return img

    def load_image(self):
        if self.current_index >= len(self.image_paths):
            self.image_label.config(image="", text="모든 이미지 분류 완료!", font=self.custom_font)
            self.label_info.config(text="")
            self.progress_label.config(text="작업이 완료되었습니다.")
            return

        image_path = self.image_paths[self.current_index]

        # 이미지 로드
        img = Image.open(image_path).convert("RGB")

        # 화면에 맞게 축소(비율 유지)
        # (원 코드의 resize + thumbnail 조합은 왜곡/의도불명이라 안정적으로 변경)
        max_w, max_h = 1600, 900
        img.thumbnail((max_w, max_h), Image.LANCZOS)

        # 라벨 파일 확인 및 그리기
        txt_path = self._get_label_path(image_path)
        labels = []
        if self.show_labels and os.path.exists(txt_path):
            labels = self._parse_yolo_labels(txt_path)
            img = self._draw_labels(img, labels)
            self.label_info.config(text=f"라벨: {os.path.basename(txt_path)} / {len(labels)}개")
        else:
            # 라벨 파일 없을 수 있으니 안전 처리
            self.label_info.config(text="라벨: (없음)")

        self.tk_img = ImageTk.PhotoImage(img)
        self.image_label.config(image=self.tk_img, text="")
        self.progress_label.config(text=f"{self.current_index + 1} / {len(self.image_paths)}")

    def classify_image(self, event=None):
        if self.current_index >= len(self.image_paths):
            return

        current_image = self.image_paths[self.current_index]
        target_dir = os.path.join(self.selected_folder, self.status.get())
        moved_img_path = os.path.join(target_dir, os.path.basename(current_image))

        # txt도 같이 이동(없으면 None)
        original_txt = self._get_label_path(current_image)
        moved_txt_path = None

        # 먼저 이미지 이동
        shutil.move(current_image, moved_img_path)

        # 라벨 파일이 존재하면 같이 이동
        if os.path.exists(original_txt):
            moved_txt_path = os.path.join(target_dir, os.path.basename(original_txt))
            try:
                shutil.move(original_txt, moved_txt_path)
            except Exception:
                moved_txt_path = None

        # 히스토리 저장(undo를 위해 원본/이동 경로 모두 저장)
        self.history.append({
            "original_img": current_image,
            "moved_img": moved_img_path,
            "original_txt": original_txt if os.path.exists(original_txt) or moved_txt_path else None,
            "moved_txt": moved_txt_path,
            "prev_index": self.current_index
        })

        self.current_index += 1
        self.load_image()

    def skip_image(self):
        if self.current_index < len(self.image_paths):
            self.current_index += 1
            self.load_image()

    def undo_last(self):
        if not self.history:
            return

        item = self.history.pop()

        # 이미지 원위치
        moved_img = item["moved_img"]
        original_img = item["original_img"]
        if os.path.exists(moved_img):
            shutil.move(moved_img, original_img)

        # txt 원위치(있을 때만)
        moved_txt = item["moved_txt"]
        original_txt = item["original_txt"]
        if moved_txt and original_txt and os.path.exists(moved_txt):
            try:
                shutil.move(moved_txt, original_txt)
            except Exception:
                pass

        # 인덱스 복구 + 리스트 경로 복구
        prev_index = item["prev_index"]
        # current_index는 "되돌린 이미지가 다시 현재"가 되어야 함
        self.current_index = prev_index

        # image_paths에는 원래 경로가 남아있을 수도/없을 수도 있으니 안전하게 보정
        # (이동한 이미지는 원래 경로가 깨졌기 때문에, 되돌린 뒤 원래 경로를 보장)
        if prev_index < len(self.image_paths):
            self.image_paths[prev_index] = original_img
        else:
            self.image_paths.append(original_img)

        self.load_image()


if __name__ == "__main__":
    root = Tk()
    window_width, window_height = 1920, 1080
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width // 2) - (window_width // 2)
    y = (screen_height // 2) - (window_height // 2)
    root.geometry(f"{window_width}x{window_height}+{x}+{y}")
    app = ImageClassifier(root)
    root.mainloop()
