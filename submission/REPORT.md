# Báo cáo Day 09 — Nguyễn Minh Hiếu, 2A202603091

## 1. Kết luận trước
Pipeline kết luận **Hold** (mã thoát 10). Vào 224 ảnh, cửa vào loại 21 (hỏng, nhỏ, trùng, rò rỉ test), còn **203 ảnh** vào bản xuất nháp `export/clean_v1` (chưa phát hành). Lý do: không còn lỗi bắt buộc (`n_errors` = 0), nhưng 38/203 ảnh (18,7%) còn cảnh báo chưa người duyệt, vượt ngưỡng 10% của cổng (hàng đợi 125 ảnh, người duyệt xem được 80).

## 2. Lỗi và phân việc
Lấy từ `02_error_list_v1` (gom theo mã lỗi). Cột "ai sửa": **máy** (autofix) hay **người** (hàng đợi); chỉ ghi những mã có mặt trong lô của bạn.

| Mã lỗi | Số ảnh/dòng | Ai sửa (máy/người) | Vì sao |
|---|---:|---|---|
| `BAD_CLASS_ID` | 6 | máy | Cú pháp rõ ràng, xoá dòng (`drop_line`) |
| `BAD_FORMAT` | 3 | máy | Dòng sai cột/không phải số, xoá dòng |
| `BOX_ZERO` | 4 | máy | Box w hoặc h ≤ 0, xoá dòng |
| `DUP_BOX` | 7 | máy | Box lặp cùng lớp, xoá dòng sau |
| `BOX_OUT_OF_IMAGE` | 8 | máy | Cắt về [0,1] (`clip_box`), hoặc xoá nếu hết diện tích |
| `BAD_CLASS_NAME` | 2 dòng (1 file `data.yaml`) | máy | Ghi lại `names` đúng `cfg["classes"]` |
| `DUP_IMAGE_EXACT` / `DUP_IMAGE_NEAR` | 8 / 3 | máy | Loại ảnh trùng ở cửa vào |
| `LEAK_TEST` / `BAD_SIZE` / `CORRUPT_IMAGE` | 5 / 3 / 2 | máy | Loại ảnh rò rỉ test, quá nhỏ (< 250px), hỏng |
| `MISSING_LABEL_FILE` | 6 | **người** | Máy không bịa nhãn; vào hàng đợi (`NEEDS_LABEL`, ưu tiên 10) |
| `POSSIBLE_MISSING` / `WRONG_CLASS` / `LOOSE_BOX` / `FALSE_POS` | 52 / 18 / 24 / 27 ảnh | **người** | Lỗi ngữ nghĩa, máy chỉ cảnh báo vì model lớn cũng có thể sai |

`05_review_queue.csv` xếp theo `priority` = tổng trọng số của các mã lỗi trên ảnh (`review.weights`): `NEEDS_LABEL` 10 (ảnh chưa có nhãn nào), `POSSIBLE_WRONG_CLASS` 3, `POSSIBLE_MISSING`/`POSSIBLE_FALSE_POS`/`FIXED_DROP_LINE` 2. Ảnh đầu hàng là `img_0020` (priority 11,5) vì dồn ba mã (`FIXED_DROP_LINE`, `POSSIBLE_MISSING`, `POSSIBLE_WRONG_CLASS`); 6 ảnh `NEEDS_LABEL` đứng ngay sau (priority 10). Hàng đợi 125 ảnh, người xem 80 (64%). Trong 80 ảnh đó, theo mã đứng đầu mỗi ảnh có 21 `POSSIBLE_MISSING`, 14 `POSSIBLE_WRONG_CLASS`, 6 `POSSIBLE_LOOSE_BOX`, 4 `POSSIBLE_FALSE_POS` (45 ảnh nghi lỗi ngữ nghĩa); còn lại là ảnh có dòng bị máy xoá/cắt (17), `EMPTY_LABEL` (11), `NEEDS_LABEL` (6) và `BOX_TINY` (1). 45 ảnh cuối hàng đợi không được xem.

## 3. Calibration (2 ngưỡng)
| Tham số | Khởi đầu | Đã chọn | Precision / Recall (trước → sau) | Lý do (đánh đổi) |
|---|---|---|---|---|
| `duplicates.phash_dist` | 2 | 8 | `DUP_IMAGE_NEAR`: P 1.00 / R 0.50 → P 1.00 / R 0.67 (`DUP_IMAGE_EXACT` giữ 1.00/1.00) | Xoá ảnh là hành động tự động, nên ưu tiên precision: P vẫn 1.00. Dist 4–14 là vùng bằng phẳng (R 0.67), chọn giữa vùng. Dist 16 có R 0.83 nhưng ở sát vách: dist 20 làm `DUP_IMAGE_EXACT` R tụt còn 0.33. |
| `second_opinion.conf` | 0.25 | 0.6 | `MISSING`: P 0.50 → 0.57 (R giữ 1.00); `WRONG_CLASS`: P 0.56 → 0.62 (R giữ 0.83); `LOOSE_BOX`: P 0.29 / R 0.40 → P 0.20 / R 0.20 | Cảnh báo chỉ chuyển người xem nên chấp nhận P thấp, nhưng giữ R của `MISSING` ở 1.00 (conf 0.7 mới làm R tụt còn 0.88, 0.8 còn 0.75). Đánh đổi: `LOOSE_BOX` tệ đi (R 0.40 → 0.20), chấp nhận vì tập calib chỉ có 5 ca loose và đã ghi là điểm mù ở mục 4. |

