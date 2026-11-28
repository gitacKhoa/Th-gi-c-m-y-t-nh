# Lời thoại chi tiết — Người 1: tổng quan và demo

Tài liệu dành cho Người 1 trong [phân công báo cáo](phan_cong_bao_cao.md). Phần nói được chia làm hai lượt: mở đầu trước các phần kỹ thuật, sau đó quay lại demo và kết luận. Thời lượng gợi ý khoảng **5–6 phút**, chưa tính phần hỏi đáp.

Các nội dung trong dấu `[ngoặc vuông]` cần thay bằng thông tin thật của nhóm. Không tự điền số đo, calibration hoặc dung sai chưa kiểm chứng.

## Trước khi trình bày

Điền các thông tin sau để tránh lúng túng khi demo:

- Tên nhóm: `[tên nhóm]`
- Tên Người 2, 3, 4 để giới thiệu/chuyển phần: `[tên]`
- Mã sản phẩm trong demo: `[mã sản phẩm]`
- Bàn cờ sử dụng: `[số góc trong ngang] × [số góc trong dọc]`, cạnh ô `[giá trị] mm`
- Camera/độ phân giải đã calibration: `[camera]`, `[độ phân giải]`
- Dụng cụ đo tham chiếu và kích thước thật: `[ghi số đo thước cặp nếu có]`
- Danh nghĩa và giới hạn dung sai lấy từ đâu: `[bản vẽ/tiêu chuẩn/thông số thật]`

Chuẩn bị sẵn một ảnh demo đã kiểm tra, calibration tương ứng và một ảnh dự phòng. Mở sẵn ứng dụng ở trang **Quy trình đo**. Nếu muốn chụp trực tiếp, kiểm tra quyền camera và trình duyệt trước giờ báo cáo.

## Phần A — Mở đầu và tổng quan

### 1. Chào hỏi và giới thiệu đề tài — khoảng 20 giây

**Lời nói:**

> “Em xin chào thầy và các bạn. Nhóm em là `[tên nhóm]`. Hôm nay nhóm em trình bày dự án VisionGauge — hệ thống đo kích thước và kiểm tra dung sai sản phẩm bằng thị giác máy tính. Em là `[tên]`, phụ trách giới thiệu tổng quan và demo hệ thống.”

**Trên slide:** tên đề tài, thành viên, một ảnh minh họa đầu vào có sản phẩm và bàn cờ.

### 2. Bài toán và mục tiêu — khoảng 35 giây

**Lời nói:**

> “Trong kiểm tra sản phẩm, việc đo từng mẫu bằng tay mất thời gian và kết quả phụ thuộc thao tác. Mục tiêu của nhóm là xây dựng một ứng dụng nhận ảnh sản phẩm, xác định kích thước chiều dài và chiều rộng theo milimét, rồi so sánh với giới hạn dung sai do người dùng cung cấp. Hệ thống hướng tới sản phẩm phẳng, có biên dạng gần chữ nhật, được đặt cùng mặt phẳng với bàn cờ chuẩn.”

> “Đầu vào chính là ảnh có cả sản phẩm và bàn cờ. Cạnh ô bàn cờ phải được đo và khai báo đúng để ảnh có cơ sở quy đổi từ pixel sang mm. Đầu ra gồm kích thước, độ lệch, kết luận dung sai nếu đủ điều kiện, ảnh chú thích và bản ghi lịch sử.”

**Lưu ý:** nếu chưa có bộ số đo sản phẩm thật, nói “mục tiêu của hệ thống” chứ không nói “đã chứng minh đo chính xác”.

### 3. Phạm vi và lựa chọn kỹ thuật — khoảng 30 giây

**Lời nói:**

> “Project hiện dùng OpenCV và các phép xử lý ảnh, hình học; không huấn luyện mô hình AI và không dùng ArUco. Nhóm chọn Chessboard vì các góc trong tạo thành lưới đều, và kích thước ô thật có thể dùng làm hệ tọa độ chuẩn trên mặt phẳng.”

> “Một giả thiết quan trọng là bàn cờ và sản phẩm gần như đồng phẳng. Nếu thiếu calibration, bàn cờ không đủ góc, ảnh không đạt chất lượng hoặc phép ánh xạ không đáng tin, hệ thống phải trả về ‘Không thể đánh giá’, không tự đoán kết quả.”

### 4. Giới thiệu luồng và các trang — khoảng 30 giây

**Lời nói:**

> “Ở mức tổng quan, luồng xử lý là: ảnh được kiểm tra và khử méo theo calibration; hệ thống tìm bàn cờ để xác lập mặt phẳng mm; sau đó tách contour sản phẩm và tính kích thước; cuối cùng mới kiểm tra dung sai, hiển thị và lưu lịch sử.”

