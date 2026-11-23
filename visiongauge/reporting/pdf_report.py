"""Paginated Vietnamese PDF reports with embedded fonts and optional annotations."""

from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from matplotlib import get_data_path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from visiongauge.storage import summarize_records


def records_to_pdf(records: list[dict], *, annotated_images: dict[str, bytes] | None = None) -> bytes:
    """No measurement is recomputed or fabricated during report generation."""
    font = "VisionGaugeDejaVu"
    if font not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(font, str(Path(get_data_path()) / "fonts/ttf/DejaVuSans.ttf")))
    style = ParagraphStyle("Body", fontName=font, fontSize=9, leading=13, spaceAfter=7)
    title = ParagraphStyle("Title", parent=style, fontSize=19, leading=24, spaceAfter=14)
    small = ParagraphStyle("Small", parent=style, fontSize=8, leading=11)

    def p(value, selected_style=style):
        return Paragraph(escape(str(value)).replace("\n", "<br/>"), selected_style)

    def table(rows, widths):
        result = Table([[p(value, small) for value in row] for row in rows], colWidths=widths, repeatRows=1, hAlign="LEFT")
        result.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef1f4")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), .4, colors.HexColor("#d5d9dd")),
            ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        return result

    target = BytesIO()
    document = SimpleDocTemplate(target, pagesize=A4, leftMargin=40, rightMargin=40, topMargin=42, bottomMargin=42,
                                 title="VisionGauge - Báo cáo kiểm tra kích thước", author="VisionGauge")
    story = [p("VisionGauge", title), p("BÁO CÁO KIỂM TRA KÍCH THƯỚC", title)]
    counts = summarize_records(records)
    story += [p(f"Số lượt đo trong báo cáo: {len(records)}"),
              table([["ĐẠT", "KHÔNG ĐẠT", "KHÔNG THỂ ĐÁNH GIÁ"], list(counts.values())], [171, 172, 172]),
              Spacer(1, 14), p("Số đo và kết luận lấy từ lịch sử đã lưu. Thời gian dùng UTC (ISO 8601)."),
              p("Quy tắc: hai giới hạn được tính là đạt; so sánh số đo chưa làm tròn. Cảnh báo gần giới hạn không thay đổi kết luận và không thay thế đánh giá độ không đảm bảo đo."),
              p("Chưa có kết luận về độ chính xác thực nghiệm nếu chưa đối chiếu dụng cụ tham chiếu. Sai số chiếu lại bàn cờ không phải sai số kích thước theo mm.")]
    for record in records:
        story += [PageBreak(), p("Chi tiết lượt đo", title), p(f"Mã: {record['run_id']}"),
                  p(f"Sản phẩm: {record['product_id']} | Ảnh: {record['filename']}"),
                  p(f"Bắt đầu: {record['started_at']} | Thời gian xử lý: {record['duration_ms']} ms"),
                  p(f"Trạng thái: {record['processing_status']} | Kết luận: {record['decision']}"),
                  p(record["message"])]
        if record["error_code"]:
            story.append(p(f"Bước lỗi: {record['error_stage']} | Mã lỗi: {record['error_code']}"))
        if record["dimensions"]:
            rows = [["Kích thước", "Danh nghĩa mm", "Giới hạn dưới mm", "Giới hạn trên mm", "Đo được mm", "Độ lệch mm", "Kết luận"]]
            for dimension in record["dimensions"]:
                rows.append(["Dài" if dimension["name"] == "length" else "Rộng",
                             *[dimension[key] for key in ("nominal_mm", "lower_limit_mm", "upper_limit_mm", "measured_mm", "deviation_mm", "status")]])
            story += [table(rows, [48, 65, 65, 65, 93, 93, 86]), Spacer(1, 10)]
        story.append(p(f"Calibration: {record['calibration_id'] or 'Chưa có'}", small))
        if record["calibration"]:
            model = record["calibration"]
            story.append(p(f"Độ phân giải: {model['image_size']} | RMS calibration: {model['rms_px']} px", small))
        if record["settings"]:
            settings = record["settings"]
            story += [p(f"Bàn cờ: {settings['board']} | Tách biên: {settings['segmentation']}", small),
                      p(f"Điều kiện chụp: {settings['acquisition_notes'] or 'Không ghi chú'}", small),
                      p(f"Đã xác nhận điều kiện đo: {settings['conditions_confirmed']}", small)]
        if record["quality"]:
            q = record["quality"]
            story.append(p(f"Laplacian variance: {q['laplacian_variance']:.3f}; tương phản P95-P05: {q['contrast_p95_p05']:.3f}", small))
        for warning in record["warnings"]:
            story.append(p(f"Lưu ý: {warning}", small))
        picture = (annotated_images or {}).get(record["run_id"])
        if picture:
            item = Image(BytesIO(picture))
            factor = min(515 / item.imageWidth, 230 / item.imageHeight)
            item.drawWidth, item.drawHeight = item.imageWidth * factor, item.imageHeight * factor
            story += [Spacer(1, 8), item, p("Ảnh sau khử méo, có chú thích kích thước. Kết luận dung sai nằm trong bảng phía trên.", small)]
        story.append(p(f"SHA-256 ảnh nguồn: {record['source_sha256']}", small))

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont(font, 8)
        canvas.drawString(40, 24, "VisionGauge | mm | Báo cáo từ lịch sử phép đo")
        canvas.drawRightString(A4[0] - 40, 24, f"Trang {doc.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=footer, onLaterPages=footer)
    return target.getvalue()
