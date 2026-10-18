"""生成 MailPull 应用图标 (无第三方依赖, 手写 ICO)。"""
import struct, os

SIZE = 256

def rounded_rect_px(x, y, x0, y0, w, h, r):
    """判断 (x,y) 是否在圆角矩形内。"""
    if x < x0 or x > x0 + w or y < y0 or y > y0 + h:
        return False
    cx = min(max(x, x0 + r), x0 + w - r)
    cy = min(max(y, y0 + r), y0 + h - r)
    return (x - cx) ** 2 + (y - cy) ** 2 <= r * r

def render():
    """渲染 RGBA 像素: 深色圆角底 + 蓝色信封 + 白色信封盖 + 绿色勾。"""
    px = []
    x0, y0 = 8, 8
    w = h = SIZE - 16
    r = 52
    # 信封主体坐标
    ex0, ey0, ew, eh = 52, 84, 152, 104

    for y in range(SIZE):
        row = []
        for x in range(SIZE):
            if not rounded_rect_px(x, y, x0, y0, w, h, r):
                row.append((0, 0, 0, 0))
                continue
            # 底色: 深蓝紫渐变
            t = (x + y) / (SIZE * 2)
            br = int(30 + t * 30)
            bg = int(41 + t * 60)
            bb = int(92 + t * 90)
            R, G, B = br, bg, bb

            # 信封白底
            if ex0 <= x <= ex0 + ew and ey0 <= y <= ey0 + eh:
                R, G, B = 240, 246, 255
                # 信封盖(倒 V 形折线)
                rel = (y - ey0) / eh
                lineY = ey0 + 46 - abs(x - (ex0 + ew / 2)) * 0.62
                if abs(y - lineY) < 7 and y < ey0 + 58:
                    R, G, B = 88, 130, 220
                # 信封底边线
                if abs(y - (ey0 + eh - 12)) < 3:
                    R, G, B = 210, 220, 238

            # 右下角绿色圆点(在线状态点)
            if (x - 208) ** 2 + (y - 208) ** 2 <= 30 ** 2:
                R, G, B = 52, 199, 123
                if (x - 208) ** 2 + (y - 208) ** 2 <= 22 ** 2:
                    R, G, B = 92, 230, 158
            row.append((R, G, B, 255))
        px.append(row)
    return px

def write_ico(px, path):
    """写 ICO: 内嵌一张 256x256 PNG(用 zlib 手工编码, 无 PIL)。"""
    import zlib
    raw = b""
    for row in px:
        raw += b"\x00" + b"".join(bytes(p) for p in row)
    comp = zlib.compress(raw, 9)

    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xffffffff)

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0))
           + chunk(b"IDAT", comp)
           + chunk(b"IEND", b""))

    header = struct.pack("<HHH", 0, 1, 1)
    # 256x256 在 ICO 目录里编码为 0
    entry = struct.pack("<BBBBHHII", 0 if SIZE >= 256 else SIZE, 0 if SIZE >= 256 else SIZE,
                        0, 0, 1, 32, len(png), 22)
    with open(path, "wb") as f:
        f.write(header + entry + png)

def write_png(px, path):
    """同时输出 PNG 预览图。"""
    import zlib
    raw = b""
    for row in px:
        raw += b"\x00" + b"".join(bytes(p) for p in row)
    comp = zlib.compress(raw, 9)

    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xffffffff)

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0))
           + chunk(b"IDAT", comp)
           + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)

if __name__ == "__main__":
    px = render()
    here = os.path.dirname(os.path.abspath(__file__))
    ico = os.path.join(here, "logo.ico")
    png = os.path.join(here, "logo.png")
    write_ico(px, ico)
    write_png(px, png)
    print(f"已生成: {ico}")
    print(f"已生成: {png}")