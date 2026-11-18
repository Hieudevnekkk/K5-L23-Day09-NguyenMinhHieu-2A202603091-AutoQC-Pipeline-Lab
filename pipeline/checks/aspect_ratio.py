"""CHECK BONUS — Tỉ lệ khung hình bất thường của box (thưởng +3).

Box rất mảnh (dài gấp nhiều lần cạnh ngắn, tính bằng PIXEL) thường là box kéo lệch/nhầm điểm,
hoặc đo trên toạ độ chuẩn hoá mà quên nhân kích thước ảnh. Các lỗi này không vi phạm quy tắc cú pháp
(`label_format`) và có thể IoU vẫn cao với model, nên `second_opinion` không bắt.

| code            | severity | khi nào                                                      |
|-----------------|----------|--------------------------------------------------------------|
| BOX_ODD_ASPECT  | WARN     | max(w*W, h*H) / min(w*W, h*H) > `max_ratio` (mặc định 6.0)  |

- Chỉ cảnh báo (người xem), không tự sửa.
- Bỏ qua dòng hỏng, dòng w/h <= 0 (việc của `label_format`), ảnh không mở được.
- Ngưỡng lấy từ `cfg["aspect_ratio"]["max_ratio"]` nếu có; không có thì dùng `DEFAULT_MAX_RATIO`.
  (`configs/pipeline.yaml` được ghim nên không thêm khoá mới vào đó.)

Test:  pytest tests/test_aspect_ratio.py -q
Chạy riêng trên một thư mục dataset:  python -m pipeline.checks.aspect_ratio work/run/ds
"""
from ..common import WARN, Issue, parse_yolo_line

DEFAULT_MAX_RATIO = 6.0


def run(ds, cfg):
    max_ratio = cfg.get("aspect_ratio", {}).get("max_ratio", DEFAULT_MAX_RATIO)
    issues = []
    for lp in ds.label_files():
        stem = lp.stem
        size = ds.image_size(stem)
        if not size:
            continue
        for no, text in ds.read_label_lines(stem) or []:
            try:
                _, _, _, w, h = parse_yolo_line(text)
            except ValueError:
                continue
            pw, ph = w * size[0], h * size[1]
            if pw <= 0 or ph <= 0:
                continue
            ratio = max(pw, ph) / min(pw, ph)
            if ratio > max_ratio:
                issues.append(Issue("aspect_ratio", WARN, "BOX_ODD_ASPECT", stem,
                                    f"box {pw:.0f}x{ph:.0f}px, tỉ lệ {ratio:.1f}:1 > {max_ratio:g}:1",
                                    no, {"ratio": round(ratio, 2)}))
    return issues


if __name__ == "__main__":
    import sys

    from ..common import Dataset, load_config

    cfg = load_config()
    found = run(Dataset(sys.argv[1] if len(sys.argv) > 1 else "work/run/ds", cfg["classes"]), cfg)
    for i in found:
        print(f"[{i.severity}] {i.code} {i.image}:{i.line}  {i.message}")
    print(f"{len(found)} cảnh báo")
