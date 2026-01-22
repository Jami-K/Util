import os
import shutil
from tkinter import Tk, Button, Label, Frame, filedialog, StringVar, Radiobutton, Toplevel, Checkbutton
from tkinter import font as tkFont
from tkinter import simpledialog, messagebox
from PIL import Image, ImageTk, ImageDraw, ImageFont


IMG_EXTS = (".png", ".jpg", ".jpeg", ".bmp", ".gif")


def yolo_txt_path(image_path: str) -> str:
    base, _ = os.path.splitext(image_path)
    return base + ".txt"


def parse_yolo_txt(txt_path: str):
    """
    YOLO format: class x_center y_center width height (normalized 0~1)
    return: list[(cls:str, xc, yc, w, h)]
    """
    if not os.path.exists(txt_path):
        return []
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
                try:
                    xc, yc, w, h = map(float, parts[1:5])
                except ValueError:
                    continue
                labels.append((cls, xc, yc, w, h))
    except Exception:
        return []
    return labels


def save_yolo_txt(txt_path: str, labels):
    """
    labels: list[(cls:str, xc, yc, w, h)]
    - labels가 비어있으면 txt 삭제(있다면)
    """
    if not labels:
        if os.path.exists(txt_path):
            try:
                os.remove(txt_path)
            except Exception:
                pass
        return

    tmp_path = txt_path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        for cls, xc, yc, w, h in labels:
            f.write(f"{cls} {xc:.6f} {yc:.6f} {w:.6f} {h:.6f}\n")
    os.replace(tmp_path, txt_path)


