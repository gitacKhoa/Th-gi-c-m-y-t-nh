# Kiểm tra dung sai sản phẩm — nhiệm vụ 6

Module [tolerance/](../visiongauge/tolerance/) không phụ thuộc OpenCV hoặc Streamlit.
Giao diện dùng kết quả pipeline hiện tại, không thay đổi thuật toán đo hay số đo
để đưa sản phẩm vào khoảng dung sai.

## Sử dụng trên giao diện

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

1. Chọn trang **Đo kích thước**, bật **Kiểm tra dung sai** trong thanh bên.
2. Nhập đủ sáu giá trị: danh nghĩa, sai lệch dưới và sai lệch trên cho cả chiều
   dài và chiều rộng. Không tự điền thông số sản phẩm giả định.
3. Upload/chụp ảnh, cấu hình bàn cờ và calibration như quy trình đo đã có, bấm
   **Bắt đầu đo**. Kết luận tự xuất hiện sau kết quả đo.
4. Xem trạng thái tổng thể và bảng từng kích thước: danh nghĩa, hai giới hạn,
   số đo, độ lệch có dấu, kết luận và lý do. Kích thước vượt giới hạn được báo đỏ
   kèm chữ **Trên/Dưới giới hạn**, không chỉ phân biệt bằng màu.

Nhập sai lệch **có dấu**, đơn vị mm. Ví dụ cấu hình minh họa (không phải số đo thực):

| Kích thước | Danh nghĩa | Sai lệch dưới | Sai lệch trên | Khoảng cho phép |
| --- | ---: | ---: | ---: | --- |
| Chiều dài | 160 | -0.5 | +1.0 | [159.5, 161.0] mm |
| Chiều rộng | 80 | -0.2 | +0.3 | [79.8, 80.3] mm |

Với dung sai ±0.5 mm, nhập dưới **-0.5**, trên **+0.5**. Cũng hỗ trợ dung sai
một phía hoặc cả hai sai lệch cùng dấu, miễn dưới <= trên. Hai sai lệch bằng 0
nghĩa là chỉ chấp nhận đúng danh nghĩa. Khoảng chấp nhận có thể có độ rộng bằng 0.

Chiều dài là cạnh dài, chiều rộng là cạnh ngắn của kết quả hình học, không phải
trục ngang/dọc ảnh. Danh nghĩa chiều dài phải >= danh nghĩa chiều rộng.

## Quy tắc hiện tại

- `lower_limit = nominal + lower_deviation`.
- `upper_limit = nominal + upper_deviation`.
- `deviation = measured - nominal`: số dương là lớn hơn danh nghĩa.
- **ĐẠT** cho một chiều khi `lower_limit <= measured <= upper_limit`.
- **KHÔNG ĐẠT** cho một chiều khi nằm dưới/trên khoảng đó.
- Sản phẩm chỉ **ĐẠT** khi cả hai chiều đều ĐẠT. Nếu có chiều KHÔNG ĐẠT và cả
  hai chiều đủ điều kiện đánh giá thì sản phẩm KHÔNG ĐẠT.
- Thiếu kết quả, phép đo thất bại, số đo NaN/vô cực/không dương hoặc chiều dài
  nhỏ hơn chiều rộng: **KHÔNG THỂ ĐÁNH GIÁ**, không đánh đồng lỗi đo với lỗi sản phẩm.
- Nếu một quy tắc tương lai trả KHÔNG THỂ ĐÁNH GIÁ cho bất kỳ chiều nào, kết luận
  toàn sản phẩm cũng là KHÔNG THỂ ĐÁNH GIÁ (ưu tiên hơn các trạng thái khác).

Cấu hình sai, thiếu giá trị, danh nghĩa không dương, giới hạn dưới <= 0 hoặc
sai lệch dưới > sai lệch trên không được dùng để đánh giá. API cấu hình báo
`ValueError`; giao diện hiển thị KHÔNG THỂ ĐÁNH GIÁ và vẫn cho phép đo hình học.

So sánh bằng `Decimal` từ biểu diễn thập phân của số đã nhập/đo, không làm tròn
số đo theo các chữ số của ô metric, không nới giới hạn bằng epsilon. Ví dụ kết
quả hơi lớn hơn giới hạn vẫn KHÔNG ĐẠT dù ô metric làm tròn nhìn giống giới hạn.
Bảng dung sai giữ các chữ số của số đo để giải thích trường hợp này. Cách biểu
diễn số không làm tăng độ chính xác thực tế của OpenCV.

## Trạng thái và kết quả cũ

Đổi thông số dung sai đánh giá lại kết quả đo hiện có, không chạy lại OpenCV.
Đổi ảnh, nguồn ảnh, bàn cờ, điều kiện méo, phương pháp tách biên hoặc calibration
làm mất hiệu lực kết quả đo; kết luận dung sai cũng không còn được giữ.
Nhấn phát hiện bàn cờ lại sẽ xóa phép đo và đưa dung sai về KHÔNG THỂ ĐÁNH GIÁ
cho đến khi đo lại. Không lưu cache kết luận riêng có thể lệch với ảnh hiện tại.

