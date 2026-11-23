# Quy trình đo đầy đủ - nhiệm vụ 7

Luồng sử dụng **Chessboard/Checkerboard**, không có ArUco hoặc mô hình AI.
Ảnh do người dùng cung cấp là nguồn duy nhất của số đo. Không có số đo mẫu,
calibration mặc định, hoặc nhánh dự phòng lấy kết quả mô phỏng trong ứng dụng.

## Chạy trên Windows

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

1. Chọn **Camera Calibration** để tạo/nạp và áp dụng calibration, hoặc nạp
   JSON trực tiếp trong **Quy trình đo**. Phải đúng camera, chế độ độ phân giải,
   zoom và focus của ảnh nguồn.
2. Chọn **Quy trình đo**. Nhập số góc trong ngang/dọc, cạnh ô mm, mã sản phẩm,
   chiều dài/rộng danh nghĩa và sai lệch dưới/trên có dấu. Không tự đặt kích
   thước danh nghĩa hoặc dung sai mặc định.
3. Xác nhận điều kiện chụp: bàn cờ đúng kích thước, đủ góc thấy rõ, bàn cờ và
   sản phẩm phẳng, đồng phẳng, cùng thiết lập camera đã hiệu chuẩn.
4. Chọn **File** để tải một/nhiều ảnh hoặc **Camera** để chụp một ảnh. Nhấn
   **Đo, kiểm tra và lưu lịch sử**. Chụp tiếp bằng cách xóa/chụp lại ảnh trên
   widget và nhấn đo lần nữa; mỗi thao tác đo tạo UUID mới.
5. Xem ảnh gốc, ảnh đã khử méo có chú thích, số đo, độ lệch từng chiều, kết luận,
   cảnh báo và các bước đã hoàn thành. Lỗi một ảnh không dừng các ảnh còn lại.
6. Chọn **Lịch sử** để lọc mã sản phẩm, kết luận, ngày UTC; xem chi tiết, tải ảnh
   và cấu hình JSON; xuất CSV/PDF. PDF chi tiết có ảnh chú thích; PDF theo bộ
   lọc gồm thống kê và chi tiết các lượt, không nhúng mọi ảnh.

Một lô dùng chung mã sản phẩm, tiêu chuẩn, bàn cờ và calibration; tối đa 50 ảnh,
100 MB tổng, mỗi ảnh tối đa 20 MB. Chia lô khác nếu cấu hình khác nhau.
Camera yêu cầu chế độ 480p/720p/1080p phù hợp; kích thước ảnh thực vẫn được kiểm
tra, không resize/crop để ép khớp calibration.

Trang **Đo kích thước** cũ được giữ cho xem trước/debug thuật toán. Dùng trang
**Quy trình đo** cho luồng có calibration bắt buộc và lịch sử; các xác nhận
"méo không đáng kể" ở trang debug không được dùng để bỏ qua bước này.

## Thứ tự và điều kiện bắt buộc

```text
Ảnh nguồn -> giải mã -> kiểm tra cấu hình
          -> calibration hợp lệ và đúng độ phân giải -> khử méo với K gốc
          -> xác nhận điều kiện chụp -> sàng lọc chất lượng
          -> Chessboard -> homography -> contour -> hình học mm
          -> dung sai -> ảnh chú thích -> SQLite -> lịch sử / PDF / CSV
```

- Không có calibration: **KHÔNG THỂ ĐÁNH GIÁ**, không gọi thuật toán đo.
- Calibration có RMS tổng > 1 px hoặc RMS ảnh bất kỳ > 2 px: từ chối áp dụng,
  cùng ngưỡng với trang Camera Calibration. RMS không chứng minh độ chính xác mm.
- JSON tải lên bị lỗi: báo lỗi, không quay về calibration cũ.
- Homography luôn xây dựng trên ảnh **sau khử méo** trong luồng đầy đủ.
- Chỉ kết luận đạt/không đạt nếu toàn bộ bước bắt buộc thành công và cả hai
  kích thước hữu hạn, dương, chiều dài >= chiều rộng.
- Bằng giới hạn được tính là đạt, dùng số đo chưa làm tròn. Quy tắc vẫn là
  `inclusive_limits_v1`; chưa áp dụng độ không đảm bảo đo hoặc guard band.

## Sàng lọc chất lượng và cảnh báo

Ngưỡng mặc định có thể điều chỉnh ở sidebar:

| Kiểm tra | Giá trị | Hành vi |
| --- | --- | --- |
| Variance Laplacian toàn ảnh sau khử méo | >= 20 | Dưới ngưỡng: từ chối vì thiếu nét |
| Tương phản P95-P05 grayscale | >= 20 | Dưới ngưỡng: từ chối vì tương phản thấp |
| Độ nét gần ngưỡng | < 2 lần ngưỡng tối thiểu | Cảnh báo |
| RMS homography gần ngưỡng | >= 80% ngưỡng loại hiện có | Cảnh báo |
| Khoảng cách tới giới hạn dung sai gần nhất | <= 0.2 mm mặc định | Cảnh báo từng chiều, kể cả phía ngoài giới hạn |

