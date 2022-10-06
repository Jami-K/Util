import os
 
def changeName(path, cName):
    i = 22071100001
    for filename in os.listdir(path):
        print(path+filename, '=>', path+str(cName)+str(i)+'.jpg')
        os.rename(path+filename, path+str(cName)+str(i)+'.jpg')
        i += 1
 
changeName('/home/nongshim/tray/Database/2022-07-08/','')

# 간편하게 폴더 내 모든 파일 옮기는 방법
# cp -r 폴더명/* Train
