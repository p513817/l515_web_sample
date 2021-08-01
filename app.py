from flask import Flask, Response,jsonify, render_template,request
import cv2
import numpy as np
import time
from l500 import L515
import sys
import json

print('Load Flask')
app = Flask(__name__)

print('Load Intel RealSense...')
l515 = L515()
l515.start_stream()
# 'color', 'depth', 'cnt_depth', 'clip', 'cursor_depth'
cam_stats = False
app_mode = 'color'
sec_mode = 'depth'
cursor = [320, 240]
clip_limit = 100

def get_target_depth(frame, position=(320,240)):
    
    (x,y) = position
    x,y = int(x), int(y)

    depth = l515.get_depth(x,y)
    text = f'Depth: {depth*100:.3f} (cm)'

    cv2.circle(frame, (x,y), 3, (0,0,255), 2)
    cv2.putText(frame, text, (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1, cv2.LINE_AA)

    return frame    

def get_cursor_mode():
    global cursor
    frame = l515.color_image if sec_mode=='color' else l515.depth_image
    return get_target_depth(frame, cursor)

    
def clipping_mode():
    global clip_limit
    clip_meter = clip_limit/100
    return l515.clipping_bg(clip_distance=clip_meter, bg_color=155)

def gen_frame():
    global app_mode,cam_stats
    
    while(True):
        
        if not cam_stats: 

            img = cv2.imread('./images/no_frame.jpg')

            ret, jpg = cv2.imencode('.jpg', img )

            yield (b'--frame\r\n' + 
                b'Content-Type: image/jpeg\r\n\r\n' + 
                jpg.tobytes() + 
                b'\r\n')

        else:

            if app_mode == 'color':
                frame = l515.color_image

            elif app_mode =='depth':
                frame = l515.depth_image
            
            elif app_mode =='cursor_depth':
                frame = get_cursor_mode()

            elif app_mode =='clip':
                frame = clipping_mode()
            
            else:
                continue

            ret, jpg = cv2.imencode('.jpg', frame )

            yield (b'--frame\r\n' + 
                b'Content-Type: image/jpeg\r\n\r\n' + 
                jpg.tobytes() + 
                b'\r\n')


@app.route("/")
def main():
    return render_template(r"video_stream.html")

@app.route("/_camStats") 
def camera_ctrl():
    global cam_stats
    cam_stats = 1 if not cam_stats else 0
    return jsonify(stats=cam_stats)

@app.route("/_colorMode") 
def color_mode():
    global app_mode
    app_mode = 'color'
    return jsonify(None)

@app.route("/_depthMode") 
def depth_mode():
    global app_mode
    app_mode = 'depth'
    return jsonify(None)

@app.route("/_clipMode") 
def clip_mode():
    global app_mode
    app_mode = 'clip'
    return jsonify(None)

@app.route("/_clipDistance", methods=["POST","GET"])
def clip_distance():
    global clip_limit
    clip_limit = int(request.get_json())
    return jsonify(clip_limit)

@app.route("/_cursorDepthMode") 
def cursor_mode():
    global app_mode, sec_mode
    app_mode = 'cursor_depth'
    sec_mode='depth' if sec_mode=='color' else 'color'
    return jsonify(None)

@app.route("/_feedFrame") 
def feed_frame():
    return Response(gen_frame(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route("/_cursorPos", methods = ['POST'])
def get_cursor_pos():
    global cursor
    cursor = list(request.get_json().values())
    return json.dumps({'success':True}), 200, {'ContentType':'application/json'} 

@app.route("/_quit", methods=['GET'])
def quit():
    l515.stop_stream()
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()
    return jsonify('Web App Shutdown')

# @app.route("/res")
# def get_res():
#     global face_nums
#     return jsonify(result=face_nums)


if __name__ == '__main__':
    try:
        app.run(host="0.0.0.0")
    except:
        sys.exit()