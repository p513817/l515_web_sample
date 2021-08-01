## License: Apache 2.0. See LICENSE file in root directory.
## Copyright(c) 2015-2017 Intel Corporation. All Rights Reserved.

###############################################
##      Open CV and Numpy integration        ##
###############################################

import pyrealsense2 as rs
import numpy as np
import cv2
import sys
import threading
import time

class L515():

    def __init__(self):

        # 初始化
        self.pipeline = rs.pipeline()
        self.config = rs.config()

        # 開啟攝影機並允許串流
        self.config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
        # self.config.enable_stream(rs.stream.color, 960, 540, rs.format.bgr8, 30)
        self.config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
        self.profile = self.pipeline.start(self.config)

        #
        self.stream = threading.Thread(target=self.update_frame)
        self.flag = 1

        # rs.align 讓 深度圖像 跟 其他圖像 對齊
        align_to = rs.stream.color
        self.align = rs.align(align_to)

        # 存放影像的變數
        self.depth_frame, self.color_frame = [], []
        self.depth_numpy, self.color_numpy = [], []
        self.depth_image, self.color_image = [], []
    
    def update_frame(self):
        ### 01 ###
        while self.flag:
            ### 02 ###
            frames = self.pipeline.wait_for_frames()
            aligned_frames = self.align.process(frames)
            
            self.depth_frame = aligned_frames.get_depth_frame()
            self.color_frame = aligned_frames.get_color_frame()
            
            if not self.depth_frame or not self.color_frame: return None

            ### 03 ###
            # convert to cv2 from pipeline
            self.color_numpy = np.asanyarray(self.color_frame.get_data()) 
            self.depth_numpy = np.asanyarray(self.depth_frame.get_data())

            # 統一用法，雖然浪費資源但是能夠統一用法
            self.color_image = self.color_numpy
            self.depth_image = cv2.applyColorMap(cv2.convertScaleAbs(self.depth_numpy, alpha=0.03), cv2.COLORMAP_JET)

    def get_depth(self, x, y):
        return self.depth_frame.get_distance(x,y) 

    def clipping_bg(self, clip_distance=1, bg_color=153):

        # 將 公尺資訊 轉換成 RealSense 的 深度單位
        depth_sensor = self.profile.get_device().first_depth_sensor()
        depth_scale = depth_sensor.get_depth_scale()

        # 去背距離、背景顏色         
        clipping_distance = (clip_distance / depth_scale)
        bg_color = bg_color

        # 取得前景
        depth_image_3d = np.dstack((self.depth_numpy, self.depth_numpy, self.depth_numpy)) 
        bg_removed = np.where((depth_image_3d > clipping_distance) | (depth_image_3d <= 0), bg_color, self.color_numpy)

        return bg_removed

    def start_stream(self):
        print(f"Start Stream ... " , end='\n')
        self.stream.start()
        time.sleep(1)
        
    def stop_stream(self):
        print("Stop Stream ...")
        self.flag = 0
        print("Clean RS Camera")
        self.pipeline.stop()

        if not self.stream.is_alive(): print("Stream Killed")

if __name__ == "__main__":

    l515 = L515()

    l515.start_stream()

    mode = {0:'color', 1:'depth'}

    while True:

        frame = l515.color_image if mode=='color' else l515.depth_image

        cv2.imshow('Test', frame)

        key = cv2.waitKey(1)

        if key==ord('q'): break
        elif key==ord(' '): mode = not mode
        else: continue

    l515.stop_stream()