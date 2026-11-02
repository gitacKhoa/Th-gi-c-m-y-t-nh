# VisionGauge

Hệ thống đo kích thước và kiểm tra dung sai sản phẩm bằng thị giác không tiếp xúc.
Mẫu hiệu chuẩn duy nhất là **Chessboard/Checkerboard**; không sử dụng ArUco.

## Trạng thái hiện tại — nhiệm vụ 4

Đã có pipeline OpenCV độc lập với Streamlit: đọc/kiểm tra ảnh, tìm góc bàn cờ,
kiểm tra homography, tách contours và đo chiều dài/chiều rộng trong mặt phẳng mm.
Có CLI, ảnh chú thích và test hình học tổng hợp. Xem [hướng dẫn đo](docs/measurement.md).

Giao diện đã hỗ trợ upload/chụp ảnh, phát hiện bàn cờ, đo, xem debug và tải PNG.
Trang **Camera Calibration** hỗ trợ nhiều ảnh, camera matrix, 5 hệ số méo,
rvec/tvec, reprojection error, lưu/nạp JSON và áp dụng khử méo trước khi đo.
Có thể chụp liên tiếp ảnh Chessboard bằng camera ngay trên trang hiệu chuẩn,
xem/xóa ảnh đã thêm và tải cả bộ ảnh JPEG dưới dạng ZIP.
Có bảng so sánh trước/sau trên cùng bộ ảnh và CSV tham chiếu tùy chọn.
Xem [hướng dẫn giao diện](docs/ui.md) và [camera calibration](docs/camera_calibration.md).

Chưa triển khai phân loại dung sai, lưu lịch sử CSV/SQLite hoặc báo cáo nghiệp vụ.
Chưa có dữ liệu thực nghiệm để kết luận độ chính xác hoặc mức cải thiện sau hiệu chuẩn.

## Cài đặt trên Windows (PowerShell)

Yêu cầu Python **3.11 hoặc 3.12** 64-bit. Mở terminal tại thư mục dự án.
Chọn một trong hai phiên bản để tạo môi trường (ví dụ dưới dùng 3.11):

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Nếu dùng Python 3.12, thay `py -3.11` bằng `py -3.12`.
Nếu chưa có Python Launcher (`py`), dùng đường dẫn đầy đủ tới Python đã cài.
Không tạo đè một môi trường đang dùng phiên bản Python khác.

Các lệnh dùng trực tiếp interpreter trong môi trường, nên không cần kích hoạt
hoặc thay đổi Execution Policy của PowerShell. Kích hoạt là tùy chọn:

```powershell
.\.venv\Scripts\Activate.ps1
```

Trong VS Code, chọn **Python: Select Interpreter**, sau đó chọn interpreter
trong môi trường dự án. Nếu có môi trường cũ được giữ lại ở
[.venv-py313-backup/](.venv-py313-backup/), đó là bản dự phòng, không dùng để chạy dự án.

## Chạy giao diện

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Mở địa chỉ được Streamlit in ra, thường là http://localhost:8501.
Dừng bằng `Ctrl+C`. Có thể dùng tác vụ **VisionGauge: Run Streamlit** của VS Code.
Trong thanh bên, chọn **Đo kích thước** hoặc **Camera Calibration**.
Upload ảnh/chụp camera, nhập đúng số góc trong và cạnh ô, chọn điều kiện méo ảnh,
sau đó phát hiện bàn cờ hoặc bắt đầu đo. Với camera đã hiệu chuẩn, chọn
**Dùng calibration đang áp dụng**; phần mềm tự khử méo trước pipeline đo.
Kết quả cũ được xóa khi thay ảnh, cấu hình hoặc calibration. JSON được lưu qua
nút tải xuống; calibration đang áp dụng chỉ tồn tại trong phiên trình duyệt.

## Kiến trúc và hướng phụ thuộc

[app.py](app.py) gọi lớp giao diện; giao diện sẽ điều phối các module nghiệp vụ.
Các module nghiệp vụ không phụ thuộc Streamlit. Cấu hình dùng chung nằm ở
[visiongauge/config.py](visiongauge/config.py).

