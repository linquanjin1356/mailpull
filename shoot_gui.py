"""启动 GUI 并截图,用于验证界面渲染效果(处理 DPI 缩放)。"""
import sys, time, ctypes
import tkinter as tk

def enable_dpi_awareness():
    """让进程感知 DPI,否则 winfo 坐标与物理像素不一致。"""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PER_MONITOR_DPI_AWARE
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

def shoot():
    enable_dpi_awareness()
    root = tk.Tk()
    root.withdraw()
    import mailpull_gui as g
    app = g.App(root)
    root.deiconify()
    root.lift()
    root.geometry("+180+70")
    try:
        root.attributes("-topmost", True)
        root.update()
    except Exception:
        pass
    for _ in range(14):
        root.update()
        time.sleep(0.4)

    root.update_idletasks()
    x, y = root.winfo_rootx(), root.winfo_rooty()
    w, h = root.winfo_width(), root.winfo_height()
    print("逻辑坐标:", x, y, w, h)

    # 换算成物理像素
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    from PIL import ImageGrab
    img = ImageGrab.grab()
    # 按缩放比例裁剪窗口区域
    sx = img.width / ctypes.windll.user32.GetSystemMetrics(0)
    sy = img.height / ctypes.windll.user32.GetSystemMetrics(1)
    print(f"缩放: {sx:.2f}x{sy:.2f}  屏幕: {img.width}x{img.height}")
    box = (int(x * sx), int(y * sy), int((x + w) * sx), int((y + h) * sy))
    img = img.crop(box)
    #限制尺寸,避免过大
    if img.width > 1280:
        img = img.resize((1280, int(img.height * 1280 / img.width)))
    img.save("gui_screenshot.png")
    print("saved", img.size)
    root.destroy()

if __name__ == "__main__":
    shoot()