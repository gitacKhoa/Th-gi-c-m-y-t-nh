# Giao diện đo — nhiệm vụ 3

Nhiệm vụ 7 bổ sung **Quy trình đo** (calibration bắt buộc, lô ảnh/camera, chất
lượng, dung sai và lưu tự động) cùng **Lịch sử** (xem lại, thống kê, PDF/CSV).
Xem [hướng dẫn full flow](full_flow.md). Trang **Đo kích thước** mô tả dưới đây
được giữ cho xem trước/debug.

Chạy từ thư mục gốc:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Chọn **Đo kích thước** trong thanh bên. Upload một ảnh 8-bit hoặc chọn **Chụp
camera** để chụp ảnh tĩnh. Trình duyệt cần quyền camera và môi trường localhost
hoặc HTTPS; nếu thiết bị không khả dụng, dùng upload. File tối đa 20 MB.

Nhập số góc trong ngang/dọc và cạnh ô vuông thực tế. Nút **Phát hiện bàn cờ**
hiển thị các góc; nút **Bắt đầu đo** cũng có thể tự phát hiện trước khi đo.
Chọn điều kiện méo ảnh hoặc [calibration đang áp dụng](camera_calibration.md).
Ảnh gốc/kết quả hiển thị cạnh nhau, kích thước tính bằng mm, tải kết quả dưới dạng PNG.

Bật **Kiểm tra dung sai** ở thanh bên để nhập danh nghĩa và sai lệch có dấu cho
từng chiều. [Kết luận dung sai](tolerance.md) tự cập nhật theo số đo hiện tại;
phép đo thất bại/thiếu cấu hình không được coi là ĐẠT. Bảng chỉ rõ giới hạn,
độ lệch và chiều vượt dung sai. Cấu hình dung sai được giữ khi chuyển trang trong
phiên; kết luận không được tái sử dụng nếu ảnh hoặc phép đo đã thay đổi.

Thiết kế nền trắng/trung tính dùng [.streamlit/config.toml](../.streamlit/config.toml).
Các cột xếp dọc ở màn hình hẹp. Phần debug hiển thị grayscale, Gaussian Blur,
góc bàn cờ, mask và homography; khi đo thất bại nhưng vẫn tìm được bàn cờ, có thể
xem mask để tìm nguyên nhân. Ảnh đã khử méo cũng hiển thị khi có calibration.

Trạng thái nằm trong từng phiên; không lưu ảnh người dùng lên thư mục dự án.
Đổi ảnh, nguồn ảnh, cấu hình, phương pháp tách biên hoặc calibration sẽ xóa số đo,
ảnh kết quả và bytes tải xuống cũ. Đổi cách xem debug không tính lại phép đo.
Nạp lại trang/đổi trang có thể cần upload lại ảnh; lưu JSON calibration để tái sử dụng.

Thuật toán đo nằm riêng trong [measurement/](../visiongauge/measurement/).
Phần giao diện gồm [app.py](../visiongauge/ui/app.py),
[workflow.py](../visiongauge/ui/workflow.py) và [views.py](../visiongauge/ui/views.py).
Kiểm thử bằng [test_app.py](../tests/test_app.py) và
[test_ui_workflow.py](../tests/test_ui_workflow.py) dùng widget upload/camera thật
của AppTest và pipeline thật; ảnh camera trong test là JPEG tổng hợp, không phải
kiểm thử camera vật lý. Các test PNG kiểm tra bytes tải xuống bằng cách giải mã
và đối chiếu với ảnh được chú thích trong kết quả.
