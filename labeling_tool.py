import os
from collections import Counter

def change_label_all(dir, label_before, label_after): # 라벨 일괄 변경
    LABEL_DIR = dir
    OLD_CLASS = str(label_before)
    NEW_CLASS = str(label_after)
  
    for filename in os.listdir(LABEL_DIR):
        if not filename.endswith(".txt"):
            continue

        file_path = os.path.join(LABEL_DIR, filename)

        with open(file_path, "r") as f:
            lines = f.readlines()

        new_lines = []
        for line in lines:
            line = line.strip()
            if not line:
                continue

            parts = line.split()
            if parts[0] == OLD_CLASS:
                parts[0] = NEW_CLASS

            new_lines.append(" ".join(parts))

        if new_lines:
            f.write("\n".join(new_lines) + "\n")
        else:
            f.write("")with open(file_path, "w") as f:
                f.write("\n".join(new_lines) + "\n")

    print("✅ 모든 라벨 수정 완료")

def label_checker(dir): # 라벨 분포도 확인
    LABEL_DIR = dir
    class_counter = Counter()

    for filename in os.listdir(LABEL_DIR):
        if not filename.endswith(".txt"):
            continue

        file_path = os.path.join(LABEL_DIR, filename)

        with open(file_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                class_id = line.split()[0]
                class_counter[class_id] += 1

    print("📊 클래스 분포:")
    for cls, count in class_counter.items():
        print(f"  class {cls}: {count}개")

    if not class_counter:
        return None

    minority_class = min(class_counter, key=class_counter.get)
    print(f"\n⚠️ 이상(소수) 클래스: class {minority_class}")

    return minority_class

def label_checker_minor(dir): # 이상 클래스 탐지
    minority_class = label_checker(dir)
    if minority_class is None:
        print("⚠️ 라벨이 없습니다.")
        return
      
    LABEL_DIR = dir
    minority_files = []

    for filename in os.listdir(LABEL_DIR):
        if not filename.endswith(".txt"):
            continue

        file_path = os.path.join(LABEL_DIR, filename)

        with open(file_path, "r") as f:
            for line in f:
                if not line.strip():
                    continue

                class_id = line.split()[0]
                if class_id == minority_class:
                    minority_files.append(filename)
                    break

    print("\n🗂️ 이상 클래스가 포함된 파일:")
    for f in minority_files:
        print(" ", f)


if __name__ == "__main__":
    LABEL_DIR = r"./labels"  # 라벨 폴더 경로로 수정
  
    while True:
        print(f"\n📂 현재 선택된 라벨 경로:")
        print(f"   {os.path.abspath(label_dir)}")
        print("\n====== YOLO Label Tool ======")
        print("1. 라벨 분포 확인")
        print("2. 이상(소수) 클래스 탐지")
        print("3. 라벨 일괄 변경")
        print("0. 종료")

        choice = input("👉 번호를 선택하세요: ").strip()

        if choice == "1":
            label_checker(label_dir)

        elif choice == "2":
            label_checker_minor(label_dir)

        elif choice == "3":
            before = input("변경할 class_id (예: 2): ").strip()
            after = input("변경 후 class_id (예: 1): ").strip()
            change_label_all(label_dir, before, after)

        elif choice == "0":
            print("👋 프로그램을 종료합니다.")
            break

        else:
            print("⚠️ 올바른 번호를 선택하세요.")
    
