import asyncio

import pytest
from PIL import Image

import artstudio_colours as colours
import artstudio_common as ac
import artstudio_create as create
import artstudio_photos as photos
import artstudio_qr as qr
import screen
import tools
from config import Settings


@pytest.fixture
def s(tmp_path):
    settings = Settings(memory_dir=str(tmp_path))
    hol = tmp_path / "Personal" / "Holiday"
    hol.mkdir(parents=True)
    for n, colour in enumerate(["red", "green", "blue", "yellow"]):
        Image.new("RGB", (80 + n * 20, 60), colour).save(hol / f"beach {n}.jpg")
    two = Image.new("RGB", (100, 50), "white")
    two.paste(Image.new("RGB", (50, 50), (10, 20, 200)), (0, 0))
    two.save(hol / "half.png")
    (hol / "iphone.heic").write_bytes(b"not really")
    (tmp_path / "Ideas").mkdir()
    return settings


def run(module, settings, **args):
    return module.run_tool(next(iter(module.NAMES)), args, settings)


def is_file_card(shown):
    return isinstance(shown, screen.Shown) and shown.card["kind"] == "file" and shown.card["mime"].startswith("image/")


# ---- colours ------------------------------------------------------------------------------------------

def test_palettes_from_a_base_colour(s):
    assert colours.scheme("#ff0000", "complementary")[:2] == ["#ff0000", "#00ffff"]
    assert colours.scheme("#ff0000", "triadic") == ["#ff0000", "#00ff00", "#0000ff"]
    assert colours.scheme("#ff0000", "tetradic") == ["#ff0000", "#80ff00", "#00ffff", "#8000ff"]
    assert colours.scheme("#ff0000", "analogous") == ["#ff00ff", "#ff0080", "#ff0000", "#ff8000", "#ffff00"]
    assert colours.scheme("#ff0000", "split_complementary") == ["#ff0000", "#00ff80", "#0080ff"]
    mono = colours.scheme("#3fa9ff", "monochrome")
    assert len(mono) == 6 and len(set(mono)) == 6
    shown = run(colours, s, action="palette", colour="teal", scheme="triadic")
    assert shown.card["kind"] == "art-palette"
    assert [w["hex"] for w in shown.card["data"]["swatches"]][0] == "#008080"
    assert shown.card["data"]["swatches"][0]["name"] == "teal"
    assert "triadic" in shown and len(shown.card["buttons"]) == 4
    with pytest.raises(ValueError):
        run(colours, s, action="palette", colour="not a colour")


def test_palette_from_a_picture(s):
    shown = run(colours, s, action="picture_palette", folder="Personal/Holiday", filename="half")
    swatches = shown.card["data"]["swatches"]
    assert shown.card["kind"] == "art-palette" and swatches[0]["share"] >= 45
    assert {w["hex"] for w in swatches[:2]} == {"#ffffff", "#0a14c8"}
    assert sum(w["share"] for w in swatches) in (99, 100, 101)


def test_colour_names(s):
    exact = run(colours, s, action="colour_name", colour="#708090")
    assert exact == "#708090 is slate grey." and len(exact.card["data"]["swatches"]) == 1
    near = run(colours, s, action="colour_name", colour="3fa9ff")
    assert near.startswith("#3fa9ff is closest to") and near.card["kind"] == "art-palette"
    assert run(colours, s, action="colour_name", colour="Dark Gray").startswith("#a9a9a9 is dark grey")
    assert len(ac.NAMED) >= 138


# ---- photo effects ------------------------------------------------------------------------------------

@pytest.mark.parametrize("effect", photos.FILTERS)
def test_every_filter_saves_a_new_copy(s, tmp_path, effect):
    shown = run(photos, s, action="filter", folder="Personal/Holiday", filename="beach 0", effect=effect)
    assert is_file_card(shown)
    out = tmp_path / "Personal" / "Holiday" / f"beach 0 {effect}.jpg"
    assert out.exists() and Image.open(out).size == (80, 60)
    assert (tmp_path / "Personal" / "Holiday" / "beach 0.jpg").exists()


