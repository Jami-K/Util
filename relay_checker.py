import hid
import time

# HID 장치 목록 확인
devices = hid.enumerate()
for d in devices:
    print(f"Vendor ID: {hex(d['vendor_id'])}, Product ID: {hex(d['product_id'])}")
    print(f"Manufacturer: {d.get('manufacturer_string', 'N/A')}")
    print(f"Product: {d.get('product_string', 'N/A')}")
    print(f"Path: {d['path']}")
    print("-" * 30)

# 특정 HID 장치 열기
VENDOR_ID = 0x16c0  # 예시 Vendor ID
PRODUCT_ID = 0x05df  # 예시 Product ID

try:
    # 장치를 여는 가장 일반적인 방식
    device = hid.Device(VENDOR_ID, PRODUCT_ID)
    print("USB HID 장치에 연결되었습니다.")
except Exception as e:
    print(f"장치 연결 실패: {e}")
    exit()

# 릴레이 제어 함수
def relay_control(on: bool):
    """
    릴레이를 켜거나 끕니다.
    :param on: True면 켜기, False면 끄기
    """
    try:
        if on:
            device.write([0x00, 0xFF, 0x01])
            print("릴레이가 켜졌습니다.")
        else:
            device.write([0x00, 0xFF, 0x00])
            print("릴레이가 꺼졌습니다.")
    except Exception as e:
        print(f"릴레이 제어 중 오류가 발생했습니다: {e}")

# 릴레이 테스트
relay_control(True)
time.sleep(5)
relay_control(False)

# 장치 닫기
device.close()
print("장치 연결이 해제되었습니다.")