| Đường dẫn | Trách nhiệm | Trạng thái |
| --- | --- | --- |
| [visiongauge/image_io/](visiongauge/image_io/) | Đọc file/bytes, kiểm tra ảnh đầu vào | Đã có; ảnh chụp qua widget camera |
| [visiongauge/calibration/](visiongauge/calibration/) | Bàn cờ, nội tham, khử méo, JSON và homography | Đã có |
| [visiongauge/processing/](visiongauge/processing/) | Gaussian Blur, Otsu/Canny, loại contours bàn cờ | Đã có |
| [visiongauge/measurement/](visiongauge/measurement/) | Hình học mm, pipeline, vẽ kích thước và so sánh trước/sau | Đã có |
| [visiongauge/tolerance/](visiongauge/tolerance/) | So sánh kích thước chuẩn/dung sai, phân loại ba trạng thái | Khung module |
| [visiongauge/ui/](visiongauge/ui/) | Giao diện đo và Camera Calibration | Đã tích hợp |
| [visiongauge/storage/](visiongauge/storage/) | Lịch sử CSV/SQLite và xuất báo cáo | Khung module |
| [config/settings.toml](config/settings.toml) | Cấu hình chung | Đã có bộ đọc và kiểm tra |
| [tests/](tests/) | Kiểm thử cấu hình, dependency và giao diện | Đã có |
| [data/](data/) | Ảnh và dữ liệu hiệu chuẩn | Có thể tạo ảnh tổng hợp bằng CLI test |
| [reports/](reports/) | Ảnh chú thích và báo cáo tương lai | Có ảnh chú thích thử nghiệm tổng hợp |

Luồng dự kiến: ảnh → hiệu chỉnh méo → tìm bàn cờ/thiết lập tọa độ mm →
tách đường viền → đo → kiểm tra dung sai → hiển thị và lưu.
Hiệu chuẩn camera là luồng riêng dùng **nhiều ảnh bàn cờ** để tạo thông số camera.
Homography chỉ xử lý ánh xạ mặt phẳng/phối cảnh, không thay thế hiệu chỉnh méo.

## Cấu hình bàn cờ

Chỉnh [config/settings.toml](config/settings.toml):

```toml
[chessboard]
columns = 9
rows = 6
square_size_mm = 25.0
```

- `columns` và `rows` là **số góc trong**, mỗi giá trị là số nguyên >= 3.
- OpenCV nhận `patternSize = (columns, rows)`, không đảo thành `(rows, columns)`.
- Bàn cờ 9 × 6 góc trong tương ứng 10 × 7 ô vuông.
- `square_size_mm` là chiều dài cạnh một ô thực tế, phải hữu hạn và > 0.
- Các giá trị trên chỉ là ví dụ cấu hình, không phải dữ liệu thực nghiệm hay
  thông số camera đã hiệu chuẩn. Không suy ra tỉ lệ pixel/mm từ cấu hình này.
- Thiếu file, sai cú pháp, sai kiểu, thiếu khóa hoặc khóa không được hỗ trợ sẽ
  báo lỗi rõ ràng; giao diện dừng trước khi sử dụng cấu hình lỗi.

Phạm vi đo dự kiến: một sản phẩm chữ nhật phẳng, bàn cờ cùng mặt phẳng với sản phẩm,
đủ góc trong nhìn thấy rõ và camera gần vuông góc với mặt phẳng đo.
Thiếu dữ liệu cần thiết hoặc phép đo không đáng tin cậy phải cho trạng thái
**KHÔNG THỂ ĐÁNH GIÁ**, không tự suy ra ĐẠT/KHÔNG ĐẠT.

