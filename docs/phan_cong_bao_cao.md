# Phân công học và báo cáo dự án VisionGauge

## 1. Mục tiêu và cách dùng tài liệu

Tài liệu này chia phần chuẩn bị cho nhóm **4 người**. Thay “Người 1–4” bằng tên thành viên. Người 1 phụ trách tổng quan và demo; Người 2–4 đi sâu vào các nhóm kỹ thuật.

Tên đề tài có thể trình bày: **VisionGauge — đo kích thước sản phẩm không tiếp xúc và kiểm tra dung sai bằng thị giác máy tính**.

Thông điệp thống nhất của nhóm:

> Đây là ứng dụng thị giác máy tính truyền thống dùng OpenCV, bàn cờ Chessboard/Checkerboard và hình học mặt phẳng. Project hiện không dùng mô hình AI/ML, không dùng ArUco, và chưa có kết quả thực nghiệm trên bộ sản phẩm thật để khẳng định độ chính xác đo.

Thời lượng gợi ý: **15–18 phút trình bày**, sau đó dành 3–5 phút hỏi đáp.

| Người | Phần chính | Thời lượng gợi ý |
|---|---|---:|
| Người 1 | Tổng quan, kiến trúc, demo trực tiếp, kết luận | 5 phút |
| Người 2 | Hiệu chuẩn camera và khử méo | 3–4 phút |
| Người 3 | Phát hiện bàn cờ, homography, tách vật và đo mm | 4–5 phút |
| Người 4 | Dung sai, đánh giá, lịch sử/báo cáo và giới hạn | 3–4 phút |

## 2. Phân công chi tiết

### Người 1 — Tổng quan và demo

**Cần học**

- Bài toán: đo chiều dài/rộng của một sản phẩm chữ nhật phẳng từ ảnh, không tiếp xúc; sau đó đối chiếu với dung sai.
- Người dùng nhập những gì: cấu hình bàn cờ, kích thước ô thực tế, calibration, mã sản phẩm, kích thước danh nghĩa và sai lệch dưới/trên.
- Kiến trúc tổng quát và thứ tự các bước xử lý ở mục 3.
- Khác nhau giữa **Camera Calibration**, **Quy trình đo**, **Lịch sử** và trang **Đo kích thước** dùng để xem trước/debug.
- Phạm vi/giả thiết: sản phẩm phẳng, bàn cờ và sản phẩm đồng phẳng, đủ góc bàn cờ nhìn thấy, dùng đúng camera và độ phân giải đã hiệu chuẩn.
- Giải thích được thời gian xử lý được ghi cho mỗi lượt; không gọi quy trình hiện tại là đo video real-time.

**Cần trình bày**

1. Nêu vấn đề thực tế và mục tiêu của project.
2. Giới thiệu đầu vào, đầu ra và các trang chính.
3. Trình bày sơ đồ pipeline ở mục 3 bằng lời dễ hiểu.
4. Demo một lượt đo: nạp/áp dụng calibration → nhập thông tin sản phẩm/dung sai → đưa ảnh có vật và bàn cờ vào → xác nhận điều kiện → đo → giải thích kết quả → mở lịch sử.
5. Chỉ ra kết luận ĐẠT/KHÔNG ĐẠT/KHÔNG THỂ ĐÁNH GIÁ và thời gian xử lý của lượt vừa chạy.
6. Kết luận ngắn về những gì đã làm được và phần cần kiểm chứng tiếp.

**Chuẩn bị demo**

- Dùng calibration thực đã lưu, khớp với đúng camera, độ phân giải, zoom/focus của ảnh demo. Không dùng calibration mẫu không rõ nguồn.
- Chuẩn bị trước một ảnh/đối tượng có bàn cờ rõ; biết đúng số góc trong và cạnh ô. Có số đo thước cặp và thông số danh nghĩa/dung sai thật nếu demo kết luận dung sai.
- Chọn đối tượng và ánh sáng đơn giản; kiểm tra trước app, quyền camera và kết nối localhost.
- Chuẩn bị ảnh dự phòng cùng calibration nếu camera trực tiếp hoặc quyền trình duyệt gặp lỗi.
- Không khẳng định kết quả của một lượt demo là độ chính xác chung của hệ thống.

**Câu dẫn khi demo**

> “Em sẽ chạy một lượt đo theo đúng luồng sử dụng. Calibration phải khớp với camera và độ phân giải. Hệ thống nhận ảnh, kiểm tra chất lượng, tìm bàn cờ, ánh xạ sang mm, đo vật thể rồi mới xét dung sai. Nếu thiếu điều kiện hoặc phép đo không đáng tin cậy, hệ thống phải báo không thể đánh giá thay vì tự đưa ra kết luận.”