class LabelEditorPopup:
    """
    팝업 라벨 편집기
    - 드래그: 새 박스 추가
    - 클릭: 박스 선택
    - BackSpace: 선택 박스 삭제
    - e: 선택 박스 클래스 수정
    - 확인: 저장 후 닫기 / 취소: 닫기(저장 안 함)
    """
    def __init__(self, parent, image_path: str, on_close_saved=None):
        self.parent = parent
        self.image_path = image_path
        self.txt_path = yolo_txt_path(image_path)
        self.on_close_saved = on_close_saved

        self.top = Toplevel(parent)
        self.top.title(f"라벨 편집 - {os.path.basename(image_path)}")
        self.top.geometry("1500x950")
        self.top.transient(parent)
        self.top.grab_set()  # 모달처럼

        # 상단 버튼
        header = Frame(self.top)
        header.pack(fill="x", padx=8, pady=8)

        Button(header, text="확인(저장)", command=self.save_and_close, width=12).pack(side="left", padx=6)
        Button(header, text="취소", command=self.close, width=8).pack(side="left", padx=6)
        Button(header, text="선택 삭제(BackSpace)", command=self.delete_selected, width=18).pack(side="left", padx=6)
        Button(header, text="클래스 수정(e)", command=self.edit_selected_class, width=12).pack(side="left", padx=6)

        self.info_var = StringVar(value="")
        Label(header, textvariable=self.info_var).pack(side="left", padx=12)

        # 캔버스
        from tkinter import Canvas
        self.canvas = Canvas(self.top, width=1450, height=860, bg="black")
        self.canvas.pack(padx=8, pady=8)

        # 폰트
        try:
            self.pil_font = ImageFont.truetype("NanumGothic.ttf", 20)
        except Exception:
            self.pil_font = ImageFont.load_default()

        # 이미지/스케일
        self.pil_orig = Image.open(image_path).convert("RGB")
        self.disp_img = None
        self.tk_img = None
        self.disp_w = 0
        self.disp_h = 0

        # labels: list[(cls, xc, yc, w, h)] normalized
        self.labels = parse_yolo_txt(self.txt_path)

        # 선택/드래그 상태
        self.selected_idx = None
        self.drag_start = None
        self.temp_rect_id = None

        # 이벤트
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_move)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        self.canvas.bind("<ButtonPress-3>", self.on_right_click_select)  # 우클릭 선택도 가능

        self.top.bind("<BackSpace>", lambda e: self.delete_selected())
        self.top.bind("e", lambda e: self.edit_selected_class())
        self.top.bind("<Escape>", lambda e: self.cancel_temp())

        self.top.after(50, self.render)

    def render(self):
        # 캔버스 크기에 맞춰 이미지 표시
        cw = max(self.canvas.winfo_width(), 1450)
        ch = max(self.canvas.winfo_height(), 860)

        img = self.pil_orig.copy()
        img.thumbnail((cw, ch), Image.LANCZOS)

        self.disp_img = img
        self.disp_w, self.disp_h = img.size

        self.tk_img = ImageTk.PhotoImage(img)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img, tags=("img",))

        self.draw_boxes()
        self.update_info()

    def update_info(self):
        base = os.path.basename(self.image_path)
        self.info_var.set(f"{base} | labels: {len(self.labels)} | txt: {'있음' if os.path.exists(self.txt_path) else '없음'}")

    def yolo_to_canvas(self, xc, yc, w, h):
        x1 = (xc - w / 2) * self.disp_w
        y1 = (yc - h / 2) * self.disp_h
        x2 = (xc + w / 2) * self.disp_w
        y2 = (yc + h / 2) * self.disp_h
        return x1, y1, x2, y2

    def canvas_to_yolo(self, x1, y1, x2, y2):
        x1, x2 = sorted([x1, x2])
        y1, y2 = sorted([y1, y2])

        # clamp to image area
        x1 = max(0, min(self.disp_w, x1))
        x2 = max(0, min(self.disp_w, x2))
        y1 = max(0, min(self.disp_h, y1))
        y2 = max(0, min(self.disp_h, y2))

        bw = max(1.0, x2 - x1)
        bh = max(1.0, y2 - y1)

        xc = (x1 + x2) / 2 / self.disp_w
        yc = (y1 + y2) / 2 / self.disp_h
        w = bw / self.disp_w
        h = bh / self.disp_h
        return xc, yc, w, h

    def draw_boxes(self):
        self.canvas.delete("box")
        for i, (cls, xc, yc, w, h) in enumerate(self.labels):
            x1, y1, x2, y2 = self.yolo_to_canvas(xc, yc, w, h)
            outline = "yellow" if i == self.selected_idx else "red"
            width = 3 if i == self.selected_idx else 2

            rect_id = self.canvas.create_rectangle(x1, y1, x2, y2, outline=outline, width=width, tags=("box", f"box_{i}"))
            self.canvas.tag_bind(rect_id, "<ButtonPress-1>", lambda e, idx=i: self.select_box(idx))

            # 클래스 텍스트
            text_id = self.canvas.create_text(x1 + 4, max(10, y1 + 10), anchor="nw", fill="white",
                                              text=str(cls), tags=("box", f"box_{i}"))
            self.canvas.tag_bind(text_id, "<ButtonPress-1>", lambda e, idx=i: self.select_box(idx))

    def select_box(self, idx):
        self.selected_idx = idx
        self.draw_boxes()

    def find_box_at(self, x, y):
        # 클릭 위치가 어떤 박스 안인지 찾기(뒤에서부터: 마지막이 위에)
        for i in range(len(self.labels) - 1, -1, -1):
            cls, xc, yc, w, h = self.labels[i]
            x1, y1, x2, y2 = self.yolo_to_canvas(xc, yc, w, h)
            if x1 <= x <= x2 and y1 <= y <= y2:
                return i
        return None

    def on_right_click_select(self, event):
        if event.x < 0 or event.y < 0 or event.x > self.disp_w or event.y > self.disp_h:
            return
        idx = self.find_box_at(event.x, event.y)
        if idx is not None:
            self.select_box(idx)

    def on_mouse_down(self, event):
        if event.x < 0 or event.y < 0 or event.x > self.disp_w or event.y > self.disp_h:
            return

        # 이미 박스 위면 선택만 하고, 드래그 생성은 "빈 곳"에서만 시작하도록
        hit = self.find_box_at(event.x, event.y)
        if hit is not None:
            self.select_box(hit)
            self.drag_start = None
            return

        self.selected_idx = None
        self.draw_boxes()

        self.drag_start = (event.x, event.y)
        self.temp_rect_id = self.canvas.create_rectangle(event.x, event.y, event.x, event.y,
                                                         outline="cyan", width=2, tags=("temp",))

    def on_mouse_move(self, event):
        if not self.drag_start or not self.temp_rect_id:
            return
        x0, y0 = self.drag_start
        x1 = max(0, min(self.disp_w, event.x))
        y1 = max(0, min(self.disp_h, event.y))
        self.canvas.coords(self.temp_rect_id, x0, y0, x1, y1)

    def on_mouse_up(self, event):
        if not self.drag_start or not self.temp_rect_id:
            return

        x0, y0 = self.drag_start
        x1 = max(0, min(self.disp_w, event.x))
        y1 = max(0, min(self.disp_h, event.y))

        # 작은 박스 무시
        if abs(x1 - x0) < 5 or abs(y1 - y0) < 5:
            self.cancel_temp()
            return

        cls = simpledialog.askstring("클래스", "클래스 ID(또는 이름)를 입력:", parent=self.top)
        if cls is None or str(cls).strip() == "":
            self.cancel_temp()
            return
        cls = str(cls).strip()

        xc, yc, w, h = self.canvas_to_yolo(x0, y0, x1, y1)
        self.labels.append((cls, xc, yc, w, h))
        self.selected_idx = len(self.labels) - 1

        self.cancel_temp()
        self.draw_boxes()
        self.update_info()

    def cancel_temp(self):
        self.drag_start = None
        if self.temp_rect_id:
            self.canvas.delete(self.temp_rect_id)
        self.temp_rect_id = None

    def delete_selected(self):
        if self.selected_idx is None:
            return
        if 0 <= self.selected_idx < len(self.labels):
            self.labels.pop(self.selected_idx)
        self.selected_idx = None
        self.draw_boxes()
        self.update_info()

    def edit_selected_class(self):
        if self.selected_idx is None:
            return
        cls, xc, yc, w, h = self.labels[self.selected_idx]
        new_cls = simpledialog.askstring("클래스 수정", f"현재: {cls}\n새 클래스:", parent=self.top)
        if new_cls is None or str(new_cls).strip() == "":
            return
        new_cls = str(new_cls).strip()
        self.labels[self.selected_idx] = (new_cls, xc, yc, w, h)
        self.draw_boxes()

    def save_and_close(self):
        try:
            save_yolo_txt(self.txt_path, self.labels)
        except Exception as e:
            messagebox.showerror("저장 실패", str(e))
            return

        if callable(self.on_close_saved):
            self.on_close_saved()
        self.close()

    def close(self):
        try:
            self.top.grab_release()
        except Exception:
            pass
        self.top.destroy()


