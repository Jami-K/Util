import os

dir_path = '/Users/kim/nongshim/작업용/멸치221212/OK'. #경로
type_name = 'M'  #분류용 글자
date = 2212120000   #이미지 촬영 일자

def changeName(path, cName):
    i = date
    for filename in os.listdir(path):
        print(path+filename, '=>', path+str(cName)+str(i)+'.jpg')
        os.rename(path+filename, path+str(cName)+str(i)+'.jpg')
        i += 1

changeName(dir_path,type_name)

# 간편하게 폴더 내 모든 파일 옮기는 방법
# cp -r 폴더명/* Train

# 폴더 내부 랜덤하게 파일 삭제하는 방법
# find ./ -type f -print0 | sort -zR | tail -zn +10000 | xargs -0 rm

# TXT 파일 내부 글자 바꾸는 방법 (vi)
# :%s(기존텍스트)/(변경텍스트)
# '/'는 앞에 | 붙일 것
