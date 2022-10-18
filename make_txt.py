import os, random

def make_list_txt():
    temp = []
    label_dir = './jyb/220920/ok'
    label_list = os.listdir(label_dir)
    label_list = [file for file in label_list if file.endswith(".jpg")]       # .jpg만 남김
    label_list = [file for file in label_list if not file.startswith("._")]   # Dump data 삭제
    print(label_list)

    for i in label_list:
        temp_list = i.split(".")
        temp.append(temp_list[-2])

    temp_set = set(temp)
    result = list(temp_set) #폴더 내 파일이름(확장자x)만 남게됨

    n = int(len(result)*0.8)

    basic_dir = os.path.abspath(label_dir)

    with open('Train.txt', 'w') as f:
        for i in result[:n]:
            data = "{}/{}.jpg\n".format(basic_dir, i)
            #print("Train : {}".format(data))
            f.write(data)

    with open('Valid.txt', 'w') as f:
        for i in result[n:]:
            data = "{}/{}.jpg\n".format(basic_dir, i)
            #print("Valid : {}".format(data))
            f.write(data)

if __name__ == "__main__":
    make_list_txt()