## Kiểm thử

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
```

Các test kiểm tra:

- Cấu hình hợp lệ, thứ tự cột/hàng, đường dẫn không phụ thuộc thư mục làm việc.
- Từ chối số góc sai kiểu, kích thước không dương/NaN/vô cực và TOML không hợp lệ.
- Import các module, thư viện cần thiết và sự hiện diện của API bàn cờ trong OpenCV.
- Khởi động Streamlit bằng `AppTest`, đổi thông số và hiển thị lỗi cấu hình.
- Phát hiện bàn cờ, tinh chỉnh góc, biến đổi tọa độ và từ chối homography không tin cậy.
- Đo vật 65 × 35 mm trong ảnh tổng hợp với 4 góc xoay, 3 phép chiếu và Otsu/Canny.
- Bàn cờ bị che/thiếu, sản phẩm bị cắt mép/chạm bàn cờ, vật không chữ nhật,
  nhiều vật, nhiễu, ảnh hỏng và đầu ra tiếng Việt qua CLI Windows.
- Upload/camera bằng Streamlit AppTest, tải PNG và xóa kết quả cũ khi đầu vào đổi.
- Hiệu chuẩn từ tọa độ và ảnh tổng hợp có camera biết trước, JSON không hợp lệ,
  thiếu ảnh, thiếu đa dạng góc chụp, độ phân giải sai, nhất quán tọa độ khử méo.
- So sánh theo cặp, không tính độ chính xác khi thiếu số đo tham chiếu.

Các test không cần camera, dữ liệu thực nghiệm hoặc kết nối mạng sau khi cài thư viện.
Kiểm thử này chỉ xác minh nền tảng phần mềm, **không đánh giá độ chính xác đo**.

Kết quả nhiệm vụ 4: **208 tests passed** trên Windows/Python 3.11.9.
Các test gồm luồng upload → hiệu chuẩn → lưu/nạp → áp dụng → đo và so sánh
trước/sau bằng Streamlit AppTest. Chưa có dữ liệu thực để đánh giá độ chính xác.

Kết quả lịch sử sau nhiệm vụ 2: **140 tests passed** trên Windows/Python 3.11.9,
gồm 49 test nền và 91 test mới. CLI đo đã được chạy thực tế; ảnh chú thích đã được
kiểm tra trực quan. Chi tiết thuật toán, cách chạy mẫu và giới hạn nằm trong
[tài liệu nhiệm vụ 2](docs/measurement.md).

Kết quả kiểm chứng nhiệm vụ 1 trên Windows, Python 3.11.9:
**49 tests passed**; `pip check` không phát hiện dependency lỗi;
máy chủ Streamlit khởi động tại localhost và `/_stcore/health` trả về `ok`.
Các phiên bản trực tiếp được dùng: OpenCV 4.14.0.94, NumPy 2.4.6,
Streamlit 1.66.1, Pandas 2.3.3, Matplotlib 3.11.2, pytest 9.2.0.

Cấu hình chạy/test trong VS Code nằm ở [.vscode/tasks.json](.vscode/tasks.json)
và [.vscode/settings.json](.vscode/settings.json). Cấu hình pytest dùng chung nằm ở
[pyproject.toml](pyproject.toml); [.gitignore](.gitignore) loại trừ môi trường,
cache và dữ liệu phát sinh khỏi quản lý mã nguồn.

## Thư viện và lưu ý

[requirements.txt](requirements.txt) khai báo các khoảng phiên bản dependency.
Streamlit tối thiểu 1.66.1 để dùng giao diện và kiểm thử upload/camera đã được xác minh.
Chỉ dùng `opencv-python-headless` vì giao diện hiển thị ảnh sẽ do Streamlit đảm nhiệm;
không dùng `cv2.imshow`. Bản này vẫn có API bàn cờ và camera `VideoCapture`.
Không cài đồng thời nhiều biến thể OpenCV trong cùng môi trường.
CSV và SQLite có sẵn trong thư viện chuẩn Python; chưa tạo database ở giai đoạn này.

Đã kiểm thử thuật toán bằng ảnh tổng hợp; chưa có kiểm thử camera hoặc dữ liệu
sản phẩm thực tế. Python 3.12 là
phiên bản mục tiêu; cần chạy lại bộ test trên interpreter 3.12 trước khi xác nhận
tương thích thực tế. Không có tuyên bố về sai số hoặc độ chính xác của hệ thống.
