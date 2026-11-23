# Đánh giá độ chính xác — nhiệm vụ 5

Module [evaluation/](../visiongauge/evaluation/) chạy độc lập với Streamlit và dùng
lại pipeline đo hiện có. Chưa có bộ dữ liệu thực nghiệm được cung cấp cho nhiệm vụ
này; không có kết luận về sai số thực tế hoặc mức cải thiện độ chính xác.

## Dataset và dữ liệu tham chiếu

Sao chép [mẫu trống](../datasets/template/) thành một bộ dữ liệu riêng:

```text
datasets/my_experiment/
  measurements.csv       # Người dùng điền dữ liệu thực
  camera.json            # Calibration đã lưu, nếu dùng ảnh thô
  images/
    ...                  # Ảnh sản phẩm + bàn cờ, có thể chia thư mục con
```

CSV mẫu chỉ có tiêu đề. Đọc [mô tả các cột](../datasets/template/README.md) trước
khi nhập dữ liệu. Mỗi ảnh có một đường dẫn, mã mẫu sản phẩm cụ thể, kích thước
thước cặp và `condition_id`. Cạnh dài được gọi là length, cạnh ngắn là width;
không phụ thuộc hướng xoay của vật trong ảnh. Giữ số 0 đầu mã sản phẩm.

Các cột tùy chọn ghi camera, ánh sáng, góc chụp, khoảng cách, dụng cụ tham chiếu,
thời điểm và ghi chú. Các ảnh cùng `condition_id` phải thuộc cùng nhóm điều kiện
mà bạn muốn so sánh; phần mềm không tự suy đoán điều kiện từ ảnh. Không cần điền
số cho điều kiện chưa đo được. Cấu hình bàn cờ/camera dùng chung cho một lần chạy;
tách thành nhiều lần chạy nếu đổi camera/calibration hoặc bàn cờ.

Đường dẫn ảnh tương đối với thư mục `images`, hỗ trợ Unicode và dấu `/` hoặc `\`.
CSV UTF-8 (có hoặc không BOM), dấu phẩy phân cách, dấu chấm thập phân. Tên cột,
cột bắt buộc, kích thước hữu hạn > 0, length >= width và đường dẫn không trùng
được kiểm tra trước khi chạy. Lỗi cấu trúc/tham chiếu CSV dừng toàn bộ lần chạy
để người dùng sửa, không tự thay giá trị hoặc bỏ dòng. Không đọc đường dẫn vượt
ra ngoài thư mục ảnh, kể cả liên kết trỏ ra ngoài.

## Chạy hàng loạt trên Windows

Từ thư mục gốc dự án, sau khi đã điền CSV và cung cấp ảnh/calibration:

```powershell
.\.venv\Scripts\python.exe -m visiongauge.evaluation `
  --images "datasets/my_experiment/images" `
  --metadata "datasets/my_experiment/measurements.csv" `
  --calibration "datasets/my_experiment/camera.json" `
  --columns 8 --rows 5 --square-size-mm 29 `
  --segmentation canny `
  --output "reports/evaluation_run_01"