> “Trong giao diện, Camera Calibration dùng để tạo hoặc nạp thông số camera; Quy trình đo là luồng chính có kiểm tra điều kiện và lưu lịch sử; Lịch sử dùng để xem lại và xuất CSV hoặc PDF. Trang Đo kích thước được giữ để xem trước và debug thuật toán.”

### 5. Chuyển sang Người 2 — khoảng 10 giây

**Lời nói:**

> “Đó là bức tranh chung của hệ thống. Để phép đo có thể quy đổi đúng từ ảnh sang không gian thực, trước tiên cần hiệu chuẩn camera và xử lý méo ống kính. Em xin mời bạn `[tên Người 2]` trình bày phần này.”

## Phần B — Demo trực tiếp sau phần kỹ thuật

### 6. Mở đầu demo — khoảng 10 giây

**Lời nói:**

> “Cảm ơn các phần trình bày vừa rồi. Bây giờ em xin minh họa một lượt đo hoàn chỉnh. Em đã chuẩn bị calibration phù hợp với camera và độ phân giải của ảnh; trong demo này em sẽ dùng đúng cấu hình đó.”

**Thao tác:** chuyển sang trang **Quy trình đo**. Nếu calibration đã áp dụng, chỉ kiểm tra fingerprint/độ phân giải đang hiển thị; không cần chạy calibration trực tiếp trong lúc báo cáo.

### 7. Nhập cấu hình và xác nhận điều kiện — khoảng 25 giây

**Lời nói:**

> “Ở đây em khai báo đúng số góc trong của bàn cờ, cạnh ô đo thực tế, mã sản phẩm và thông số danh nghĩa/dung sai lấy từ `[nguồn thông số]`. Các giá trị này không nên đặt tùy ý vì chúng ảnh hưởng trực tiếp đến quy đổi mm và kết luận.”

> “Em xác nhận ảnh dùng đúng camera và độ phân giải đã hiệu chuẩn; bàn cờ rõ, phẳng và nằm cùng mặt phẳng với sản phẩm. Nếu những điều kiện này không đúng thì kết quả không đáng tin.”

**Thao tác:** rà lại các trường ở sidebar và thông tin sản phẩm; xác nhận checkbox điều kiện chụp. Không đọc to các giá trị nhạy cảm/không cần thiết; chỉ chỉ vào nguồn dữ liệu thật.

### 8. Chọn ảnh hoặc chụp — khoảng 20 giây

**Lời nói nếu dùng File:**

> “Để demo ổn định, em chọn ảnh đã chuẩn bị có đủ sản phẩm và bàn cờ. Khi làm thực tế, có thể chọn một ảnh hoặc một lô ảnh; các ảnh trong cùng lô phải dùng chung cấu hình sản phẩm và calibration.”

**Lời nói nếu dùng Camera:**

> “Ở nguồn Camera, em chụp ảnh sản phẩm và bàn cờ. Giao diện hiển thị độ phân giải thực của ảnh. Em có thể tải ảnh gốc và file metadata JSON để lưu làm tư liệu xây dựng dataset; ảnh tải xuống giữ nguyên dữ liệu camera trả về.”

**Thao tác:** chọn nguồn **File** hoặc **Camera**. Nếu dùng camera, có thể chỉ nhanh hai nút **Tải ảnh gốc** và **Tải metadata JSON**, nhưng không bắt buộc tải file xuống ngay trên sân khấu.

### 9. Chạy phép đo và giải thích kết quả — khoảng 40 giây

**Lời nói trước khi bấm:**

> “Em nhấn ‘Đo, kiểm tra và lưu lịch sử’. Hệ thống xử lý từng ảnh độc lập. Nếu một ảnh lỗi thì trạng thái lỗi được ghi cho ảnh đó, không biến lỗi xử lý thành kết luận sản phẩm không đạt.”

**Thao tác:** bấm nút chạy; chờ kết quả; trỏ lần lượt vào trạng thái, số đo length/width, độ lệch, ảnh chú thích và cảnh báo.

**Lời nói khi có kết quả:**

> “Kết quả của lượt này là `[đọc số đo đang hiển thị]` mm. Hệ thống so sánh số đo chưa làm tròn với khoảng dung sai đã khai báo. Kết luận đang hiển thị là `[đọc đúng trạng thái]`. Ảnh chú thích giúp đối chiếu vị trí bàn cờ và đường bao mà thuật toán dùng.”

> “Nếu kết quả là ‘Không thể đánh giá’, đây không phải là ‘Không đạt’. Nó có nghĩa là thiếu điều kiện hoặc phép đo chưa đủ tin cậy để kết luận.”

**Quan trọng:** không đổi dung sai sau khi thấy kết quả chỉ để biến trạng thái thành ĐẠT. Nếu muốn minh họa hai trạng thái, dùng sản phẩm và tiêu chuẩn thật khác nhau, hoặc chỉ giải thích trên slide bằng ví dụ giả định được ghi rõ.

