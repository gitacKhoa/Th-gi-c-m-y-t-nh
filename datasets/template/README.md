# Dataset thực nghiệm — mẫu trống

Sao chép thư mục mẫu thành bộ dữ liệu riêng. Đặt ảnh trong `images/` (có thể có
thư mục con), điền [measurements.csv](measurements.csv). Mỗi ảnh là một dòng.
Không có ảnh hoặc số đo thực nghiệm giả trong mẫu này.

Các cột bắt buộc:

| Cột | Nội dung người dùng cung cấp |
| --- | --- |
| image_path | Đường dẫn ảnh tương đối so với images/, dùng `/` hoặc `\` |
| product_id | Mã mẫu vật cụ thể, giữ nguyên qua các lần chụp; phân biệt các mẫu khác nhau |
| reference_length_mm | Chiều dài thực đo bằng thước cặp, mm, > 0 |
| reference_width_mm | Chiều rộng thực đo bằng thước cặp, mm, > 0 và <= chiều dài |
| condition_id | Mã nhóm điều kiện chụp có ý nghĩa, dùng nhất quán để tổng hợp |

Các cột mô tả tùy chọn (để trống nếu chưa ghi nhận, không tự đoán):

- `camera_id`: thiết bị/lens hoặc chế độ camera.
- `lighting`: mô tả nguồn sáng, hướng sáng, phản xạ/bóng đổ.
- `view_angle_deg`: góc giữa trục nhìn camera và pháp tuyến mặt phẳng, 0–90 độ.
- `camera_distance_mm`: khoảng cách camera đến mặt phẳng đo, > 0 mm.
- `reference_instrument`: mã thước cặp và thông tin độ phân giải/hiệu chuẩn nếu có.
- `captured_at`: thời điểm chụp dạng ISO 8601 nếu biết (được lưu như văn bản).
- `notes`: độ dày vật, bố trí, nền, zoom/focus và ghi chú khác.

Ghi kích thước thực của mẫu, không dùng kích thước danh nghĩa thay số đo thước cặp.
Dùng dấu chấm thập phân; CSV UTF-8, dấu phẩy phân cách, đặt văn bản có dấu phẩy
trong dấu nháy kép. Không nhập đơn vị vào ô số. Mã có số 0 ở đầu được giữ nguyên.
Tham chiếu cũng có sai số; kết quả đánh giá là so với tham chiếu đã cung cấp.

Mỗi lần chạy dùng cùng cấu hình bàn cờ, camera calibration và cách tách biên.
Tách bộ dữ liệu nếu đổi camera, chế độ ống kính hoặc bàn cờ. Giữ bộ ảnh đánh giá
độc lập với bộ dùng hiệu chuẩn và bộ dùng điều chỉnh thuật toán.

Xem [hướng dẫn chạy và công thức](../../docs/evaluation.md).