Các ngưỡng ảnh là heuristic sàng lọc, cần xác minh trên bộ ảnh thực. Điểm toàn
ảnh không bảo đảm vùng sản phẩm luôn nét. Bóng/phản xạ, bề mặt cong, không đồng
phẳng hoặc sai camera có thể không được phát hiện tự động. Người vận hành
vẫn phải bảo đảm điều kiện chụp và đối chiếu dụng cụ tham chiếu.

Cảnh báo gần giới hạn **không thay đổi kết luận**, không cộng trừ dung sai và
không phải độ không đảm bảo đo. Lỗi hình học không tin cậy bị chặn bởi các kiểm
tra homography/contour/rectangle hiện có.

## Trạng thái và lỗi

Kết luận sản phẩm và trạng thái xử lý là hai trường riêng:

- `COMPLETED`: xử lý xong; sản phẩm có thể ĐẠT hoặc KHÔNG ĐẠT.
- `REJECTED`: đầu vào/điều kiện không đáp ứng; KHÔNG THỂ ĐÁNH GIÁ.
- `ERROR`: lỗi nội bộ bất ngờ; KHÔNG THỂ ĐÁNH GIÁ, tra log theo mã lượt đo.

| Mã lỗi | Ý nghĩa |
| --- | --- |
| `INVALID_IMAGE` | Ảnh trống/hỏng/không hỗ trợ/vượt dung lượng |
| `INVALID_CONFIGURATION` | Thiếu mã sản phẩm, tiêu chuẩn/dung sai hoặc cấu hình không hợp lệ |
| `MISSING_CALIBRATION` | Chưa có calibration |
| `INVALID_CALIBRATION` | JSON, mô hình hoặc chất lượng calibration không hợp lệ |
| `RESOLUTION_MISMATCH` | Độ phân giải ảnh và calibration không khớp |
| `CONDITIONS_UNCONFIRMED` | Chưa xác nhận điều kiện chụp |
| `IMAGE_QUALITY` | Không qua ngưỡng nét/tương phản |
| `CHESSBOARD_NOT_FOUND` | Không đủ góc trong bàn cờ |
| `PRODUCT_NOT_FOUND` | Không có sản phẩm chữ nhật phù hợp |
| `AMBIGUOUS_PRODUCT` | Nhiều sản phẩm ứng viên |
| `UNRELIABLE_MAPPING` | Homography không đáng tin cậy |
| `UNRELIABLE_MEASUREMENT` | Hình học/số đo không đáng tin cậy |
| `PROCESSING_ERROR` | OpenCV hoặc tạo ảnh chú thích thất bại |
| `INTERNAL_ERROR` | Lỗi nội bộ/tài nguyên bất ngờ; chi tiết trong log |

`error_stage` xác định bước dừng; `stages_completed` ghi các bước đã hoàn thành.
Lỗi lưu/đọc SQLite và xuất PDF hiển thị riêng trên giao diện, không đổi một
phép đo hợp lệ thành sản phẩm KHÔNG ĐẠT hoặc thông báo lưu thành công giả.

## Lịch sử và tính truy vết

Mặc định: `data/history.sqlite3`, tạo khi sử dụng lịch sử. Có thể đặt vị trí khác:

```powershell
$env:VISIONGAUGE_HISTORY_DB = 'D:\VisionGaugeData\history.sqlite3'
```

Mỗi bản ghi chứa UUID, mã sản phẩm, tên/nguồn ảnh, SHA-256 ảnh gốc, thời gian bắt
đầu/kết thúc UTC, thời gian xử lý ms, phiên bản ứng dụng, trạng thái/lỗi, số đo,
các góc sản phẩm/homography, điểm chất lượng, dung sai và cảnh báo. Calibration
đầy đủ và fingerprint được lưu cùng cấu hình tại thời điểm đo. Ảnh nguồn và
PNG kết quả là BLOB trong cùng giao dịch SQLite với JSON kết quả.

Thời gian xử lý tính đến khi tạo ảnh chú thích, không gồm lưu DB/xuất báo cáo.
Ảnh lỗi vẫn lưu byte nguồn; không tạo ảnh kết quả hoặc số đo giả. Đổi cấu hình
hiện tại không đánh giá lại lịch sử đã lưu. Cấu hình được lưu cả khi giải mã
ảnh lỗi để truy vết yêu cầu, không chứng tỏ các bước calibration/đo đã chạy.

Lưu lại cùng UUID/nội dung không tạo bản ghi trùng; cùng UUID khác nội dung bị
từ chối. Đo lại cùng file bằng nút đo tạo UUID mới. Đổi đầu vào/cấu hình ẩn kết
quả cũ khỏi vùng kết quả hiện tại; vẫn có thể xem trong lịch sử nếu đã lưu.

