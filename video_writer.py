import subprocess
import numpy as np
from utils import FPS,info

class VideoWriter:
    
    def __init__(self, output_file, size):
        self.output_file = output_file
        self.width, self.height = size
        
        # FFmpeg命令
        self.cmd = [
            'ffmpeg',
            '-y',  # 覆盖输出文件
            '-f', 'rawvideo',  # 输入格式：原始视频
            '-vcodec', 'rawvideo',  # 输入编码：原始视频
            '-pix_fmt', 'rgb24',  # PIL使用RGB
            '-s', f'{self.width}x{self.height}',  # 分辨率
            '-r', str(FPS),  # 帧率
            '-i', '-',  # 从标准输入读取
            '-c:v', 'libx264',  # 视频编码器
            '-preset', 'slow',  # 编码速度预设
            '-crf', '20',  # 质量参数（0-51，越小质量越好）
            '-pix_fmt', 'yuv420p',  # 输出像素格式（兼容性更好）
            '-f', 'mp4',  # 输出格式
            self.output_file
        ]
        
        # 启动进程
        self.proc = subprocess.Popen(
            self.cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        self.frame_count = 0
    
    def write(self, frame):
        """
        写入一帧
        
        Args:
            frame: numpy数组，RGB格式
        """
        
        # 写入到ffmpeg
        self.proc.stdin.write(frame.tobytes())
        self.frame_count += 1
    
    def release(self):
        """释放资源"""
        if self.proc.stdin:
            self.proc.stdin.close()
        
        self.proc.wait()
        info(f"已保存 {self.frame_count} 帧到 {self.output_file}")

from tkinter import filedialog
if __name__ == "__main__":
    
    output_file = filedialog.asksaveasfilename(
        title="保存为",
        defaultextension=".mp4",
        filetypes=[("MP4 文件", "*.mp4")],
    )

    # 创建写入器
    writer = VideoWriter(output_file, size=(640, 480))
    
    # 生成100帧
    for i in range(100):
        # 创建彩色帧
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # 随时间变化颜色
        r = int((i / 100) * 255)
        g = int(((100 - i) / 100) * 255)
        b = 128
        
        frame[:, :] = [r, g, b]  # OpenCV是BGR顺序
        
        # 写入帧
        writer.write(frame)
    
    # 保存
    writer.release()