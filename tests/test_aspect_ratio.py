from pipeline.checks import aspect_ratio


def run(make_ds, cfg, lines, size=(640, 480)):
    ds = make_ds(images={"a": 1}, labels={"a": lines}, size=size)
    return aspect_ratio.run(ds, cfg)


def found(issues):
    return [(i.image, i.line) for i in issues if i.code == "BOX_ODD_ASPECT"]


def test_normal_boxes_are_silent(make_ds, cfg):
    # xe nằm ngang ~2:1, người đứng ~3:1
    assert run(make_ds, cfg, ["0 0.5 0.5 0.4 0.3", "1 0.2 0.5 0.1 0.5"]) == []


def test_very_wide_and_very_tall_boxes_are_warned(make_ds, cfg):
    iss = run(make_ds, cfg, ["0 0.5 0.5 0.9 0.05", "1 0.5 0.5 0.02 0.8"])    # 960/24 và 384/12.8 px
    assert found(iss) == [("a", 1), ("a", 2)]
    assert all(i.severity == "warn" and i.extra["ratio"] > 6 for i in iss)


def test_ratio_is_measured_in_pixels_not_normalised_units(make_ds, cfg):
    # w=0.3, h=0.1 (chuẩn hoá) nhưng ảnh 1000x200 -> 300x20 px: 15:1 (bất thường); ảnh vuông 300x100: 3:1 (ổn)
    assert found(run(make_ds, cfg, ["0 0.5 0.5 0.3 0.1"], size=(1000, 200))) == [("a", 1)]
    assert run(make_ds, cfg, ["0 0.5 0.5 0.3 0.1"], size=(300, 300)) == []


def test_exact_threshold_is_not_flagged(make_ds, cfg):
    cfg["aspect_ratio"] = {"max_ratio": 4.0}
    assert run(make_ds, cfg, ["0 0.5 0.5 0.4 0.1"], size=(100, 100)) == []        # đúng 4:1
    assert found(run(make_ds, cfg, ["0 0.5 0.5 0.41 0.1"], size=(100, 100))) == [("a", 1)]


def test_threshold_comes_from_config(make_ds, cfg):
    line = ["0 0.5 0.5 0.4 0.1"]                                                    # 4:1 trên ảnh vuông
    assert run(make_ds, cfg, line, size=(100, 100)) == []                           # mặc định 6
    cfg["aspect_ratio"] = {"max_ratio": 3}
    assert found(run(make_ds, cfg, line, size=(100, 100))) == [("a", 1)]


def test_blank_lines_keep_original_line_numbers(make_ds, cfg):
    assert found(run(make_ds, cfg, ["0 0.5 0.5 0.3 0.3", "", "", "0 0.5 0.5 0.9 0.05"])) == [("a", 4)]


def test_bad_lines_and_zero_size_do_not_crash(make_ds, cfg):
    iss = run(make_ds, cfg, ["garbage", "0 0.5 0.5 0 0.3", "93 0.5 0.5 0.9 0.05", "0 nan 0.5 0.2 0.2", "0 0.5 0.5 0.9 0.05"])
    assert found(iss) == [("a", 3), ("a", 5)]       # id lớp lạ vẫn là box hình học hợp lệ: việc của label_format


def test_image_without_label_or_unreadable_image_is_skipped(make_ds, cfg):
    ds = make_ds(images={"a": 1, "b": b"not an image"}, labels={"b": ["0 0.5 0.5 0.9 0.05"]})
    assert aspect_ratio.run(ds, cfg) == []