Nếu lưu thất bại, giữ bản ghi chưa lưu trong phiên và hiển thị nút **Thử lưu
lại lịch sử**. Không chạy lô mới khi còn lượt chưa lưu. Thử lại chỉ lưu, không
đo lại. Đóng tab/server trước khi lưu thành công sẽ mất bản ghi chưa lưu.
Các lượt đã commit vẫn còn; chưa hỗ trợ phục hồi lượt đang tính khi tiến trình
bị tắt đột ngột. Chưa sửa/xóa lịch sử qua giao diện ở giai đoạn này.

Lịch sử dùng chung cho các phiên trên cùng máy chủ/đường dẫn DB; chưa có tài
khoản/phân quyền hay đồng bộ nhiều máy. Sao lưu DB khi ứng dụng đã dừng để có
bản sao nhất quán. Ảnh làm DB tăng dung lượng theo số lượt; chưa tự xóa dữ liệu.

CSV UTF-8 BOM hỗ trợ Excel/tiếng Việt, gồm mọi bản ghi khớp bộ lọc, giữ lỗi và
cột số đo trống khi không đo được; chứa snapshot cấu hình/calibration JSON.
Tên ảnh/mã sản phẩm bắt đầu bằng ký tự công thức Excel được thêm dấu nháy đơn
trong CSV; JSON trong lịch sử giữ nguyên giá trị gốc.

Bảng hiển thị 200 lượt mới nhất trong bộ lọc. PDF giới hạn 200 lượt/báo cáo;
CSV không giới hạn theo số hàng hiển thị. PDF nhúng font Unicode từ Matplotlib,
không cần cài font riêng trên Windows. UI chỉ xuất báo cáo từ lịch sử đã lưu.

## Kiểm thử và giới hạn xác minh

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_full_flow.py tests/test_history_reports.py tests/test_full_flow_app.py
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
```

Kết quả: **398 tests passed** trên Windows/Python 3.11.9, gồm **55 test mới**.
Test thực sự gọi phát hiện góc, `calibrateCamera`, lưu/nạp JSON, khử méo,
homography, đo, dung sai, SQLite và xuất báo cáo. AppTest kiểm tra upload lô,
chụp JPEG liên tiếp, lỗi calibration, ẩn kết quả cũ, xem lại bằng phiên mới,
retry lưu và vô hiệu hóa PDF cũ khi bộ lọc đổi. PDF kiểm thử 4 trang đã render
và kiểm tra trực quan tiếng Việt, bảng, ảnh và phân trang.

Ảnh/camera chuẩn trong test là **fixture tổng hợp để kiểm thử phần mềm**, không
phải dữ liệu thực nghiệm. Test dùng DB tạm riêng, không ghi lịch sử sản xuất.
Chưa có bộ ảnh sản phẩm thực kèm số đo thước cặp để nghiệm thu độ chính xác.
Python 3.12 và camera vật lý chưa được kiểm thử trong nhiệm vụ này.

Tái lập kiểm tra PDF trực quan:

```powershell
.\.venv\Scripts\python.exe -m tests.render_report_fixture --output tmp/pdfs
```

Lệnh tạo PDF/PNG **chỉ kiểm thử**, không ghi lịch sử. PDF render bằng PDFium độc
lập với ReportLab; pypdf kiểm tra nội dung. Không dùng chúng làm báo cáo đo thực.
Môi trường đã gặp lỗi cấp phát bộ nhớ OpenBLAS/OpenCL khi chạy kiểm thử. Bộ
test đầy đủ đạt khi giới hạn luồng; render PDF đạt bằng CPU. Nếu gặp lỗi tương tự,
đặt các biến sau trong terminal kiểm thử (không thay đổi thuật toán hoặc số đo):

```powershell
$env:OPENBLAS_NUM_THREADS = '1'
$env:OMP_NUM_THREADS = '1'
$env:OPENCV_OPENCL_RUNTIME = 'disabled'
```

## File tạo/sửa

- Điều phối: [models.py](../visiongauge/workflow/models.py), [quality.py](../visiongauge/workflow/quality.py),
  [service.py](../visiongauge/workflow/service.py), [__init__.py](../visiongauge/workflow/__init__.py).
- Lưu trữ: [history.py](../visiongauge/storage/history.py), [__init__.py](../visiongauge/storage/__init__.py).
- Báo cáo: [csv_report.py](../visiongauge/reporting/csv_report.py), [pdf_report.py](../visiongauge/reporting/pdf_report.py),
  [__init__.py](../visiongauge/reporting/__init__.py).
- UI: [inspection_page.py](../visiongauge/ui/inspection_page.py), [history_page.py](../visiongauge/ui/history_page.py),
  [run_views.py](../visiongauge/ui/run_views.py), [app.py](../visiongauge/ui/app.py), [tolerance_panel.py](../visiongauge/ui/tolerance_panel.py).
- Tests: [test_full_flow.py](../tests/test_full_flow.py), [test_history_reports.py](../tests/test_history_reports.py),
  [test_full_flow_app.py](../tests/test_full_flow_app.py), [render_report_fixture.py](../tests/render_report_fixture.py).
- Khác: [requirements.txt](../requirements.txt), [phiên bản](../visiongauge/__init__.py),
  [README.md](../README.md), [ui.md](ui.md), [.gitignore](../.gitignore), và tài liệu này.
