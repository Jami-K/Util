import cv2, os, shutil, time
from multiprocessing import Process
from pypylon import pylon

class q2save:
    def main(self, camera_num):
        # 카메라 관련 설정
        camera_num = camera_num
        dirpath = './img_Grab/'
        window_name = 'Press Q to start saving Image / Press S to stop / ESC = Quit'
        self.camera_setting = None
        self.name = 0
        self.total_num = 0
        self.operating = 0  # off

        self.make_dir(dirpath)
        self.load_camera(camera_num)
        print("I'm Ready to Start!")

        start_time = time.time()
        saved_images = 0 

        while self.cameras.IsGrabbing():
            self.grabResult = self.cameras.RetrieveResult(50000, pylon.TimeoutHandling_ThrowException)

            if self.grabResult.GrabSucceeded():
                image_raw = self.converter.Convert(self.grabResult)
                image = image_raw.GetArray()
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                self.img = image

                cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
                cv2.imshow(window_name, self.img)

                k = cv2.waitKey(1) & 0xFF

                if k == ord('q'):
                    self.operating = 1

                if k == ord('s'):
                    self.operating = 0

                if self.operating == 1 and saved_images < 10:
                    print("Save Image as {}.jpg".format(self.name))
                    self.total_num += 1
                    self.save_img(dirpath)
                    saved_images += 1

                if saved_images == 10:
                    if time.time() - start_time >= 300:  # 5분이 지났는지 확인
                        saved_images = 0
                        start_time = time.time()

                if k == 27:
                    cv2.destroyAllWindows()
                    print("\nYou got {} image sample..!\n".format(self.total_num))
                    break

    def load_camera(self, camera_num):  # 카메라 설정 불러오기
        maxCamerasToUse = 1
        tlFactory = pylon.TlFactory.GetInstance()
        devices = tlFactory.EnumerateDevices()

        self.cameras = pylon.InstantCameraArray(min(len(devices), maxCamerasToUse))
        for i, self.cam in enumerate(self.cameras):
            self.cam.Attach(tlFactory.CreateDevice(devices[camera_num]))
        self.cameras.Open()

        if self.camera_setting is not None:
            pylon.FeaturePersistence.Load(self.camera_setting, self.cam.GetNodeMap(), True)

        self.cameras.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

        self.converter = pylon.ImageFormatConverter()
        self.converter.OutputPixelFormat = pylon.PixelType_BGR8packed
        self.converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned

    def make_dir(self, dir_path):
        checking = str(dir_path) + '0.jpg'
        if os.path.exists(checking):
            shutil.rmtree(dir_path)
            os.mkdir(dir_path)
        else:
            if os.path.exists(dir_path):
                pass
            else:
                os.mkdir(dir_path)
        print("\nThe New Saving Folder is Ready..! \n")

    def save_img(self, dirpath):
        dirpath_img = str(dirpath) + str(self.name) + '.jpg'
        cv2.imwrite(dirpath_img, self.img)
        self.name += 1


if __name__ == "__main__":
    a = q2save()
    a.main(0)
