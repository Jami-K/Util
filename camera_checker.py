import time
import cv2
import numpy as np
from pypylon import pylon
from time import sleep

class Camera:
    """ 카메라 활성화 """
    def __init__(self,camera_ip,camera_setting):
        self.camera_ip = camera_ip
        self.camera_setting = camera_setting
    """ 카메라 설정 """
    def load_camera(self):
        maxCamerasToUse = 1
        tlFactory = pylon.TlFactory.GetInstance()
        devices = tlFactory.EnumerateDevices()
        for dev_info in devices:
            #print(dev_info)
            if dev_info.GetIpAddress() == self.camera_ip:
                cam_info = dev_info
                print('Camera_IP :',cam_info.GetIpAddress())
        if len(devices) == 0:
            raise pylon.RuntimeException("\n카메라 네트워크 상태 또는 주소를 확인해주세요.")

        self.cameras = pylon.InstantCameraArray(min(len(devices), maxCamerasToUse))
        for i, self.cam in enumerate(self.cameras):
            self.cam.Attach(tlFactory.CreateDevice(cam_info))
        self.cameras.Open()
        try:
            pylon.FeaturePersistence.Load(self.camera_setting, self.cam.GetNodeMap(), True)
        except:
            raise pylon.RuntimeException("\n카메라 세팅 파일이 없습니다.")
        self.cameras.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
        self.converter = pylon.ImageFormatConverter()
        self.converter.OutputPixelFormat = pylon.PixelType_BGR8packed
        self.converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned
        return self.cam,self.cameras,self.converter
    """ 이미지 생성 """
    def get_img(self,cameras,converter,image_no,image):
        grab_on = 0 #카메라 인식 초기화
        grabResult = 0
        try:
            grabResult = cameras.RetrieveResult(2000, pylon.TimeoutHandling_ThrowException) #2초 반응없을 시 넘어감 
            if grabResult.GrabSucceeded():
                image_raw = converter.Convert(grabResult).GetArray()
                #image_raw = cv2.rotate(image_raw,cv2.ROTATE_90_CLOCKWISE) #시계방향 90도 회전
                image_rgb = cv2.cvtColor(image_raw, cv2.COLOR_BGR2RGB)
                grab_on = 2
                return image_raw,image_rgb,image_rgb,grabResult,grab_on
            else : 
                grab_on = 1
                print('Can\'t Read the Image')
        except:
            grab_on = 0
            print('Can\'t Read the Camera')
        return image_no,image,image,grabResult,grab_on #인식 실패 , 카메라 고장, 센서 미입력 등


if __name__ == "__main__":
    camera_ip = '192.168.80.12'
    camera_setting = './acA640-300gm_24346014.pfs'

    cam, cameras, converter = Camera(camera_ip, camera_setting).load_camera()
    
    cam.UserOutputValue.SetValue(False) # 카메라 출력 초기화
    
    image_no = np.zeros((494,659,3), np.uint8)
    text_size = cv2.getTextSize('NO IMAGE', cv2.FONT_HERSHEY_PLAIN, 5, 3)[0]
    cv2.putText(image_no, 'No Image', (int((659 - text_size[0]) / 2), int((494 + text_size[1]) / 2)), 
                    cv2.FONT_HERSHEY_PLAIN, 5, [225,255,255], 3)
    
    maked_img = image_no
    cv2.imshow('Q to Quit', maked_img)
    
    while True:
        CAM = Camera(camera_ip, camera_setting)
    
        image_raw, image_rgb, maked_img, grabResult, grab_on = CAM.get_img(cameras, converter, image_no, image_no)
    
        cv2.imshow('Q to Quit', maked_img)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        elif cv2.waitKey(1) & 0xFF == ord('k'):
            print("카메라에서 신호를 출력합니다.")
            cam.UserOutputValue.SetValue(True)
            sleep(0.5)
            cam.UserOutputValue.SetValue(False)
            print("카메라에서 신호를 초기화합니다.")
        
        if grabResult != 0:
            grabResult.Release()
    
    cameras.StopGrabbing()
    cv2.destroyAllWindows()
