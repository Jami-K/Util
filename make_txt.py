import os, random

def make_list_txt():
    temp = []
    label_dir = './temp'
    label_list = os.listdir(label_dir)

    for i in label_list:
        temp_list = i.split(".")
        temp.append(temp_list[-2])

    temp_set = set(temp)
    result = list(temp_set) #폴더 내 파일이름(확장자x)만 남게됨

    n = int(len(result)*0.8)

    random.shuffle(result)
    random.shuffle(result)

    basic_dir = os.path.abspath(label_dir)

    with open('Train.txt', 'w') as f:
        for i in result[:n]:
            data = "{}/{}.jpg\n".format(basic_dir, i)
            f.write(data)

    with open('Valid.txt', 'w') as f:
        for i in result[n:]:
            data = "{}/{}.jpg\n".format(basic_dir, i)
            f.write(data)

if __name__ == "__main__":
    make_list_txt()