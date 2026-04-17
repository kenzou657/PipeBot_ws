import cv2

cap = cv2.VideoCapture(0)

# 设置分辨率
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

# 验证实际设置
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = int(cap.get(cv2.CAP_PROP_FPS))

ret, frame = cap.read()

print(f"分辨率: {width}x{height}")
print(f"帧率: {fps} FPS")

if ret:
    cv2.imwrite('test_image.jpg', frame)
    print("✓ 图像已保存为 test_image.jpg")
else:
    print("❌ 捕获失败")

cap.release()