class ImageClassifier:
    def __init__(self, root):
        self.root = root
        self.root.title("이미지 분류기 (Space: 이미지 이동 / 화살표: 유형 변경 / p: 통과 / z: 실행취소)")

        self.image_paths = []
        self.current_index = 0
        self.selected_folder = ""

        # history: dict(original_img, moved_img, original_txt, moved_txt, prev_index)
        self.history = []

        self.status = StringVar(value="OK")
        self.custom_font = tkFont.Font(family="NanumGothic", size=16)

        # 폰트 (라벨 텍스트용)
        try:
            self.pil_font = ImageFont.truetype("NanumGothic.ttf", 24)
        except Exception:
            self.pil_font = ImageFont.load_default()

        # 경로 선택 버튼
        self.select_button = Button(root, text="이미지 폴더 선택", command=self.select_folder, font=self.custom_font)
        self.select_button.pack()

        # 라벨 편집 버튼
        self.edit_label_button = Button(root, text="라벨 편집(팝업)", command=self.open_label_editor, font=self.custom_font)
        self.edit_label_button.pack()

        # 이미지 라벨
        self.image_label = Label(root, font=self.custom_font)
        self.image_label.pack()

        # 라벨 상태 표시
        self.label_info = Label(root, text="", font=self.custom_font)
        self.label_info.pack()

        # 라디오 버튼 프레임
        self.radio_frame = Frame(root)
        self.radio_frame.pack()
        
        # 라벨 오버레이 토글
        self.show_labels = StringVar(value="ON")  # 간단히 문자열로 (ON/OFF)
        self.toggle_button = Button(root,
                                    text="라벨 표시: ON (l)",
                                    command=self.toggle_labels,
                                    font=self.custom_font)
        self.toggle_button.pack()

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
        self.root.bind("e", lambda e: self.open_label_editor())  # 단축키로도 편집
        self.root.bind("l", lambda e: self.toggle_labels()) # 라벨 토글 단축키

    def select_folder(self):
        self.selected_folder = filedialog.askdirectory()
        if not self.selected_folder:
            return

        self.image_paths = sorted([
            os.path.join(self.selected_folder, f)
            for f in os.listdir(self.selected_folder)
            if f.lower().endswith(IMG_EXTS)
        ])
        self.current_index = 0
        self.history = []

        os.makedirs(os.path.join(self.selected_folder, "OK"), exist_ok=True)
        os.makedirs(os.path.join(self.selected_folder, "NG"), exist_ok=True)

        self.load_image()

    def _draw_labels_on_image(self, img: Image.Image, labels):
        if not labels:
            return img
        draw = ImageDraw.Draw(img)
        W, H = img.size

        for (cls, xc, yc, w, h) in labels:
            x1 = (xc - w / 2) * W
            y1 = (yc - h / 2) * H
            x2 = (xc + w / 2) * W
            y2 = (yc + h / 2) * H

            x1 = max(0, min(W - 1, x1))
            y1 = max(0, min(H - 1, y1))
            x2 = max(0, min(W - 1, x2))
            y2 = max(0, min(H - 1, y2))

            draw.rectangle([x1, y1, x2, y2], outline="red", width=1)

            text = str(cls)
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

        try:
            img = Image.open(image_path).convert("RGB")
            img = img.resize((1280, 1024))
        except Exception as e:
            self.label_info.config(text=f"이미지 로드 실패: {os.path.basename(image_path)} ({e})")
            self.current_index += 1
            self.load_image()
            return

        img.thumbnail((1000, 1000), Image.LANCZOS)

        # 라벨 오버레이 표시(토글 반영)
        txt_path = yolo_txt_path(image_path)
        labels = parse_yolo_txt(txt_path) if os.path.exists(txt_path) else []

        if labels and self.show_labels.get() == "ON":
            img = self._draw_labels_on_image(img, labels)
            self.label_info.config(text=f"라벨: {os.path.basename(txt_path)} / {len(labels)}개 (표시 ON)")
        else:
            if labels:
                self.label_info.config(text=f"라벨: {os.path.basename(txt_path)} / {len(labels)}개 (표시 OFF)")
            else:
                self.label_info.config(text="라벨: (없음)")

        self.tk_img = ImageTk.PhotoImage(img)
        self.image_label.config(image=self.tk_img, text="")
        self.progress_label.config(text=f"{self.current_index + 1} / {len(self.image_paths)}")

    def open_label_editor(self):
        if self.current_index >= len(self.image_paths):
            return
        image_path = self.image_paths[self.current_index]

        # 팝업 닫고 저장되면 분류기 화면 라벨 표시도 갱신
        LabelEditorPopup(self.root, image_path, on_close_saved=self.load_image)

    def classify_image(self, event=None):
        if self.current_index >= len(self.image_paths):
            return

        current_image = self.image_paths[self.current_index]
        target_dir = os.path.join(self.selected_folder, self.status.get())
        moved_img_path = os.path.join(target_dir, os.path.basename(current_image))

        original_txt = yolo_txt_path(current_image)
        moved_txt_path = None

        shutil.move(current_image, moved_img_path)

        if os.path.exists(original_txt):
            moved_txt_path = os.path.join(target_dir, os.path.basename(original_txt))
            try:
                shutil.move(original_txt, moved_txt_path)
            except Exception:
                moved_txt_path = None

        self.history.append({
            "original_img": current_image,
            "moved_img": moved_img_path,
            "original_txt": original_txt if moved_txt_path else (original_txt if os.path.exists(original_txt) else None),
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
        moved_img = item["moved_img"]
        original_img = item["original_img"]

        if os.path.exists(moved_img):
            shutil.move(moved_img, original_img)

        moved_txt = item["moved_txt"]
        original_txt = item["original_txt"]
        if moved_txt and original_txt and os.path.exists(moved_txt):
            try:
                shutil.move(moved_txt, original_txt)
            except Exception:
                pass

        self.current_index = item["prev_index"]
        if self.current_index < len(self.image_paths):
            self.image_paths[self.current_index] = original_img
        else:
            self.image_paths.append(original_img)

        self.load_image()

    def toggle_labels(self):
        # ON <-> OFF
        if self.show_labels.get() == "ON":
            self.show_labels.set("OFF")
            self.toggle_button.config(text="라벨 표시: OFF (l)")
        else:
            self.show_labels.set("ON")
            self.toggle_button.config(text="라벨 표시: ON (l)")
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
