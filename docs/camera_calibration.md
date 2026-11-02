# Camera Calibration — nhiệm vụ 4

Hiệu chuẩn dùng Chessboard, mô hình pinhole OpenCV với 5 hệ số
`(k1, k2, p1, p2, k3)`. Không dùng ArUco hoặc mô hình học máy.

## Chạy và sử dụng trên Windows

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
.\.venv\Scripts\python.exe -m pytest -q
```

1. Trong thanh bên chọn **Camera Calibration**. Nhập số góc trong ngang/dọc và
   kích thước cạnh ô theo mm. Cấu hình phải khớp chính xác với bàn cờ trong ảnh.
2. Ở tab **Hiệu chuẩn từ ảnh**, upload nhiều ảnh. Tối thiểu 5 ảnh hợp lệ; khuyến
   nghị thực hành của dự án là 15–25 ảnh ở các vị trí, khoảng cách và hướng nghiêng
   khác nhau, phủ vùng ảnh. Không chỉ dịch chuyển hoặc xoay bàn cờ trong mặt phẳng.
3. Bấm **Kiểm tra ảnh bàn cờ** để xem số thành công/thất bại và lý do từng ảnh.
   Có thể chọn một ảnh để xem các góc đã đánh dấu. Không tự resize ảnh bị khác độ phân giải.
4. Bấm **Chạy hiệu chuẩn**. Ứng dụng cũng tự quét ảnh nếu chưa quét. Xem K, D,
   RMS tổng, RMSE từng ảnh, các rvec/tvec và tên ảnh tương ứng.
5. Bấm **Lưu calibration JSON** để tải file về máy. Tab **Nạp calibration** cho
   phép upload và kiểm tra lại file đã lưu; chỉ schema của VisionGauge được hỗ trợ.
6. Bấm **Áp dụng cho chức năng đo**, chuyển sang trang **Đo kích thước**. Chế độ
   **Dùng calibration đang áp dụng** được chọn. Upload/chụp ảnh thô từ cùng camera
   với cùng độ phân giải, zoom/focus; chương trình khử méo trước khi tìm góc/tính homography.

Calibration đang áp dụng chỉ được giữ trong phiên. Thay bộ ảnh hiệu chuẩn hoặc
cấu hình xóa kết quả hiệu chuẩn đang xây dựng; mô hình đã áp dụng vẫn còn hiệu lực
cho đến khi bấm áp dụng mô hình khác hoặc **Gỡ calibration đang áp dụng**. ID mô
hình được hiển thị để phân biệt. Lưu JSON trước khi đóng phiên.

Ảnh gốc bên trái giữ nguyên dữ liệu đầu vào; ảnh kết quả bên phải dùng tọa độ đã
khử méo. Không áp dụng calibration thêm lần nữa cho ảnh đã khử méo bên ngoài.

## Chụp trực tiếp bộ ảnh hiệu chuẩn

1. Vào **Camera Calibration → Hiệu chuẩn từ ảnh → Chụp camera**.
2. Chọn mức chụp 480p/720p/1080p (mặc định 720p), cho phép truy cập camera.
3. Chụp một ảnh rồi bấm **Thêm ảnh vào bộ hiệu chuẩn**. Khung chụp được làm trống
   để sẵn sàng cho ảnh tiếp theo. Chỉ chụp mà chưa bấm thêm thì ảnh chưa thuộc bộ dữ liệu.
4. Đổi vị trí, khoảng cách và góc nghiêng bàn cờ rồi lặp lại. Giữ cùng camera,
   zoom/focus và bàn cờ. Cần tối thiểu 5 ảnh nhận diện được, ưu tiên 15–25 ảnh đa dạng.
5. Xem số ảnh và độ phân giải thực tế. Có thể xem/xóa từng ảnh hoặc xóa cả bộ;
   mức chụp được khóa khi bộ ảnh còn ảnh. Ảnh khác độ phân giải, ảnh hỏng và ảnh
   trùng bytes không được thêm. Ảnh thiếu bàn cờ được báo ở bước kiểm tra tiếp theo.
6. Bấm **Kiểm tra ảnh bàn cờ**, rồi **Chạy hiệu chuẩn**, lưu JSON và áp dụng như
   quy trình upload. Hai nguồn được dùng riêng; chuyển nguồn không tự trộn dữ liệu.
7. **Tải bộ ảnh đã chụp (ZIP)** để giữ nguyên các ảnh JPEG gốc. Giải nén để upload
   lại sau này. Bộ ảnh được giữ khi đổi trang trong cùng phiên, nhưng có thể mất
   khi tải lại trình duyệt/đóng phiên/khởi động lại máy chủ.

Thêm/xóa ảnh hoặc đổi cấu hình sẽ làm mất hiệu lực kết quả hiệu chuẩn đang xây dựng.
Calibration đã áp dụng vẫn được giữ đến khi áp dụng mô hình mới hoặc gỡ mô hình.
Camera trình duyệt không bảo đảm mức phân giải yêu cầu; ảnh đầu tiên xác lập kích
thước thực tế của bộ ảnh và các ảnh tiếp theo phải khớp. Không resize/crop hoặc khử
méo ảnh trước khi đưa vào bộ hiệu chuẩn. Khi đo, dùng cùng thiết bị/chế độ chụp.

Mã giao diện ở [calibration_capture.py](../visiongauge/ui/calibration_capture.py),
quản lý bộ ảnh ở [capture_workflow.py](../visiongauge/ui/capture_workflow.py), tích hợp
trong [calibration_page.py](../visiongauge/ui/calibration_page.py). Test mới ở
[test_calibration_capture.py](../tests/test_calibration_capture.py) bao gồm tích lũy,
hiệu chuẩn từ 12 JPEG tổng hợp, áp dụng, xóa ảnh, chuyển trang, lỗi ảnh và xuất ZIP.
AppTest mô phỏng ảnh camera; chưa chứng nhận chất lượng trên camera vật lý.
Sau bổ sung tính năng chụp: **217 test toàn dự án đạt** trên Windows/Python 3.11.9.

## Thuật toán và kiểm tra dữ liệu

- Tái sử dụng detector SB với tọa độ dưới pixel và nhánh classic + `cornerSubPix`.
  Chỉ chấp nhận đủ góc. Ảnh hỏng, thiếu bàn cờ, khác độ phân giải và trùng nội
  dung bytes được báo riêng; ảnh bị loại không tham gia phép giải.
- Tọa độ góc 3D là `(column*s, row*s, 0)` mm. Tất cả ảnh phải dùng cùng bàn cờ.
- Kiểm tra hạng các ràng buộc nội tham từ các homography để từ chối bộ góc chụp
  suy biến/thiếu đa dạng. Đây là bộ lọc ban đầu, không chứng nhận bộ ảnh đủ tốt.
- Gọi `cv2.calibrateCamera` với các điểm 3D/2D và cùng image size. Không tự loại
  góc/ảnh có sai số lớn sau khi khớp để làm đẹp kết quả.
- Tính lại điểm bằng `cv2.projectPoints`. RMSE mỗi ảnh là căn bậc hai trung bình
  bình phương **khoảng cách Euclidean hai chiều** giữa góc quan sát và chiếu lại.
  RMS tổng lấy trên tất cả các góc, không chia norm cho số góc.
- Mặc định bộ giải từ chối RMS tổng > 1 px hoặc RMSE một ảnh > 2 px. Trang áp
  dụng cũng chặn mô hình nạp có sai số vượt ngưỡng này. Đây là ngưỡng kỹ thuật
  ban đầu, không phải dung sai sản phẩm hoặc chứng nhận độ chính xác.
- Kiểm tra K hữu hạn, tiêu cự dương, principal point trong ảnh, D đúng 5 hệ số,
  số vector ngoại tham khớp số ảnh, t_z dương, RMS nhất quán và không âm.
  Kiểm tra đơn điệu xuyên tâm bằng lấy mẫu trong miền ảnh; đây không phải chứng
  minh đầy đủ tính song ánh cho mọi mô hình méo tiếp tuyến.

Camera matrix K có đơn vị pixel; D không có đơn vị; rvec dùng Rodrigues/radian,
tvec dùng mm và biến đổi **hệ bàn cờ → hệ camera**, riêng cho mỗi ảnh. Bàn cờ đối
xứng có thể đảo cách đánh số giữa các ảnh nên rvec/tvec không phải theo dõi pose cố định.

## Hệ tọa độ sau khử méo

### Khi ảnh camera khác độ phân giải calibration

Ví dụ lỗi quan sát được: ảnh camera 778 × 584 nhưng calibration 1280 × 720.
Widget trước đây không đặt `resolution`, nên Streamlit lấy kích thước ảnh theo
kích thước widget. Hiện ứng dụng yêu cầu 480p/720p/1080p theo chiều cao calibration;
nếu chiều cao không thuộc ba mức này hoặc chưa dùng calibration, yêu cầu 720p.
Đây chỉ là yêu cầu tới camera; trình duyệt có thể trả độ phân giải hoặc tỉ lệ khác.
Xem [tài liệu camera_input](https://docs.streamlit.io/develop/api-reference/widgets/st.camera_input).

Sau cập nhật, chụp lại ảnh. Nếu vẫn khác kích thước, dùng file gốc từ cùng camera
và cùng chế độ chụp với bộ hiệu chuẩn, hoặc hiệu chuẩn lại cho nguồn/chế độ hiện tại.
Không resize/crop để ép khớp hay chọn chế độ ảnh đã khử méo để bỏ qua kiểm tra.
Ứng dụng giữ ảnh gốc, giải thích cách khắc phục và chặn đo nếu không tương thích.

`undistort_image` dùng `cv2.undistort(image, K, D, None, K)`:

- Giữ nguyên `(width, height)` và ma trận chiếu K, không crop hoặc tự resize.
- Ảnh khác độ phân giải calibration bị từ chối. Không suy ra cùng camera chỉ
  vì hai ảnh có cùng độ phân giải; người dùng phải bảo đảm nguồn camera/ống kính.
- `undistort_image_points` dùng `P=K`, trả **pixel đã khử méo**, không phải tọa độ
  camera chuẩn hóa. Phát hiện bàn cờ và contours đều chạy trên ảnh đã khử méo.
- Homography chỉ được tính sau khử méo; không trộn góc của ảnh thô với contours
  của ảnh đã khử méo. Có thể có vùng đen ở mép sau phép nội suy.

## API độc lập giao diện

```python
from pathlib import Path
from visiongauge.config import ChessboardConfig
from visiongauge.calibration import (
    scan_calibration_images, calibrate_camera, save_calibration,
    load_calibration, undistort_image,
)
from visiongauge.image_io import read_image
from visiongauge.measurement import measure_rectangle