```

Thông số bàn cờ trong lệnh chỉ minh họa cách gọi; thay bằng số góc và kích thước ô
đã kiểm chứng của bộ ảnh. `my_experiment` không phải dataset có sẵn. Mỗi lần chạy
dùng thư mục output mới hoặc rỗng, nằm ngoài thư mục ảnh; không ghi đè báo cáo cũ.

Chọn đúng **một** trong hai cách:

- `--calibration ...`: ảnh thô, tự khử méo rồi tìm bàn cờ/contour và homography.
  Giữ cùng camera, zoom/focus, độ phân giải calibration; không tự scale K/crop.
- `--image-geometry undistorted`: ảnh đã khử méo bên ngoài hoặc ảnh tổng hợp.
  Có thể dùng `negligible_distortion` chỉ khi đã có cơ sở xác nhận méo không đáng kể.
  Không chọn tùy chọn này chỉ để vượt qua lỗi thiếu calibration.

`--segmentation` nhận `threshold` (Otsu, mặc định) hoặc `canny`. Các ảnh cùng lần
chạy dùng cùng tham số để so sánh nhất quán. Xem `--help` để biết các tùy chọn.
Không thay đổi thuật toán đo, không hiệu chỉnh kết quả bằng số đo tham chiếu.

Quét đệ quy ảnh PNG/JPEG/BMP/TIFF/WebP trong thư mục. Ảnh chưa có dòng CSV vẫn
được đưa vào báo cáo với trạng thái thiếu metadata và không đo khi thiếu tham chiếu.
Ảnh được khai báo nhưng thiếu file cũng được ghi rõ. Các file không phải định dạng
ảnh được hỗ trợ không thuộc tập đánh giá.

## Công thức và cách tính mẫu

Với từng chiều, gọi `r_i` là kích thước thước cặp > 0 (mm), `m_i` là kết quả đo
(mm), `n` là số ảnh đo thành công:

| Đại lượng | Công thức | Đơn vị |
| --- | --- | --- |
| Sai số có dấu | `e_i = m_i - r_i` | mm |
| Sai số tuyệt đối | `a_i = abs(e_i)` | mm |
| Sai số tương đối tuyệt đối | `p_i = 100 * a_i / r_i` | % |
| Sai số có dấu trung bình | `mean_error = sum(e_i) / n` | mm |
| MAE | `sum(a_i) / n` | mm |
| RMSE | `sqrt(sum(e_i**2) / n)` | mm |
| Sai số tuyệt đối lớn nhất | `max(a_i)` | mm |
| MAPE | `sum(p_i) / n` | % |
| Tỷ lệ đo thành công | `100 * số ảnh thành công / tổng số ảnh trong báo cáo` | % |

Tính chiều dài và chiều rộng riêng, không gộp hai chiều làm một chỉ số. Một ảnh
thành công là một mẫu có trọng số bằng nhau; nhóm có nhiều ảnh đóng góp nhiều mẫu
hơn. Tổng thể được tính từ từng ảnh, không lấy trung bình không trọng số của MAE
các nhóm. Không suy diễn các lần chụp cùng vật là các mẫu vật độc lập.

Ảnh thất bại không tham gia MAE/RMSE và không nhận sai số 0. Nếu `n = 0`, các chỉ
số sai số là NaN trong API và ô trống trong CSV. Luôn đọc chúng cùng tổng số ảnh,
số thành công, số thất bại và tỷ lệ thành công. Khi tập đầu vào rỗng, CSV bị từ chối;
API thống kê riêng hỗ trợ tập rỗng với `n = 0` và tỷ lệ thành công NaN.

Sai số so với thước cặp không phải độ không đảm bảo đo; chưa có phân tích sai số
dụng cụ tham chiếu, khoảng tin cậy hay chứng nhận đo lường. Không tự kết luận
ĐẠT/KHÔNG ĐẠT hoặc đạt mục tiêu 1 mm. Dùng tập đánh giá độc lập với tập hiệu chuẩn
và tập đã dùng điều chỉnh thuật toán, ghi rõ số ảnh và điều kiện thử nghiệm.

## Báo cáo đầu ra

| File | Nội dung |
| --- | --- |
| `results.csv` | Tất cả ảnh, metadata, số đo, sai số, trạng thái và lỗi |
| `failed_images.csv` | Các ảnh `failed` hoặc `missing_metadata`, không bỏ âm thầm |
| `overall.csv` | Thống kê toàn bộ, hai dòng cho length/width |
| `by_product.csv` | Theo mã mẫu sản phẩm |
| `by_condition.csv` | Theo mã điều kiện chụp |
| `by_product_condition.csv` | Theo cặp sản phẩm và điều kiện |
| `reference_vs_measured.png` | Hai biểu đồ scatter tham chiếu/đo, đường `y=x`, số ảnh bị loại |
| `run_metadata.json` | Thời gian UTC, phiên bản thư viện, cấu hình, calibration ID, hash CSV |

Mỗi ảnh có SHA-256 khi đọc được bytes để đối chiếu dữ liệu; kích thước pixel,
RMSE ánh xạ bàn cờ và cảnh báo pipeline cũng được lưu. `board_rmse_px` không phải
sai số đo mm. CSV dùng UTF-8 BOM để đọc tiếng Việt trong Excel; ô trống chỉ số là
không có kết quả, không phải 0. Biểu đồ chỉ chứa ảnh thành công; nếu tất cả thất bại
thì biểu đồ ghi rõ không có phép đo thành công. `condition_id`/`product_id` trống
trong nhóm thiếu metadata thể hiện các ảnh chưa được người dùng khai báo.

Mã thoát CLI: `0` = mọi ảnh đo được; `1` = có ảnh thất bại/thiếu metadata nhưng
vẫn xuất báo cáo; `2` = cấu hình/dataset hoặc xuất báo cáo lỗi. Mã `0` không nói
rằng sai số nhỏ hay sản phẩm nằm trong dung sai.

## API và kiểm thử

API: `evaluate_dataset(...)` trả `EvaluationReport` gồm `results`, `summaries`
và `metadata`; `export_report(report, output_dir)` xuất báo cáo. Các hàm thống kê
không phụ thuộc OpenCV/Streamlit và được kiểm tra bằng số tính tay.

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_evaluation_metrics.py tests/test_evaluation_dataset.py tests/test_evaluation_batch.py
.\.venv\Scripts\python.exe -m pytest -q
```

Test có sai số dương/âm/0, một mẫu, tập rỗng, NaN/vô cực, kích thước không hợp lệ,
RMSE số lớn; tổng hợp nhóm có số lượng mẫu khác nhau và nhóm toàn thất bại. Test
tích hợp dùng ảnh **tổng hợp trong thư mục tạm** để kiểm tra pipeline thật, CSV,
biểu đồ, metadata, calibration và CLI với đường dẫn tiếng Việt. Không lưu kết quả
test thành báo cáo thực nghiệm thật.

Kết quả kiểm thử nhiệm vụ 5 trên Windows/Python 3.11.9: **54 test mới đạt**;
toàn dự án **271 test đạt** trong 28,76 giây. Editor không báo lỗi. Biểu đồ test
đã được kiểm tra trực quan. Chưa chạy đánh giá trên dataset thực nghiệm vì chưa
có ảnh và số đo tham chiếu thực được cung cấp cho nhiệm vụ này.

## File tạo/sửa

- Lõi mới: [dataset.py](../visiongauge/evaluation/dataset.py),
  [metrics.py](../visiongauge/evaluation/metrics.py), [summary.py](../visiongauge/evaluation/summary.py),
  [batch.py](../visiongauge/evaluation/batch.py).
- Báo cáo/CLI: [plots.py](../visiongauge/evaluation/plots.py),
  [reporting.py](../visiongauge/evaluation/reporting.py),
  [__init__.py](../visiongauge/evaluation/__init__.py), [__main__.py](../visiongauge/evaluation/__main__.py).
- Mẫu: [measurements.csv](../datasets/template/measurements.csv),
  [README dataset](../datasets/template/README.md), thư mục ảnh trống.
- Test: [test_evaluation_metrics.py](../tests/test_evaluation_metrics.py),
  [test_evaluation_dataset.py](../tests/test_evaluation_dataset.py),
  [test_evaluation_batch.py](../tests/test_evaluation_batch.py).
- Cập nhật [README](../README.md) và [phiên bản](../visiongauge/__init__.py).
