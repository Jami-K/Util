import cv2, os, shutil, time
import numpy as np
from datetime import datetime
from pypylon import pylon

class Camera:
    """ 카메라 활성화 """
    def __init__(self, camera_ip, camera_setting, camera_mode='VIDEO'):
        self.camera_ip = camera_ip
        self.camera_setting = camera_setting
        self.camera_mode = camera_mode
        
    """ 카메라 설정 """
    def load_camera(self):
        maxCamerasToUse = 1
        devices = pylon.TlFactory.GetInstance().EnumerateDevices()
        selectedDevice = None
        
        self.cam = None
        
        if len(devices) > 0:
            for device in devices:
                if device.GetIpAddress() == self.camera_ip:
                    selectedDevice = device
                    print('Camera_IP :', selectedDevice.GetIpAddress())
        elif len(devices) == 0:
            raise pylon.RuntimeException("\n카메라 네트워크 상태 또는 주소를 확인해주세요.")

        if selectedDevice is not None:
            try:
                self.cam = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateDevice(selectedDevice))
                self.cam.Open()
            except: pass
            
            if self.camera_setting is not None:
                try:
                    pylon.FeaturePersistence.Load(self.camera_setting, self.cam.GetNodeMap(), True)
                except pylon.GenericException as e:
                    raise NameError(f"카메라 pfs 설정파일 오류 : \n{str(e)}")
            
            self.cam.TriggerMode.SetValue('Off')
            if self.camera_mode == 'VIDEO':
                self.cam.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
            elif self.camera_mode == 'TRIGGER':
                try:
                    self.cam.TriggerSelector.SetValue('FrameStart')
                    self.cam.TriggerSource.SetValue('Line1')
                    self.cam.TriggerActivation.SetValue('RisingEdge')
                    self.cam.TriggerMode.SetValue('On')
                    self.cam.StartGrabbing(pylon.GrabStrategy_OneByOne)
                except pylon.GenericException as e:
                    raise NameError(f"카메라 트리거모드 설정 초기화 오류 : \n{str(e)}")

            try:
                self.converter = pylon.ImageFormatConverter()
                self.converter.OutputPixelFormat = pylon.PixelType_BGR8packed
                self.converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned
            except Exception as e:
                raise NameError(f"카메라 이미지 컨버터 설정 초기화 오류 : \n{str(e)}")   
                
            return self.cam, self.converter
            
    """ 이미지 생성 """
    def get_img(self, cameras, converter, image_no):
        grab_on = 0 #카메라 인식 초기화
        grabResult = 0
        try:
            grabResult = cameras.RetrieveResult(2000, pylon.TimeoutHandling_ThrowException) #2초 반응없을 시 넘어감 
            if grabResult.GrabSucceeded():
                image_raw = converter.Convert(grabResult).GetArray()
                #image_raw = cv2.rotate(image_raw,cv2.ROTATE_90_CLOCKWISE) #시계방향 90도 회전
                image_rgb = cv2.cvtColor(image_raw, cv2.COLOR_BGR2RGB)
                grab_on = 2
                return image_raw, image_rgb, grabResult, grab_on
            else : 
                grab_on = 1
                print('Can\'t Read the Image')
        except:
            grab_on = 0
            print('Can\'t Read the Camera')
        return image_no, image_no, grabResult, grab_on #인식 실패 , 카메라 고장, 센서 미입력 등

    def destory_cam(self):
        if self.cam is not None:
            self.cam.StopGrabbing()
            self.cam.Close()
            self.cam = None

def create_folder(path):
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"폴더가 생성되었습니다: {path}")
    else:
        print(f"폴더가 이미 존재합니다: {path}")
    
    return path

def Q2save(image, path, name):
    # 카메라 관련 설정
    save_path = os.path.join(path, name) + '.jpg'
    cv2.imwrite(save_path, image)
    print("Save Image as {}.jpg".format(name))


if __name__ == "__main__":
    camera_ip = '192.168.80.1'
    camera_setting = './acA640-120gm_23532785.pfs'

    CAM = Camera(camera_ip, camera_setting, camera_mode='TRIGGER')
    cam, converter = CAM.load_camera()
    
    window_name = 'Press Q to start saving Image / Press S to stop / ESC = Quit'
    last_save_time = time.time()
    last_img_save_number = 0
    operating = 0
    
    dir_path = create_folder('./img_Grab/')
    
    cam.UserOutputValue.SetValue(False) # 카메라 출력 초기화
    
    image_no = np.zeros((494,659,3), np.uint8)
    text_size = cv2.getTextSize('NO IMAGE', cv2.FONT_HERSHEY_PLAIN, 5, 3)[0]
    cv2.putText(image_no, 'No Image', (int((659 - text_size[0]) / 2), int((494 + text_size[1]) / 2)), 
                    cv2.FONT_HERSHEY_PLAIN, 5, [225,255,255], 3)
    
    maked_img = image_no
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 1318, 988)
    cv2.imshow(window_name, maked_img)
    
    while True:
        image_raw, maked_img, grabResult, grab_on = CAM.get_img(cam, converter, image_no)
    
        if grab_on == 2 and operating == 1:
            if last_img_save_number < 10:
                img_name = datetime.now().strftime('%Y-%m-%d_%H-%M-%S-%f')
                Q2save(maked_img, dir_path, img_name)
                last_img_save_number += 1
            else: pass
            if time.time() - last_save_time >= 300: # 5분이 지났는지 확인
                last_img_save_number = 0
                last_save_time = time.time()
            else: pass
            
        cv2.imshow(window_name, maked_img)
        cv2.resizeWindow(window_name, 1318, 988)
        
        k = cv2.waitKey(1) & 0xFF
        
        if k == ord('q'):
            operating = 1
        elif k == ord('s'):
            operating = 0
        elif k == 27:
            break
        
        if grabResult != 0:
            grabResult.Release()
    
    CAM.destory_cam()
    cv2.destroyAllWindows()