def test_filters_change_colours():
    red = Image.new("RGB", (40, 40), (200, 30, 30))
    assert photos.apply_filter(red, "invert").getpixel((5, 5)) == (55, 225, 225)
    r, g, b = photos.apply_filter(red, "sepia").getpixel((5, 5))
    assert r > g > b
    assert photos.apply_filter(red, "noir").mode == "L"
    corner, centre = (photos.vignette(Image.new("RGB", (100, 100), "white")).getpixel(p) for p in ((0, 0), (50, 50)))
    assert corner[0] < 100 and centre == (255, 255, 255)


def test_adjust_brightness_and_contrast(s):
    for how in photos.ADJUSTMENTS:
        assert is_file_card(run(photos, s, action="adjust", folder="Personal/Holiday", filename="half",
                                adjustment=how, amount=40))
    grey = Image.new("RGB", (4, 4), (100, 100, 100))
    assert photos.adjust(grey, "brighten", 50).getpixel((0, 0))[0] == 150
    assert photos.adjust(grey, "darken", 50).getpixel((0, 0))[0] < 100


def test_border_frame_and_rounded_corners(s, tmp_path):
    shown = run(photos, s, action="border", folder="Personal/Holiday", filename="beach 0", colour="black", width=10)
    im = Image.open(tmp_path / "Personal" / "Holiday" / "beach 0 border.jpg")
    assert is_file_card(shown) and im.size == (100, 80) and max(im.getpixel((2, 2))) < 20
    run(photos, s, action="border", folder="Personal/Holiday", filename="beach 0", style="polaroid", width=5)
    assert Image.open(tmp_path / "Personal" / "Holiday" / "beach 0 polaroid.jpg").size == (90, 85)
    shown = run(photos, s, action="rounded_corners", folder="Personal/Holiday", filename="beach 1", amount=20)
    im = Image.open(tmp_path / "Personal" / "Holiday" / "beach 1 rounded.png")
    assert shown.card["name"] == "beach 1 rounded.png" and im.mode == "RGBA"
    assert im.getpixel((0, 0))[3] == 0 and im.getpixel((50, 30))[3] == 255


def test_watermark(s, tmp_path):
    shown = run(photos, s, action="watermark", folder="Personal/Holiday", filename="half", text="© 2026 Me",
                position="centre", amount=80)
    assert is_file_card(shown) and (tmp_path / "Personal" / "Holiday" / "half watermarked.png").exists()
    with pytest.raises(ValueError):
        run(photos, s, action="watermark", folder="Personal/Holiday", filename="half", text=" ")


def test_crop_to_ratios(s, tmp_path):
    run(photos, s, action="crop", folder="Personal/Holiday", filename="half")
    assert Image.open(tmp_path / "Personal" / "Holiday" / "half square.png").size == (50, 50)
    run(photos, s, action="crop", folder="Personal/Holiday", filename="half", ratio="9:16", save_to="Ideas")
    assert Image.open(tmp_path / "Ideas" / "half 9x16.png").size == (28, 50)
    assert photos.crop(Image.new("RGB", (1000, 1000)), "16:9").size == (1000, 562)
    with pytest.raises(ValueError):
        photos.crop(Image.new("RGB", (10, 10)), "5:1")


def test_meme(s, tmp_path):
    shown = run(photos, s, action="meme", folder="Personal/Holiday", filename="beach 2",
                top_text="when the code", bottom_text="passes first time")
    im = Image.open(tmp_path / "Personal" / "Holiday" / "beach 2 meme.jpg")
    assert is_file_card(shown) and max(im.size) == 600
    assert any(min(p) > 230 for _, p in im.getcolors(1 << 20))  # white letters on blue
    with pytest.raises(ValueError):
        run(photos, s, action="meme", folder="Personal/Holiday", filename="beach 2")


def test_heic_is_refused_politely(s):
    with pytest.raises(ValueError, match="HEIC"):
        run(photos, s, action="filter", folder="Personal/Holiday", filename="iphone.heic", effect="sepia")


# ---- making things ------------------------------------------------------------------------------------

def test_pixel_art_editor(s):
    shown = run(create, s, action="pixel_art", size=32, colours=["red", "#00ff00"], save_to="personal")
    data = shown.card["data"]
    assert shown.card["kind"] == "art-pixel" and data["size"] == 32 and data["folder"] == "Personal"
    assert data["palette"] == ["#ff0000", "#00ff00"] and data["scale"] == 16
    assert len(run(create, s, action="pixel_art").card["data"]["palette"]) == 16
    with pytest.raises(ValueError):
        run(create, s, action="pixel_art", size=12)
    with pytest.raises(ValueError):
        run(create, s, action="pixel_art", save_to="Personal/Holiday")