Hàng đợi duyệt trên raw (budget 0, phash_dist 8): conf 0.25 → 143 ảnh, 0.5 → 130, 0.6 → 125, 0.7 → 118. Tăng conf giảm hàng đợi nhưng **vẫn lớn hơn ngân sách 80 ở mọi giá trị**; phần lớn là `POSSIBLE_FALSE_POS` (dùng `fp_conf` cố định, P chỉ 0.31).

**Chỗ calibration có thể đánh lừa:** bảng calib cho thấy `phash_dist` 16 là tốt nhất (`DUP_IMAGE_NEAR` R 0.83, F1 0.91), nhưng trên raw nó loại thêm nhiều ảnh. Số ảnh bị loại ở bước 1: dist 2 → 19, dist 8 → 21, dist 12 → 22, **dist 16 → 31**. Nhảy 9 ảnh từ 12 lên 16 trong khi calib chỉ cải thiện 1 ca (6 ca near, 0.67 → 0.83), nên phần lớn là ảnh khác nhau bị coi là trùng (xoá nhầm). Calib chỉ có 6 ca `DUP_IMAGE_NEAR` nên mỗi ca thay đổi recall 17%, và ảnh chèn không giống ảnh trùng tự nhiên trong raw.

## 4. Cửa chặn và điều pipeline KHÔNG bắt được
**Lỗi tự quan sát bằng mắt (qua `scripts/viz_labels.py`, ảnh trong `work/viz/`):**
- `img_0001`: nhãn thiếu — có một người lính trong ảnh nhưng không có box.
- `img_0030`: nhãn thừa — có 2 box ở cạnh bên trái ảnh, không bao quanh vật thể nào.

Đối chiếu với `02_error_list_v1.csv`: cả hai lỗi này pipeline **đã bắt được**, nên chưa phải điểm mù.
- `img_0001`: `second_opinion` báo `POSSIBLE_MISSING` hai lần (model thấy lớp `person`, conf 0.95 và 0.42, mà nhãn không có box). Ngoài ra `label_format` báo `DUP_BOX` ở dòng 3.
- `img_0030`: `label_format` báo `BOX_OUT_OF_IMAGE` ở dòng 9 (tràn 0.023); `second_opinion` báo `POSSIBLE_FALSE_POS` ở dòng 9, cùng `POSSIBLE_MISSING` và `POSSIBLE_LOOSE_BOX` (IoU 0.34).

**(a) Cổng chặn đúng.** Lệnh: `python -m pipeline.run --budget 0 --reports work/rep_nb --export-dir work/exp_nb`.
- Kết luận **Rework**, mã thoát **20** (`08_summary.json`: `decision: Rework`, `n_errors: 6`, `reviewed: 0`).
- 6 lỗi bắt buộc còn lại đều là `MISSING_LABEL_FILE` (`img_0031`, `img_0053`, `img_0126`, `img_0135`, `img_0170`, `img_0219`). Máy không bịa nhãn, và không có người gán nên cổng giữ lại.
- **Không xuất** dataset: log ghi "KHÔNG xuất: còn lỗi bắt buộc (Rework)", `exported: null`, thư mục `work/exp_nb` không được tạo.
- Số liệu lượt chạy (chạy trước khi calibrate, cấu hình khởi đầu `phash_dist` 2, `conf` 0.25): nhận 205/224 ảnh (loại 19 ở cửa vào); vòng 1 có 36 lỗi bắt buộc và 273 cảnh báo; autofix thực hiện 35 thay đổi; còn 134/205 ảnh (65,4%) có cảnh báo.

**(b) Điểm mù (lỗi nhìn thấy bằng mắt nhưng `02_error_list_v1.csv` không có dòng nào cho ảnh):**
1. `img_0190`: box `person` không bám sát người trượt tuyết, dư nhiều khoảng trống phía trên và hai bên. Nhãn `1 0.439 0.801 0.250 0.356`, yolo26l (conf 0.91) cho box `0.431 0.799 0.191 0.241`. IoU ≈ 0.52, chỉ vừa trên `iou_loose` = 0.5 nên `POSSIBLE_LOOSE_BOX` không bật. IoU đo độ chồng lấp tổng thể, nên box rộng hơn vật khoảng 30% chiều rộng vẫn qua. Chỉ người nhìn ảnh mới thấy.
2. `img_0153`: nhãn có hai box khác lớp cùng một vị trí, `truck` `2 0.623 0.290 0.073 0.053` và `bus` `3 0.624 0.290 0.074 0.053` (IoU gần 1), trên cùng một xe ngoài đường. `DUP_BOX` chỉ so box cùng lớp nên không bắt; `second_opinion` im lặng vì đã có một nhãn cùng lớp với dự đoán của model phủ vật đó (luật "nhãn cùng lớp đã phủ vật thì không cờ"). Một trong hai box là thừa/sai lớp mà không ai báo.
Cách giảm: nâng `iou_loose` (đánh đổi: nhiều cảnh báo giả hơn, hàng đợi người dài hơn), và thêm check bắt hai box khác lớp có IoU cao.

## 5. Train: raw vs clean (tùy chọn, chấm riêng)
Chưa chạy. Phần train Colab là tùy chọn, chấm riêng; chưa làm vì ưu tiên hoàn thành phần lõi (5 bước) trước.

## 6. Quyết định và ghi chú AI