### Người 2 — Hiệu chuẩn camera và khử méo

**Cần học**

- Phân biệt **hiệu chuẩn nội tại camera** với **homography của mặt phẳng**. Hiệu chuẩn camera ước lượng camera matrix và méo ống kính; homography ánh xạ giữa mặt phẳng bàn cờ và tọa độ đo.
- Project dùng mô hình pinhole OpenCV với camera matrix `K` và 5 hệ số méo `(k1, k2, p1, p2, k3)`.
- Dùng nhiều ảnh bàn cờ ở các vị trí, khoảng cách và góc nghiêng khác nhau; hướng dẫn project khuyến nghị khoảng 15–25 ảnh đa dạng. Tất cả ảnh trong một bộ cần cùng camera/độ phân giải và cùng bàn cờ.
- `calibrateCamera` trả thông số nội tại, méo, pose từng ảnh và reprojection error. Calibration được lưu/nạp bằng JSON; ảnh lúc đo được khử méo trước các bước sau.
- Trong full flow hiện tại, calibration có RMS tổng > 1 px hoặc RMS một ảnh > 2 px bị từ chối. Đây là ngưỡng kiểm tra chất lượng calibration, **không đồng nghĩa sai số kích thước là 1 px hoặc 1 mm**.
- Không đổi độ phân giải, zoom/focus, crop hoặc resize ảnh nếu không tạo calibration tương ứng.

**Cần trình bày**

1. Vì sao cần calibration: méo ống kính làm biến dạng vị trí và kích thước trên ảnh.
2. Cách thu bộ ảnh bàn cờ đa dạng và cách hệ thống kiểm tra góc.
3. Ý nghĩa của `K`, hệ số méo và reprojection RMS ở mức khái niệm.
4. Luồng lưu/nạp/áp dụng calibration và khử méo.
5. Giới hạn: RMS thấp không tự chứng minh phép đo mm chính xác; cần đối chiếu thước đo chuẩn trên dữ liệu thật.

**Câu hỏi cần trả lời được**

- Vì sao cần nhiều ảnh bàn cờ, không chỉ một ảnh? — Cần nhiều pose/độ nghiêng/vị trí để ước lượng thông số camera ổn định hơn.
- Vì sao không dùng calibration của camera khác? — Thông số phụ thuộc camera và chế độ chụp; sai độ phân giải/zoom/focus có thể làm ánh xạ không còn phù hợp.
- RMS reprojection error có phải sai số đo kích thước không? — Không; đó là sai lệch chiếu điểm bàn cờ theo pixel trong quá trình fit, không phải sai số mm của vật.

### Người 3 — Thị giác máy tính và tính kích thước

**Cần học**

- Đọc/kiểm tra ảnh; áp dụng khử méo nếu có calibration.
- Phát hiện đủ các góc trong Chessboard. Detector ưu tiên `findChessboardCornersSB`; có nhánh cổ điển và tinh chỉnh subpixel khi cần.
- Gán tọa độ vật lý cho các góc: `(cột × cạnh ô, hàng × cạnh ô)` mm.
- Tính homography để ánh xạ từ pixel sang mặt phẳng mm; kiểm tra chất lượng và từ chối phép ánh xạ không đáng tin.
- Phân đoạn vật: grayscale → Gaussian Blur → Otsu (`threshold`) hoặc Canny → contours. Lọc contour bàn cờ, vật chạm mép, contour quá nhỏ/mảnh và các ứng viên không hợp hình học.
- Chuyển contour qua mặt phẳng mm, khớp hình chữ nhật tối thiểu; đặt `length` là cạnh dài và `width` là cạnh ngắn. Không dùng một tỉ lệ pixel/mm cố định cho toàn ảnh.
- Các lỗi chính: không tìm thấy bàn cờ/vật, nhiều vật ứng viên, vật không gần hình chữ nhật, homography không tin cậy, ảnh mờ/tương phản kém.

**Cần trình bày**

1. Giải thích vì sao kích thước ô bàn cờ đã biết giúp suy ra tọa độ mm.
2. Mô tả homography như phép biến đổi phối cảnh trên cùng một mặt phẳng.
3. So sánh ngắn Otsu và Canny; cả hai là phương pháp phân đoạn/biên, không phải mô hình được train.
4. Giải thích cách contour được kiểm tra và vì sao không đơn giản lấy contour lớn nhất.
5. Nêu điều kiện hệ thống từ chối kết quả để tránh đo nhầm.