### 10. Giải thích thời gian xử lý — khoảng 20 giây

**Lời nói:**

> “Mỗi lượt có trường thời gian xử lý tính bằng mili giây. Thời gian này kết thúc khi hệ thống tạo xong ảnh chú thích; không bao gồm thời gian lưu database hay xuất báo cáo. Nó cũng không phải toàn bộ thời gian từ lúc đặt vật vào camera đến lúc giao diện hiển thị xong.”

> “Ví dụ, ảnh nhóm đã chụp trước đó hiển thị 173.026 ms, tương đương khoảng 0,173 giây cho đúng lượt đó. Đây là một lần đo, chưa phải thời gian trung bình hay kết luận về real-time. Muốn báo cáo tốc độ cần đo lặp nhiều lần với cùng độ phân giải và cấu hình máy.”

**Nếu thầy hỏi hệ thống có real-time không:**

> “Hiện tại hệ thống đo ảnh tĩnh theo từng lượt; có thể xử lý một lô ảnh, nhưng chưa phải video liên tục. Project ghi thời gian xử lý cho mỗi lượt để đánh giá độ trễ thuật toán.”

### 11. Mở lịch sử và kết thúc demo — khoảng 25 giây

**Lời nói:**

> “Sau khi xử lý, lượt đo được lưu vào lịch sử cùng mã lượt, ảnh nguồn, cấu hình và calibration snapshot để có thể tra cứu lại. Em mở trang Lịch sử để xem bản ghi vừa tạo; từ đây có thể lọc và xuất CSV hoặc PDF.”

**Thao tác:** mở **Lịch sử**, tìm lượt mới nhất, chỉ vào thời gian, mã sản phẩm, trạng thái và thời gian xử lý. Nếu còn thời gian, chỉ ra chức năng xuất báo cáo; không cần mở và đọc toàn bộ file PDF.

## Phần C — Kết luận của Người 1

**Lời nói:**

> “Qua demo, nhóm đã trình bày luồng từ ảnh đầu vào đến số đo, kết luận dung sai và bản ghi có thể truy vết. Hiện các bài kiểm thử chủ yếu xác minh chức năng phần mềm bằng ảnh tổng hợp; nhóm chưa dùng một bộ dữ liệu sản phẩm thật kèm số đo thước cặp để khẳng định độ chính xác thực nghiệm.”

> “Hướng tiếp theo là thu thập ảnh thật trong nhiều điều kiện, đo tham chiếu bằng dụng cụ phù hợp, đánh giá trên tập độc lập và báo cáo MAE, RMSE, sai số lớn nhất, tỷ lệ đo thành công cùng thời gian xử lý trung bình. Nhóm em xin hết phần trình bày và sẵn sàng trả lời câu hỏi của thầy.”

## Nếu demo gặp sự cố

| Tình huống | Cách xử lý/lời nói |
|---|---|
| Camera không mở hoặc trình duyệt chưa cấp quyền | Chuyển sang **File** và nói: “Để bảo đảm đúng pipeline, em dùng ảnh dự phòng đã chụp bằng cùng camera và calibration.” |
| Calibration không khớp độ phân giải | Không cố chạy hoặc resize ảnh để lách kiểm tra. Chuyển sang ảnh dự phòng có calibration tương ứng. |
| Không tìm thấy bàn cờ/vật | Không che giấu lỗi. Nói ngắn: “Ảnh này không đáp ứng điều kiện phát hiện nên hệ thống từ chối đánh giá”; sau đó dùng ảnh dự phòng để trình bày lượt thành công. |
| Trang chạy chậm | Trong lúc chờ, nhắc rằng bước camera/contour phụ thuộc ảnh và máy; không tự đọc một con số thời gian khi chưa xuất hiện. |
| Không truy cập được app | Dùng ảnh chụp màn hình kết quả đã lưu để giải thích giao diện, nhưng nói rõ đó là minh họa đã chuẩn bị, không phải phép đo trực tiếp tại thời điểm báo cáo. |

## Nhắc nhanh trước khi lên báo cáo

- Nói “thời gian xử lý ảnh” thay vì “thời gian thực từ lúc đưa vật vào”.
- `173.026 ms` chỉ là một kết quả mẫu; không gọi là trung bình hoặc FPS.
- Reprojection RMS theo pixel không phải sai số kích thước theo mm.
- Không nói “đã đạt độ chính xác X” nếu chưa có phép đo đối chiếu trên dữ liệu thật.
- Nếu không đủ điều kiện đo, giải thích đúng trạng thái **KHÔNG THỂ ĐÁNH GIÁ**.
- Chỉ demo cấu hình, kích thước và dung sai có nguồn rõ ràng.