def test_collage(s, tmp_path):
    shown = run(create, s, action="collage", folder="Personal/Holiday", gap=10, colour="black")
    assert is_file_card(shown) and "5 pictures" in shown
    im = Image.open(tmp_path / "Ideas" / "Collage.jpg")
    assert im.size == (3 * 600 + 4 * 10, 2 * 600 + 3 * 10)
    shown = run(create, s, action="collage", folder="Personal/Holiday", filenames=["beach 0", "beach 1"])
    assert Image.open(tmp_path / "Ideas" / "Collage (2).jpg").size == (2 * 600 + 3 * 16, 600 + 2 * 16)
    with pytest.raises(ValueError):
        run(create, s, action="collage", folder="Personal/Holiday", filenames=["beach 0"])


def test_wallpapers(s, tmp_path):
    shown = run(create, s, action="wallpaper", width=320, height=200)
    im = Image.open(tmp_path / "Ideas" / "Wallpaper starfield 320x200.png")
    assert is_file_card(shown) and im.size == (320, 200)
    assert all(r == g == b for _, (r, g, b) in im.getcolors(1 << 20))  # black and white stars by default
    lit = sum(n for n, p in im.getcolors(1 << 20) if p != (0, 0, 0))
    assert 0 < lit < 320 * 200 / 10  # mostly black sky
    run(create, s, action="wallpaper", style="gradient", width=100, height=50, colour="black", colour2="white",
        name="Fade")
    fade = Image.open(tmp_path / "Ideas" / "Fade.png")
    assert fade.getpixel((50, 0))[0] < 20 and fade.getpixel((50, 49))[0] > 235
    with pytest.raises(ValueError):
        run(create, s, action="wallpaper", width=100000, height=10)


def test_ascii_art(s, tmp_path):
    shown = run(create, s, action="ascii_art", folder="Personal/Holiday", filename="half", width=20)
    lines = shown.card["data"]["text"].split("\n")
    assert shown.card["kind"] == "art-ascii" and len(lines) == 5
    assert lines[0].startswith("    ") and lines[0].endswith("@@@@")  # dark blue left, white right
    assert create.ascii_text(Image.new("RGB", (10, 10), "white"), 10, False).startswith("@@@@@@@@@@")
    run(create, s, action="ascii_art", folder="Personal/Holiday", filename="half", save_to="Ideas")
    assert (tmp_path / "Ideas" / "ASCII half.txt").exists()


def test_moodboard(s):
    shown = run(create, s, action="moodboard", folder="Personal/Holiday")
    data = shown.card["data"]
    assert shown.card["kind"] == "art-moodboard" and len(data["items"]) == 5
    assert data["items"][0]["src"].startswith("/screen/file?path=Personal/Holiday/")
    assert 1 <= len(data["swatches"]) <= 6 and data["swatches"][0]["hex"].startswith("#")


def test_drawing_prompts(s):
    assert len(create.PROMPTS) == 60 and len(set(create.PROMPTS)) == 60
    one = run(create, s, action="drawing_prompt")
    assert one.startswith("Try this:") and one.card["kind"] == "list"
    three = run(create, s, action="drawing_prompt", count=3)
    assert len(three.card["items"]) == 3


# ---- QR codes -----------------------------------------------------------------------------------------

