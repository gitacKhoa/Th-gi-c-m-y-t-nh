# Nhiệm vụ 2 — đo sản phẩm chữ nhật với Chessboard

Pipeline độc lập với Streamlit, chỉ dùng OpenCV/NumPy, không dùng marker hoặc AI.
Đầu vào là một ảnh có bàn cờ và một sản phẩm chữ nhật phẳng **cùng mặt phẳng**.
Các cạnh vật cần đủ tương phản với nền, không bị che, cắt khỏi ảnh hoặc chạm vùng
bàn cờ. Nền nên đồng nhất; ánh sáng phản xạ/bóng đổ mạnh có thể làm tách vật thất bại.

## Chạy ví dụ tổng hợp trên Windows

Tại thư mục gốc dự án, sau khi đã cài [requirements.txt](../requirements.txt):

```powershell
.\.venv\Scripts\python.exe -m tests.synthetic --output data/synthetic
.\.venv\Scripts\python.exe -m visiongauge data/synthetic/synthetic_65x35mm_angle57_perspective2.png --columns 7 --rows 5 --square-size-mm 10 --image-geometry undistorted --output reports/synthetic_measurement.png
.\.venv\Scripts\python.exe -m pytest -q
```

Ba ảnh tạo bởi [tests/synthetic.py](../tests/synthetic.py) đều có vật được thiết kế
65 × 35 mm và bàn cờ 7 × 5 **góc trong**, cạnh ô 10 mm. Đây là hình ảnh dựng tổng
hợp, không phải dữ liệu thực nghiệm. Không dùng cấu hình mẫu 9 × 6/25 mm trong
[settings.toml](../config/settings.toml) để đo các ảnh 7 × 5/10 mm này.

CLI trả mã 0 khi đo thành công, mã 2 khi không thể đánh giá. Tùy chọn
`--segmentation canny` chọn Canny; mặc định dùng Otsu. `--output` chỉ lưu PNG
đã chú thích, không lưu lịch sử hoặc phân loại dung sai. CLI không cho ghi đè
chính ảnh đầu vào. Đầu ra văn bản là UTF-8, kể cả terminal Windows có mã mặc định cp1252.

## Điều kiện méo ống kính

`image_geometry` là khai báo bắt buộc của người gọi, không phải bước xử lý ảnh:

- `undistorted`: ảnh **đã được khử méo** bằng thông số camera phù hợp, hoặc ảnh
  tổng hợp vốn không có méo ống kính.
- `negligible_distortion`: người gọi đã xác định rằng méo ống kính không đáng kể
  cho thiết lập đo đang dùng. Kết quả kèm cảnh báo về giả thiết này.

Nếu không khai báo, pipeline báo `CalibrationRequiredError`. Nó không tự suy ra
ống kính không méo từ sai số homography nhỏ. Từ nhiệm vụ 4, dùng trang
[Camera Calibration](camera_calibration.md) hoặc `undistort_image` trước khi
đưa ảnh vào pipeline. Bàn cờ và vật phải được xử lý
trong **cùng một ảnh đã khử méo**, không trộn tọa độ trước/sau khử méo.

## API Python

```python
from visiongauge.config import ChessboardConfig
from visiongauge.errors import VisionGaugeError
from visiongauge.image_io import read_image
from visiongauge.measurement import measure_rectangle

board = ChessboardConfig(columns=7, rows=5, square_size_mm=10.0)
try:
    image = read_image("data/synthetic/synthetic_65x35mm_angle57_perspective2.png")
    result = measure_rectangle(image, board, image_geometry="undistorted")
    print(result.length_mm, result.width_mm)
    annotated_bgr = result.annotated_image
except VisionGaugeError as exc:
    print(f"KHÔNG THỂ ĐÁNH GIÁ: {exc}")
```

Kết quả `MeasurementResult` cung cấp:

- `length_mm`, `width_mm`: cạnh dài và cạnh ngắn của hình chữ nhật khớp trong mm.
- `rectangle.corners_mm`, `corners_px`: bốn góc hình chữ nhật đã khớp, lần lượt
  trong mặt phẳng mm và trong ảnh đầu vào; không phải các góc bounding box pixel.
- `board`: các góc bàn cờ, tọa độ mm và phương pháp phát hiện.
- `mapping`: homography hai chiều, thông số bàn cờ và chỉ số chất lượng chiếu lại.
- `annotated_image`: ảnh BGR với góc bàn cờ, đường đo và kích thước; ảnh gốc không bị sửa.
- `segmentation_mask`: kết quả Otsu/Canny để chẩn đoán; có thể vẫn thấy bàn cờ trong
  mask vì việc loại bỏ bàn cờ thực hiện trên contours, không tạo biên giả bằng cắt mask.
