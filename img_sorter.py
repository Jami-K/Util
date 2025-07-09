import os
import shutil
from tkinter import Tk, Button, Label, Frame, PhotoImage, filedialog, StringVar, Radiobutton
from tkinter import font as tkFont
from PIL import Image, ImageTk

# 폴더 내 이미지를 분류하는 프로그램입니다.

class ImageClassifier:
    def __init__(self, root):
        self.root = root
        self.root.title("이미지 분류기 (Space : 폴더 이동)")

        self.image_paths = []
        self.current_index = 0
        self.selected_folder = ""
        self.history = []  # (file_path, moved_to)

        self.status = StringVar(value="OK")  # 기본 선택값
        self.custom_font = tkFont.Font(family="NanumGothic", size=12)

        # 경로 선택 버튼
        self.select_button = Button(root, text="이미지 폴더 선택", command=self.select_folder, font=self.custom_font)
        self.select_button.pack()

        # 이미지 라벨
        self.image_label = Label(root, font=self.custom_font)
        self.image_label.pack()
        
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
        self.root.bind("Q", lambda e: self.root.destroy())

    def select_folder(self):
        self.selected_folder = filedialog.askdirectory()
        if not self.selected_folder:
            return

        self.image_paths = [
            os.path.join(self.selected_folder, f)
            for f in os.listdir(self.selected_folder)
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif"))
        ]
        self.current_index = 0
        self.history = []

        os.makedirs(os.path.join(self.selected_folder, "OK"), exist_ok=True)
        os.makedirs(os.path.join(self.selected_folder, "NG"), exist_ok=True)

        self.load_image()

    def load_image(self):
        if self.current_index >= len(self.image_paths):
            self.image_label.config(text="모든 이미지 분류 완료!")
            self.progress_label.config(text="")
            return

        image_path = self.image_paths[self.current_index]
        img = Image.open(image_path)
        img.thumbnail((1000, 1000)) # 이미지 크기 확대
        self.tk_img = ImageTk.PhotoImage(img)

        self.image_label.config(image=self.tk_img)
        self.progress_label.config(text=f"{self.current_index + 1} / {len(self.image_paths)}")

    def classify_image(self, event=None):
        if self.current_index >= len(self.image_paths):
            return

        current_image = self.image_paths[self.current_index]
        target_dir = os.path.join(self.selected_folder, self.status.get())
        moved_path = os.path.join(target_dir, os.path.basename(current_image))

        shutil.move(current_image, moved_path)
        self.history.append((moved_path, self.current_index))
        self.current_index += 1
        self.load_image()

    def undo_last(self):
        if not self.history:
            return

        last_moved_path, prev_index = self.history.pop()
        original_path = os.path.join(self.selected_folder, os.path.basename(last_moved_path))
        shutil.move(last_moved_path, original_path)

        # 리스트에 다시 추가하고 인덱스 조정
        self.image_paths.insert(prev_index, original_path)
        self.current_index = prev_index
        self.load_image()

if __name__ == "__main__":
    root = Tk()
    window_width, window_height = 600, 700
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width // 2) - (window_width // 2)
    y = (screen_height // 2) - (window_height // 2)
    root.geometry(f"{window_width}x{window_height}+{x}+{y}")
    app = ImageClassifier(root)
    root.mainloop()
