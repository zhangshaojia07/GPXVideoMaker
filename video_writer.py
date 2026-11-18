import subprocess
import numpy as np
from utils import FPS,info

class VideoWriter:
    
    def __init__(self, output_file, size):
        self.output_file = output_file
        self.width, self.height = size
        
        # FFmpeg command
        self.cmd = [
            'ffmpeg',
            '-y',  # overwrite the output file
            '-f', 'rawvideo',  # input format: raw video
            '-vcodec', 'rawvideo',  # input codec: raw video
            '-pix_fmt', 'rgb24',  # PIL uses RGB
            '-s', f'{self.width}x{self.height}',  # resolution
            '-r', str(FPS),  # frame rate
            '-i', '-',  # read from stdin
            '-c:v', 'libx264',  # video codec
            '-preset', 'slow',  # encoding speed preset
            '-crf', '20',  # quality parameter (0-51, lower is better)
            '-pix_fmt', 'yuv420p',  # output pixel format (better compatibility)
            '-f', 'mp4',  # output format
            self.output_file
        ]
        
        # Start the process
        self.proc = subprocess.Popen(
            self.cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        self.frame_count = 0
    
    def write(self, frame):
        """
        Write one frame.

        Args:
            frame: numpy array in RGB format.
        """
        
        # Write to ffmpeg
        self.proc.stdin.write(frame.tobytes())
        self.frame_count += 1
    
    def release(self):
        """Release resources."""
        if self.proc.stdin:
            self.proc.stdin.close()
        
        self.proc.wait()
        info(f"Saved {self.frame_count} frames to {self.output_file}")

from tkinter import filedialog
if __name__ == "__main__":
    
    output_file = filedialog.asksaveasfilename(
        title="Save As",
        defaultextension=".mp4",
        filetypes=[("MP4 Files", "*.mp4")],
    )

    # Create the writer
    writer = VideoWriter(output_file, size=(640, 480))
    
    # Generate 100 frames
    for i in range(100):
        # Create a colored frame
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Change the color over time
        r = int((i / 100) * 255)
        g = int(((100 - i) / 100) * 255)
        b = 128
        
        frame[:, :] = [r, g, b]  # OpenCV uses BGR order
        
        # Write the frame
        writer.write(frame)
    
    # Save
    writer.release()