- `warnings`: giả thiết/giới hạn cần giữ lại khi hiển thị kết quả.

Không import Streamlit trong các module thuật toán. Chưa có kết luận ĐẠT/KHÔNG ĐẠT.

## Luồng và tiêu chí chấp nhận

1. **Đọc ảnh:** giải mã bằng nội dung bytes để hỗ trợ đường dẫn Unicode Windows.
   Chấp nhận uint8 grayscale/BGR/BGRA đục; ảnh được chuẩn hóa sang BGR khi đọc file.
   Từ chối ảnh rỗng, hỏng, quá nhỏ, sai số kênh, float/16-bit hoặc ảnh trong suốt.
   API ndarray nhận BGR, không tự nhận biết RGB.
2. **Tìm bàn cờ:** ưu tiên `findChessboardCornersSB` với `CALIB_CB_ACCURACY`.
   SB đã trả vị trí dưới pixel; không tinh chỉnh thêm một cách mặc định. Nếu SB
   thất bại, dùng `findChessboardCorners` và `cornerSubPix` với cửa sổ theo khoảng
   cách góc. Cần đủ mọi góc trong cấu hình; không nội suy các góc bị che khuất.
3. **Tọa độ chuẩn:** góc tại cột i, hàng j có tọa độ `(i*s, j*s)` mm. Gốc là góc
   trong đầu tiên do detector sắp xếp. Bàn cờ đối xứng có thể đảo gốc/hướng trục
   giữa các lần chụp; chiều dài/chiều rộng không đổi, nhưng không dùng hệ tọa độ
   này để theo dõi pose tuyệt đối giữa các ảnh.
4. **Homography:** khớp tất cả các góc bằng `findHomography`, không bỏ góc lỗi để
   che giấu chất lượng kém. Kiểm tra lưới, suy biến, khoảng cách góc, hướng các ô,
   sai số chiếu ngược trong pixel và vùng ngoại suy. RMSE mm được tính từ các
   góc đã ánh xạ so với tọa độ chuẩn.
5. **Tách vật:** grayscale → Gaussian Blur → Otsu hoặc Canny → contours. Loại
   contours nhỏ, quá mảnh, chạm mép ảnh và giao với **toàn bộ bàn cờ**, kể cả các
   ô ngoài cùng và khoảng đệm. Không đơn giản chọn contour lớn nhất.
6. **Hình học:** chuyển toàn bộ contour ứng viên qua homography trước; kiểm tra
   tứ giác lồi, vuông góc, cạnh đối và độ lấp đầy trong **mm**. Sau đó dùng
   `minAreaRect` trong mặt phẳng mm; `length=max(a,b)`, `width=min(a,b)`.
   Không nhân kích thước bounding box ảnh với một tỉ lệ pixel/mm cố định.
7. **Chọn vật:** hợp nhất đường biên trong/ngoài gần trùng nhau từ Canny; từ chối
   nhiều vật ứng viên. Contour lớn không ánh xạ được khiến phép đo bị từ chối,
   tránh lấy nhầm một vật khác làm kết quả. Vẽ kích thước bằng phép chiếu ngược.

Ngưỡng mặc định là tham số kỹ thuật ban đầu, **không phải dung sai hoặc độ chính
xác đã được chứng nhận**:

| Nhóm | Ngưỡng mặc định |
| --- | --- |
| `MappingOptions` | Khoảng cách góc >= 8 px; RMSE <= 0.6 px; lỗi cực đại <= 1.5 px |
| Lưới/ngoại suy | Tỉ số khoảng cách cạnh lớn nhất/nhỏ nhất <= 5; ngoại suy tối đa 10 ô ngoài miền góc trong theo mỗi trục |
| `ContourOptions` | Gaussian 5 × 5; diện tích >= 250 px²; cạnh ngắn >= 10 px; mép ảnh 2 px; đệm bàn cờ 0.25 ô |
| Canny | Ngưỡng thấp/cao 50/150 |
| `RectangleOptions` | Độ lấp đầy >= 0.94; xấp xỉ contour 1.5% chu vi; lệch vuông góc <= 8°; lệch cạnh đối <= 10% |

Có thể truyền `mapping_options`, `contour_options`, `rectangle_options` vào API.
Không nên nới ngưỡng chỉ để buộc một ảnh xấu cho ra số đo.

