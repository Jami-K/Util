import cv2, os, shutil
from multiprocessing import Process
from pypylon import pylon

class q2save:
    def main(self, camera_num):
        #카메라 관련 설정
        camera_num = camera_num
        dirpath = './q2save/'
        window_name = 'Press Q to save Image / ESC = Quit'
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
        print("I'm Ready to Start!")

        while self.cameras.IsGrabbing():
            self.grabResult = self.cameras.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)

            if self.grabResult.GrabSucceeded():
                image_raw = self.converter.Convert(self.grabResult)
                image = image_raw.GetArray()
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                self.img = image

                cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
                cv2.imshow(window_name, self.img)

                k = cv2.waitKey(1) & 0xFF

                if k == ord('q'):
                    print("Save Image as {}.jpg".format(self.name))
                    self.save_img(dirpath)

                if k == 27:
                    cv2.destroyAllWindows()
                    break

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