board = ChessboardConfig(columns=9, rows=6, square_size_mm=25.0)
files = [(p.name, p.read_bytes()) for p in Path("data/calibration").glob("*.png")]
scan = scan_calibration_images(files, board)
print(scan.failures)  # Xem ảnh bị loại trước khi quyết định sử dụng bộ dữ liệu.
calibration = calibrate_camera(scan.views, board)
save_calibration("data/camera.json", calibration)

loaded = load_calibration("data/camera.json")
corrected = undistort_image(read_image("data/product.png"), loaded)
result = measure_rectangle(corrected, board, image_geometry="undistorted")
print(result.length_mm, result.width_mm)
```

Thư mục/file trong ví dụ phải do người dùng cung cấp. CLI đo của nhiệm vụ 2 vẫn
nhận ảnh đã khử méo hoặc giả thiết méo không đáng kể; quy trình calibration mới
dùng giao diện/API trên. JSON lưu cả K, D, image size, bàn cờ, rvec/tvec, tên ảnh,
sai số từng ảnh, RMS, đơn vị và schema. Không dùng pickle hoặc thực thi dữ liệu khi nạp.

## So sánh trước / sau trên dữ liệu thực

Tab **So sánh trước / sau** nhận nhiều ảnh sản phẩm và dùng calibration đang áp
dụng. Nhập cấu hình bàn cờ khớp các ảnh sản phẩm trong thanh bên (có thể khác bàn
cờ đã dùng để hiệu chuẩn camera). Mỗi file được chạy cùng thuật toán, cùng cấu
hình/tách biên mặc định ở cả hai nhánh; chỉ nhánh sau khử méo trước.

Nhánh `raw` cố ý bỏ qua méo để tái hiện baseline cũ; điều này **không xác nhận**
ảnh thô không méo và không được dùng để kiểm tra dung sai. Nhánh `corrected`
khử méo với K/D đã chọn. Nếu một nhánh thất bại, giữ dòng báo lỗi và giá trị thiếu,
không thay bằng 0 hoặc loại ảnh âm thầm.

CSV tham chiếu UTF-8 có ba cột:

```text
filename,length_mm,width_mm
```

Mỗi dòng cần tên file chính xác và kích thước thực đo từ dụng cụ tham chiếu, đơn
vị mm, chiều dài >= chiều rộng > 0. Không có dòng dữ liệu mẫu giả trong tài liệu này.
Tên trùng, file không có trong bộ ảnh, NaN hoặc kích thước sai bị từ chối.

Không có tham chiếu: chỉ hiển thị số đo trước/sau và lỗi xử lý. Có tham chiếu:
MAE/RMSE từng chiều chỉ tính trên **cùng tập ảnh** đo thành công ở cả hai nhánh.
Hiển thị số cặp được dùng/số ảnh bị loại. CSV tải về chứa số đo, sai số có dấu,
lỗi xử lý và ID calibration; không tự tuyên bố cải thiện hoặc ý nghĩa thống kê.

**Chưa có bộ ảnh thực tế và số đo tham chiếu được cung cấp trong nhiệm vụ này.**
Do đó chức năng so sánh đã sẵn sàng, nhưng đánh giá cải thiện độ chính xác thực
tế còn chờ dữ liệu. Test tổng hợp không thay thế bước thực nghiệm này.

## Kiểm thử và giới hạn

Bộ test toàn dự án: **208 passed** trên Windows/Python 3.11.9 (29,60 giây).
Editor không báo lỗi. Máy chủ Streamlit khởi động được trên localhost.
Trang Camera Calibration được kiểm tra trên trình duyệt ở khung 1280 px và
390 px, không tràn ngang toàn trang. Sau chỉnh sửa câu hướng dẫn chế độ khử méo,
28 test giao diện chạy lại đều đạt. Camera vật lý chưa được kiểm thử.

- Khôi phục camera biết trước từ tọa độ chiếu tổng hợp; hiệu chuẩn từ 12 ảnh có
  méo được dựng độc lập và đo một ảnh sản phẩm tổng hợp tách khỏi bộ hiệu chuẩn.
- Kiểm tra dưới 5 ảnh, ảnh hỏng/không có bàn cờ, trùng ảnh, độ phân giải khác,
  góc chụp suy biến, lỗi chiếu lại lớn và cấu hình/JSON không hợp lệ.
- Kiểm tra save/load round-trip, khử méo giữ ảnh gốc, độ phân giải, điểm đã khử
  méo khớp phép chiếu không méo và homography trả lại tọa độ mm.
- Streamlit AppTest chạy các widget nhiều ảnh, fit, download, load/apply,
  đo ảnh đã khử méo, ngăn khử méo lặp lại khi rerun, xóa kết quả cũ và so sánh CSV.
- Chỉ hỗ trợ pinhole 5 hệ số, chưa hỗ trợ fisheye, tự động scale K theo resize,
  đánh giá độ không đảm bảo đo hoặc xác minh vật/bàn cờ đồng phẳng.
- Chưa kiểm thử camera vật lý hoặc Python 3.12. Không thay đổi thuật toán contour,
  hình học mm và homography đã có để làm đẹp kết quả hiệu chuẩn.

Tham khảo: [OpenCV Camera Calibration and 3D Reconstruction](https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html).

## File tạo/sửa

- Lõi: [camera.py](../visiongauge/calibration/camera.py), [camera_model.py](../visiongauge/calibration/camera_model.py),
  [calibration/__init__.py](../visiongauge/calibration/__init__.py), [errors.py](../visiongauge/errors.py),
  [comparison.py](../visiongauge/measurement/comparison.py), [version](../visiongauge/__init__.py).
- Giao diện: [calibration_page.py](../visiongauge/ui/calibration_page.py),
  [calibration_workflow.py](../visiongauge/ui/calibration_workflow.py), [app.py](../visiongauge/ui/app.py),
  [workflow.py](../visiongauge/ui/workflow.py), [views.py](../visiongauge/ui/views.py).
- Test: [camera_fixtures.py](../tests/camera_fixtures.py), [test_camera_calibration.py](../tests/test_camera_calibration.py),
  [test_calibration_app.py](../tests/test_calibration_app.py), [test_comparison.py](../tests/test_comparison.py),
  [test_ui_workflow.py](../tests/test_ui_workflow.py).
- Tài liệu: [README.md](../README.md), [measurement.md](measurement.md), [ui.md](ui.md) và tài liệu này.
