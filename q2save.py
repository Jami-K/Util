import cv2, os, shutil
from multiprocessing import Process
from pypylon import pylon

class q2save:
    def main(self, camera_num):
        #카메라 관련 설정
        camera_num = camera_num
        dirpath = './q2save/'
        window_name = 'Press Q to save Image // Press S to change Mode // ESC = Quit'
        self.camera_setting = None
        self.name = 0

        checking = str(dirpath) + '0.jpg'
        if os.path.exists(checking):
            shutil.rmtree(dirpath)
            os.mkdir(dirpath)
        else:
            if os.path.exists(dirpath):
                pass
            else:
                os.mkdir(dirpath)

        self.load_camera(camera_num)
        #print("I'm Ready to Start!")
        saving = False
        auto_mode = True
        saved_count = 0

        while self.cameras.IsGrabbing():
            self.grabResult = self.cameras.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)

            if self.grabResult.GrabSucceeded():
                image_raw = self.converter.Convert(self.grabResult)
                image = image_raw.GetArray()
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                #image = image[0:494, 144:600]
                self.img = image
                
                k = cv2.waitKey(1) & 0xFF

                if k == ord('q'):
                    if auto_mode:
                        if not saving:
                            saving = True
                            print("Auto Image Saving system ON...")
                    else:
                        print("Save Image as {}.jpg".format(self.name))
                        self.save_img(dirpath)

                if saving and saved_count <= 100:
                    print("Save Image as {}.jpg".format(self.name))
                    self.save_img(dirpath)
                    saved_count += 1

                if saved_count > 100:
                    print("Auto Image Saving system OFF...")
                    saving = False
                    saved_count = 0

                if k == ord('s'):
                    if auto_mode:
                        auto_mode = False
                        print("MODE Changed : Manual")
                    else:
                        auto_mode = True
                        print("MODE Changed : Auto")
                
                if k == 27:
                    cv2.destroyAllWindows()
                    break

                if auto_mode:
                    cv2.putText(image, "Auto", (300,50), cv2.FONT_HERSHEY_PALIN, 2, (255,0,0), 2)
                else:
                    cv2.putText(image, "Manual", (300,50), cv2.FONT_HERSHEY_PALIN, 2, (255,0,0), 2)
                    
                cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
                cv2.imshow(window_name, image)

    
    def load_camera(self, camera_num):  # 카메라 설정 불러오기
        maxCamerasToUse = 1
        tlFactory = pylon.TlFactory.GetInstance()
        devices = tlFactory.EnumerateDevices()

        self.cameras = pylon.InstantCameraArray(min(len(devices), maxCamerasToUse))
        for i, self.cam in enumerate(self.cameras):
            self.cam.Attach(tlFactory.CreateDevice(devices[camera_num]))
        self.cameras.Open()

        if self.camera_setting != None:
            pylon.FeaturePersistence.Load(self.camera_setting, self.cam.GetNodeMap(), True)

        self.cameras.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

        self.converter = pylon.ImageFormatConverter()
        self.converter.OutputPixelFormat = pylon.PixelType_BGR8packed
        self.converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned

    def save_img(self, dirpath):
        dirpath_img = str(dirpath) + str(self.name) + '.jpg'
        cv2.imwrite(dirpath_img, self.img)
        self.name += 1

if __name__ == "__main__":
    a = q2save()
    a.main(0)