**Câu hỏi cần trả lời được**

- Homography có thay thế calibration camera không? — Không. Calibration xử lý méo ống kính; homography ánh xạ phối cảnh của mặt phẳng sau khi khử méo.
- Vì sao vật và bàn cờ phải đồng phẳng? — Homography chỉ ánh xạ đúng mặt phẳng được xác lập; khác độ cao tạo sai lệch tỷ lệ/kích thước.
- Nếu bàn cờ bị che một phần thì sao? — Nếu không đủ góc trong để xác định đáng tin cậy, hệ thống từ chối đo.

### Người 4 — Dung sai, đánh giá và truy vết

**Cần học**

- Dung sai được nhập riêng cho chiều dài/rộng: danh nghĩa, sai lệch dưới có dấu và sai lệch trên có dấu.
- Giới hạn là `nominal + deviation`; hai biên được tính bao gồm. Sản phẩm chỉ ĐẠT khi cả hai chiều ĐẠT.
- Phân biệt ba kết luận: **ĐẠT**, **KHÔNG ĐẠT**, **KHÔNG THỂ ĐÁNH GIÁ**. Lỗi ảnh/đo không đồng nghĩa sản phẩm lỗi.
- Lịch sử SQLite lưu UUID, thời gian, ảnh gốc/ảnh chú thích, cấu hình và snapshot calibration; có lọc và xuất CSV/PDF.
- Trường thời gian xử lý được tính đến khi tạo ảnh chú thích; không gồm thời gian lưu database hoặc xuất báo cáo. Nó không nhất thiết là latency từ lúc người dùng đưa vật vào đến khi trình duyệt vẽ xong kết quả.
- Đánh giá dataset cần ảnh và số đo tham chiếu (ví dụ thước cặp) theo từng ảnh; báo cáo MAE/RMSE/MAPE, sai số lớn nhất và tỷ lệ đo thành công, tách length/width và phân nhóm điều kiện.
- Test hiện tại xác minh hành vi phần mềm bằng fixture tổng hợp; không thay cho thực nghiệm độ chính xác trên sản phẩm thật. README ghi rõ chưa có dữ liệu thực nghiệm để kết luận độ chính xác.

**Cần trình bày**

1. Cách chuyển số đo thành kết luận dung sai; cho một ví dụ minh họa và ghi rõ nếu dùng số giả định.
2. Vì sao có trạng thái KHÔNG THỂ ĐÁNH GIÁ.
3. Dữ liệu nào được lưu để tra cứu lại và tính truy vết.
4. Cách đánh giá độ chính xác đúng: ground truth bằng dụng cụ đo, tập đánh giá độc lập, chỉ số sai số và tỷ lệ thành công.
5. Nêu trung thực giới hạn hiện tại và đề xuất: thu dataset thực, đo lặp, đánh giá nhiều điều kiện, đo thời gian nhiều lượt.

**Câu hỏi cần trả lời được**

- Có thể dùng 398 test đạt để nói hệ thống đo chính xác không? — Không. Chúng xác minh chức năng/phần mềm; fixture hình học là tổng hợp. Muốn kết luận sai số thực cần dữ liệu thật và số đo chuẩn độc lập.
- Thời gian `173.026 ms` trong ảnh có ý nghĩa gì? — Đó là thời gian xử lý ghi nhận cho đúng lượt ấy (khoảng 0,173 giây), không phải benchmark trung bình và không bao gồm toàn bộ thời gian từ lúc đặt vật/chụp đến lúc UI hiển thị.
- Để báo cáo tốc độ đáng tin hơn cần làm gì? — Chạy nhiều lượt cùng thiết lập và độ phân giải, báo cáo trung bình/median/lớn nhất, số mẫu và cấu hình máy; phân biệt processing time với end-to-end latency.

## 3. Sơ đồ kỹ thuật cả nhóm phải nắm

```text
Ảnh nguồn
  → kiểm tra/giải mã
  → calibration hợp lệ, đúng camera và độ phân giải
  → khử méo
  → xác nhận điều kiện + sàng lọc chất lượng ảnh
  → phát hiện Chessboard
  → homography từ pixel sang mặt phẳng mm
  → phân đoạn và lọc contour sản phẩm
  → khớp hình chữ nhật, lấy length/width
  → so sánh dung sai
  → hiển thị, lưu SQLite, xem lịch sử / xuất CSV-PDF
```