Các lỗi có kiểu riêng trong [errors.py](../visiongauge/errors.py):
`InvalidImageError`, `CalibrationRequiredError`, `ChessboardNotFoundError`,
`UnreliableMappingError`, `ProductNotFoundError`, `AmbiguousProductError`,
`UnreliableMeasurementError`. Tất cả kế thừa `VisionGaugeError`; hệ thống gọi phải
coi chúng là không thể đánh giá, không phải sản phẩm ngoài dung sai.

## Kiểm thử và giới hạn

Kết quả kiểm thử nhiệm vụ 2 trên Windows/Python 3.11.9: **140 passed in 9.27s**
(49 test nền và 91 test mới). Kiểm tra diagnostics của workspace không báo lỗi.
Đã chạy CLI thành công và kiểm tra trực quan ảnh chú thích được xuất.

Các test tổng hợp bao gồm 4 góc xoay (0°, 23°, 57°, 90°), 3 phép chiếu và 2
phương pháp tách ảnh, tổng cộng 24 tổ hợp đo. Test yêu cầu sai lệch mỗi kích thước
so với hình học dựng không quá **0.8 mm**; đây chỉ là ngưỡng hồi quy phần mềm trên
ảnh raster tổng hợp. Test ánh xạ tọa độ lý tưởng dùng ngưỡng 0.0001 mm.

Còn có test bàn cờ bị che/thiếu, sản phẩm bị cắt/chạm bàn cờ, nhiều vật, hình tròn,
hình thang, nhiễu nhỏ, vật sáng trên nền tối, ảnh không hợp lệ, homography suy biến,
ngoại suy quá xa, nhánh classic và CLI với mã hóa Windows cũ.

Kết quả CLI trên ảnh tổng hợp góc 57°/phối cảnh 2: **65.139 × 35.083 mm**,
RMSE chiếu lại bàn cờ **0.115 px** trong môi trường Python 3.11.9 của dự án.
Đây là kết quả chạy thuật toán trên fixture, không phải số liệu đo vật thật.

Giới hạn còn lại:

- Không thể xác minh đồng phẳng, độ phẳng vật, độ chính xác in bàn cờ hoặc giả thiết
  không méo chỉ từ một ảnh và homography. Chưa có ước lượng độ không đảm bảo đo.
- Kích thước là hình chữ nhật bao khớp từ contour raster; chưa tinh chỉnh đường
  biên vật ở mức dưới pixel. Sai lệch phân đoạn và làm tròn pixel vẫn ảnh hưởng kết quả.
- Nền phức tạp, phản xạ mạnh, vật có lỗ/hoa văn, cạnh tròn lớn hoặc các vật chạm
  nhau chưa được bảo đảm. Nếu bộ lọc từ chối, cần cải thiện ảnh hoặc cấu hình.
- Bàn cờ rất nhỏ, phối cảnh quá xiên, góc mờ hoặc vật quá xa bàn cờ bị từ chối.
- Chưa kiểm chứng dữ liệu thực, camera, Python 3.12, dung sai hoặc lịch sử đo.

Tham khảo API chính thức: [OpenCV Camera Calibration and 3D Reconstruction](https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html).

## File tạo/sửa trong nhiệm vụ này

- [errors.py](../visiongauge/errors.py), [__main__.py](../visiongauge/__main__.py), [__init__.py](../visiongauge/__init__.py).
- [image_io/images.py](../visiongauge/image_io/images.py), [image_io/__init__.py](../visiongauge/image_io/__init__.py).
- [calibration/chessboard.py](../visiongauge/calibration/chessboard.py), [calibration/planar.py](../visiongauge/calibration/planar.py), [calibration/__init__.py](../visiongauge/calibration/__init__.py).
- [processing/contours.py](../visiongauge/processing/contours.py), [processing/__init__.py](../visiongauge/processing/__init__.py).
- [measurement/geometry.py](../visiongauge/measurement/geometry.py), [measurement/pipeline.py](../visiongauge/measurement/pipeline.py), [measurement/annotation.py](../visiongauge/measurement/annotation.py), [measurement/__init__.py](../visiongauge/measurement/__init__.py).
- [tests/__init__.py](../tests/__init__.py), [tests/synthetic.py](../tests/synthetic.py), [tests/test_image_io.py](../tests/test_image_io.py), [tests/test_chessboard.py](../tests/test_chessboard.py), [tests/test_planar.py](../tests/test_planar.py), [tests/test_measurement.py](../tests/test_measurement.py).
- [README.md](../README.md) và [tài liệu này](measurement.md).

Các PNG mẫu được sinh trong [data/synthetic/](../data/synthetic/) và ảnh chú thích
trong [reports/](../reports/); chúng được gitignore và có thể tạo lại bằng lệnh ở trên.