Cấu hình nhập được giữ trong phiên khi tắt/bật tính năng hoặc đổi trang; nó
không được lưu vĩnh viễn. Khi quay về trang đo mà không còn ảnh, không phục hồi
nhãn ĐẠT cũ. PNG tải xuống vẫn là ảnh hình học, không chứa kết luận dung sai và
không được coi là báo cáo kiểm tra dung sai.

## Mở rộng theo độ không đảm bảo đo

`DecisionRule` là interface nhận số đo, cấu hình từng chiều và độ không đảm bảo
mở rộng theo mm (nếu được cung cấp). Interface trả `RuleDecision(status, reason)`;
API tổng hợp kết quả và giữ `rule_id` cho việc truy vết.

`InclusiveLimitsRule` hiện chỉ so sánh trực tiếp với giới hạn; **chưa áp dụng
guard band hoặc độ không đảm bảo đo**. Nếu gọi API với độ không đảm bảo được
cung cấp, kể cả bằng 0, quy tắc mặc định trả KHÔNG THỂ ĐÁNH GIÁ thay vì bỏ qua.
Độ không đảm bảo âm/NaN/vô cực cũng bị từ chối đánh giá. Không tự suy ra độ không
đảm bảo theo mm từ reprojection error tính bằng pixel.

Để mở rộng, triển khai một policy có `rule_id` và `decide(...)`, rồi truyền vào
`evaluate_tolerance(..., rule=policy)`. Phải xác định cách diễn giải độ không đảm
bảo, mức bao phủ và quy tắc quyết định trước khi triển khai policy đó. Kiểm tra
phép đo thành công và dữ liệu hợp lệ luôn thực hiện trước policy, nên policy
không thể biến phép đo thất bại thành ĐẠT. Nhiệm vụ này chưa triển khai policy
độ không đảm bảo, chưa chứng nhận độ chính xác thực nghiệm hoặc rủi ro phân loại.

## API

```python
from visiongauge.tolerance import (
    DimensionTolerance, ProductTolerance, evaluate_tolerance,
)

specification = ProductTolerance(
    length=DimensionTolerance(160, -0.5, 1.0),
    width=DimensionTolerance(80, -0.2, 0.3),
)

# measurement là kết quả pipeline đã chạy thành công; các số trên là ví dụ cấu hình.
inspection = evaluate_tolerance(
    measurement.length_mm, measurement.width_mm, specification,
    measurement_succeeded=True,
)
print(inspection.status.value)
for dimension in inspection.dimensions:
    print(dimension.name, dimension.deviation_mm, dimension.status.value)

# Nhánh lỗi: không tái sử dụng số đo của ảnh trước.
unavailable = evaluate_tolerance(
    None, None, specification, measurement_succeeded=False,
    failure_reason="Không tìm thấy sản phẩm",
)
```

## Kiểm thử và file thay đổi

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_tolerance.py tests/test_tolerance_app.py
.\.venv\Scripts\python.exe -m pytest -q
```

Kết quả trên Windows/Python 3.11.9: **72 test mới đạt**, toàn bộ dự án
**343 tests passed**. Giao diện được kiểm tra bằng Streamlit AppTest; chưa kiểm
chứng độ chính xác với sản phẩm thực hoặc trên Python 3.12.

Test gồm hai biên và bốn tổ hợp biên; vừa vượt trên/dưới; hai chiều cùng lỗi;
dung sai bằng 0/bất đối xứng/một phía; sai số biểu diễn float; cấu hình và số đo
không hợp lệ; cờ thất bại thắng số đo cũ; extension policy và độ không đảm bảo.
AppTest kiểm tra pipeline thật với ảnh tổng hợp, đổi cấu hình không đo lại,
không giữ ĐẠT cũ, lỗi phát hiện bàn cờ/sản phẩm, chuyển trang và số đo chưa làm tròn.

- Lõi: [models.py](../visiongauge/tolerance/models.py), [rules.py](../visiongauge/tolerance/rules.py),
  [inspection.py](../visiongauge/tolerance/inspection.py), [__init__.py](../visiongauge/tolerance/__init__.py).
- Giao diện: [tolerance_panel.py](../visiongauge/ui/tolerance_panel.py),
  [app.py](../visiongauge/ui/app.py), [views.py](../visiongauge/ui/views.py).
- Test: [test_tolerance.py](../tests/test_tolerance.py), [test_tolerance_app.py](../tests/test_tolerance_app.py).
- Tài liệu: [README](../README.md), [hướng dẫn giao diện](ui.md) và tài liệu này;
  cập nhật [phiên bản](../visiongauge/__init__.py).