Quy tắc nói chung: **phép đo thất bại hoặc thiếu điều kiện thì không phân loại sản phẩm là KHÔNG ĐẠT; kết luận phải là KHÔNG THỂ ĐÁNH GIÁ.**

## 4. Kịch bản báo cáo và bàn giao

### Mở đầu — Người 1

“Nhóm em xây dựng VisionGauge để đo kích thước chiều dài/rộng của sản phẩm phẳng từ ảnh và hỗ trợ kiểm tra dung sai. Project dùng OpenCV và hình học với Chessboard làm chuẩn, không dùng mô hình học máy. Nhóm xin trình bày từ hiệu chuẩn camera, thuật toán đo, đến đánh giá và demo.”

### Chuyển phần

- Người 1 → Người 2: “Để phép đo từ pixel ra mm có cơ sở, trước hết cần hiệu chuẩn camera và xử lý méo ống kính. Phần này bạn … trình bày.”
- Người 2 → Người 3: “Sau khi ảnh được khử méo, hệ thống dùng các góc bàn cờ để xác lập mặt phẳng tọa độ mm. Phần tiếp theo giải thích pipeline phát hiện và đo.”
- Người 3 → Người 4: “Sau khi có chiều dài/rộng, hệ thống còn phải quyết định phép đo có nằm trong dung sai không và lưu lại để truy vết. Phần này bạn … trình bày.”
- Người 4 → Người 1: “Các chỉ số kiểm thử hiện mới xác minh phần mềm; độ chính xác thực tế cần dataset có số đo chuẩn. Sau đây nhóm demo một lượt đo và kết luận.”

## 5. Câu hỏi chung thầy có thể hỏi

| Câu hỏi | Ý chính cần trả lời |
|---|---|
| Tại sao chọn Chessboard? | Có hình học đều, góc trong xác định được và cạnh ô thực tế biết trước; phù hợp calibration và lập tọa độ phẳng. |
| Project có AI không? | Không. Đây là pipeline OpenCV/hình học truyền thống; không có bước train mô hình. |
| Đo được vật cong hoặc không phẳng không? | Project hiện nhắm tới vật chữ nhật phẳng. Vật cong/khác mặt phẳng làm giả thiết homography không còn phù hợp. |
| Có phải đo real-time không? | Hiện tại xử lý ảnh tĩnh từng lượt (có thể nhập lô); chưa phải luồng video liên tục. Thời gian processing của mỗi lượt được ghi riêng. |
| Đã chứng minh độ chính xác chưa? | Chưa trên dữ liệu sản phẩm thực. Cần chụp ảnh, đo ground truth bằng dụng cụ chuẩn, giữ tập test độc lập và tính sai số. |
| Hướng phát triển tiếp theo? | Tạo dataset thật có nhãn thước cặp; kiểm tra nhiều camera/ánh sáng/góc; báo cáo sai số và tốc độ nhiều lượt; xem xét độ không đảm bảo đo. |

## 6. Checklist chuẩn bị của nhóm

- [ ] Thay Người 1–4 bằng tên thật và chốt thứ tự nói.
- [ ] Mỗi người chuẩn bị 2–4 slide cho phần mình; thống nhất thuật ngữ và đơn vị mm/px.
- [ ] Cả nhóm thuộc pipeline ở mục 3 và hiểu giả thiết đồng phẳng.
- [ ] Kiểm tra calibration, ảnh, bàn cờ, số góc trong, cạnh ô và thông số dung sai trước buổi báo cáo.
- [ ] Người 1 chạy thử demo; các thành viên khác biết phương án chuyển sang ảnh dự phòng.
- [ ] Không trình bày số liệu tổng hợp/test như kết quả đo thực nghiệm.
- [ ] Nếu trích thời gian 173.026 ms, ghi rõ đó là một lượt minh họa, không phải trung bình.
- [ ] Chốt câu trả lời thống nhất: kết quả test phần mềm tốt không tự chứng minh độ chính xác đo thực tế.

## 7. Tài liệu project để từng người học

- Tổng quan và cài/chạy: [README](../README.md), [full flow](full_flow.md).
- Người 1: [giao diện](ui.md), [full flow](full_flow.md).
- Người 2: [camera calibration](camera_calibration.md), mã [calibration](../visiongauge/calibration/).
- Người 3: [đo lường](measurement.md), mã [processing](../visiongauge/processing/) và [measurement](../visiongauge/measurement/).
- Người 4: [dung sai](tolerance.md), [đánh giá](evaluation.md), mã [workflow](../visiongauge/workflow/), [storage](../visiongauge/storage/) và [reporting](../visiongauge/reporting/).