# A reference encoder's output for these (byte mode, level M, with the mask named).
HELLO_WORLD_MASK_4 = [
    "#######.##..#.#######", "#.....#....#..#.....#", "#.###.#..#.#..#.###.#", "#.###.#.#..#..#.###.#",
    "#.###.#.###.#.#.###.#", "#.....#.#..#..#.....#", "#######.#.#.#.#######", "........#..##........",
    "#...#.######.#####..#", "...#....#.###....####", "..######..##.##.#..#.", "#####...##...#.......",
    "#####.#.#.#.#.##..##.", "........#.#.####.#.##", "#######.###.#.#.##.#.", "#.....#..#.###.##..##",
    "#.###.#.##.#.##...##.", "#.###.#..#..#...##.##", "#.###.#..###...###...", "#.....#....#.#.......",
    "#######.#########.#.#",
]
EXAMPLE_COM_MASK_5 = [
    "#######...#.#.#...#######", "#.....#.###..##.#.#.....#", "#.###.#.##.#..#...#.###.#",
    "#.###.#.###..#..#.#.###.#", "#.###.#..##..#..#.#.###.#", "#.....#..#.#..#...#.....#",
    "#######.#.#.#.#.#.#######", "........##....###........", "#.....#.#...#....##..###.",
    ".###.#...#.#.#####.#####.", "#####.#.##...####..#.#.##", "##..##..####.#..#.##.#..#",
    "...######.#.##.##.##....#", "###.#...###....##..#...#.", "#.....##..###..#..####.##",
    "#.#.#..#####.....###.##.#", "#.#..##.####....#####.#..", "........#...###.#...#....",
    "#######...##....#.#.#...#", "#.....#.....##.##...#..#.", "#.###.#..##.#.#######.#.#",
    "#.###.#..##...#.###....##", "#.###.#..####..#.....##.#", "#.....#..#.#..####.##...#",
    "#######.###..##.#.#..#..#",
]


def rows(matrix):
    return ["".join("#" if d else "." for d in row) for row in matrix]


def test_qr_reed_solomon_matches_the_spec_example():
    # The 1-M "HELLO WORLD" data codewords and their error correction from the worked example of the standard.
    data = [32, 91, 11, 120, 209, 114, 220, 77, 67, 64, 236, 17, 236, 17, 236, 17]
    assert qr.rs_remainder(data, 10) == [196, 35, 39, 119, 235, 215, 231, 226, 93, 23]


def test_qr_format_and_version_bits():
    expected_m = ["101010000010010", "101000100100101", "101111001111100", "101101101001011",
                  "100010111111001", "100000011001110", "100111110010111", "100101010100000"]
    assert [format(qr.format_bits(m), "015b") for m in range(8)] == expected_m
    assert format(qr.version_bits(7), "018b") == "000111110010010100"
    assert format(qr.version_bits(10), "018b") == "001010010011010011"


def test_qr_sizes_capacity_and_patterns():
    assert [qr.capacity(v) for v in (1, 2, 5, 10)] == [16, 28, 86, 216]
    assert [qr.pick_version(n) for n in (1, 14, 15, 26, 213)] == [1, 1, 2, 2, 10]
    with pytest.raises(ValueError):
        qr.pick_version(214)
    m = qr.encode("x" * 150)
    assert len(m) == 49 and all(len(r) == 49 for r in m)  # version 8
    finder = ["#######", "#.....#", "#.###.#", "#.###.#", "#.###.#", "#.....#", "#######"]
    grid = rows(m)
    assert [r[:7] for r in grid[:7]] == finder and [r[-7:] for r in grid[:7]] == finder
    assert [r[:7] for r in grid[-7:]] == finder
    assert grid[6][8:41] == "#." * 16 + "#" and "".join(r[6] for r in grid)[8:41] == "#." * 16 + "#"
    assert grid[49 - 8][8] == "#"  # the dark module


def test_qr_matches_reference_matrices():
    assert rows(qr.encode("HELLO WORLD", mask=4)) == HELLO_WORLD_MASK_4
    assert rows(qr.encode("https://example.com", mask=5)) == EXAMPLE_COM_MASK_5
    assert len(qr.encode("https://example.com")) == 25


def test_qr_tool_saves_a_png(s, tmp_path):
    shown = run(qr, s, text="https://example.com")
    im = Image.open(tmp_path / "Ideas" / "QR https example.com.png")
    assert is_file_card(shown) and im.size == ((25 + 8) * 10,) * 2
    assert im.getpixel((45, 45)) == (0, 0, 0) and im.getpixel((5, 5)) == (255, 255, 255)
    with pytest.raises(ValueError):
        run(qr, s, text="")


def test_registered_and_small():
    names = {t["name"] for t in tools.client_tool_definitions(Settings())}
    assert {"art_colours", "art_photo_effects", "art_create", "art_qr_code"} <= names
    for module in (colours, photos, create, qr):
        for tool in module.tool_definitions():
            assert tool["input_schema"]["additionalProperties"] is False


def test_through_run_tool(s):
    out = asyncio.run(tools.run_tool("art_colours", {"action": "colour_name", "colour": "#ff0000"}, s, None))
    assert "red" in str(out)
