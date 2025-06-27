import cv2
import queue
import threading
import json
import warnings
import multiprocessing
from time import sleep
from datetime import datetime, timedelta

from simple_pid import PID
from ultralytics import YOLO
# from pygame.locals import *
from djitellopy import Tello
with warnings.catch_warnings(action="ignore"):
    from RealtimeSTT import AudioToTextRecorder

from textToCommand import TextToCommand
from tts2 import play_text_to_speech
from window import CWMManager
from DeviceControllers import Radio

flight_mode = None

# --- Configuration (These are safe in global scope) ---
ttc_manager = TextToCommand()
model = YOLO("yolo11n-pose.pt")

# --- Event to signal threads to stop (Safe in global scope) ---
stop_event = threading.Event()

# --- PID Controllers ---
pid_cc = PID(0.25, 0.2, 0.2, setpoint=0, output_limits=(-70, 70))
pid_ud = PID(0.3, 0.3, 0.3, setpoint=0, output_limits=(-80, 80))
pid_fb = PID(0.35,0.2,0.3, setpoint=0, output_limits=(-50, 50))

# KEYPOINT_DICT = {
#    0: "nose",
#    1: "left_eye",
#    2: "right_eye",
#    3: "left_ear",
#    4: "right_ear",
#    5: "left_shoulder",
#    6: "right_shoulder",
#    7: "left_elbow",
#    8: "right_elbow",
#    9: "left_wrist",
#    10: "right_wrist",
#    11: "left_hip",
#    12: "right_hip",
#    13: "left_knee",
#    14: "right_knee",
#    15: "left_ankle",
#    16: "right_ankle",
# }

# Define connections for drawing the skeleton
# This is a list of tuples, where each tuple represents a connection between two keypoints (by index)
POSE_CONNECTIONS = [
   # Face
   (0, 1), (0, 2), (1, 3), (2, 4),
   # Torso
   (5, 6), (5, 11), (6, 12), (11, 12),
   # Left Arm
   (5, 7), (7, 9),
   # Right Arm
   (6, 8), (8, 10),
   # Left Leg
   (11, 13), (13, 15),
   # Right Leg
   (12, 14), (14, 16)
]

# --- Drawing Parameters ---
MIN_DRAW_CONFIDENCE = 0.3 # Only draw keypoints/lines if confidence is above this
POINT_COLOR = (0, 255, 0) # Green for keypoints
LINE_COLOR = (255, 0, 0)  # Blue for skeleton lines
POINT_RADIUS = 3
LINE_THICKNESS = 2

# Drone control inputs
drone_cc = 0
drone_ud = 0
drone_fb = 0

# FOR FOLLOW MODE
def process_frame(results, overlay_image):
    """Processes a single frame for pose estimation and control updates."""
    global drone_cc, drone_ud, drone_fb, pid_cc, pid_ud, pid_fb
    # image = cv2.resize(image, (640, 480))
    
    # Run YOLO Pose Estimation
    # results = model(image, stream=False, verbose=False)
    
    largest_person_area = 0
    largest_person_keypoints = None
    if results:
        if results[0].keypoints and results[0].boxes:
            for i in range(len(results[0].keypoints.xy)):
                area = (results[0].boxes.xywh[i][2] * results[0].boxes.xywh[i][3]).item()
                if area > largest_person_area:
                    largest_person_area = area
                    largest_person_keypoints = results[0].keypoints.data[i]
                

    if largest_person_keypoints is not None:
        kpts = largest_person_keypoints.cpu().numpy()
        sees_body = False
        for i in range(kpts.shape[0]): # Iterate through all 17 keypoints
           x, y, conf = kpts[i]
           if conf > MIN_DRAW_CONFIDENCE:
               if i >= 6:
                   sees_body=True
               cv2.circle(overlay_image, (int(x), int(y)), POINT_RADIUS, POINT_COLOR, -1) # -1 means fill the circle


        centerx = int(overlay_image.shape[1] / 2)
        centery = int(overlay_image.shape[0] / 3)
        
        nosex, nosey, nose_conf = kpts[0]
        if nose_conf > MIN_DRAW_CONFIDENCE:
            cv2.line(overlay_image, (centerx, centery - 10), (int(nosex), int(nosey)), (255, 255, 0), 2)
            errorx = nosex - centerx
            errory = (centery - 10) - nosey
            drone_cc = int(pid_cc(errorx)) if abs(errorx) > 20 else 0
            drone_ud = int(pid_ud(errory)) if abs(errory) > 20 else 0
        else:
            if sees_body:
                drone_ud=-50
                print("moving up")
            else:
                drone_cc, drone_ud = 0, 0
                pid_cc.reset()
                pid_ud.reset()

        left_sh_x, _, left_sh_conf = kpts[6]
        right_sh_x, _, right_sh_conf = kpts[7]
        if left_sh_conf > MIN_DRAW_CONFIDENCE and right_sh_conf > MIN_DRAW_CONFIDENCE:
            shoulder_dist = abs(left_sh_x - right_sh_x)
            desired_dist = 150
            errorFB = desired_dist - shoulder_dist
            drone_fb = int(pid_fb(errorFB)) if abs(errorFB) > 25 else 0

        else:
            drone_fb = 0
            pid_fb.reset()
    else:
        drone_cc, drone_ud, drone_fb = 0, 0, 0
        pid_cc.reset()
        pid_ud.reset()
        pid_fb.reset()

def vision_thread(tello, frame_read, last_frame, drone_state):
    """
    Displays video frames received from the control thread.
    """
    print("Vision thread started")
    pdrone_cc, pdrone_ud, pdrone_fb = -111, -111, -111
    last_frame_save = datetime.now()
    while not stop_event.is_set():
        try:
            frame = frame_read.frame
            if frame is not None:
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR) # convert from RGB to BGR
                # The frame from frame_read is BGR, not RGB.
                with thread_lock: # Acquire lock to safely write to shared memory
                    last_frame["frame"] = frame
                results = model.track(frame, persist=True, verbose=False)
                # annotated_frame = results[0].plot()
                
                with thread_lock:
                    flight_mode = drone_state["flight_mode"]

                if flight_mode == "follow":
                    process_frame(results, frame)
                    # Check if any control input has changed to avoid sending redundant commands
                    if pdrone_cc != drone_cc or pdrone_ud != drone_ud or pdrone_fb != drone_fb:
                        # Correct order: left_right, forward_backward, up_down, yaw
                        # Using 0 for left_right as you don't calculate it
                        # Applying sign changes based on PID error direction vs Tello's velocity convention
                        tello.send_rc_control(0, -drone_fb, -drone_ud, -drone_cc) # <--- CRITICAL CHANGE
                        pdrone_cc = drone_cc
                        pdrone_ud = drone_ud
                        pdrone_fb = drone_fb

                cv2.imshow('Drone', frame)

            if cv2.waitKey(1) & 0xFF == 27: # ESC key
                print("ESC key pressed. Shutting down.")
                stop_event.set()
                break
        except Exception as e:
            # This will catch the decoding errors and others
            print(f"Skipping a bad frame in vision_thread: {e}")
            # Continue to the next iteration to get a new frame
            continue

    cv2.destroyAllWindows()
    print("Vision thread finished")

def keep_alive_thread(tello):
    print("Keep alive thread started")
    while not stop_event.is_set():
        tello.send_control_command("command")
        sleep(3)


def command_thread(tello, command_queue, drone_state):
    """
    Manages commands.
    """
    print("Control thread started")
    radio = Radio("192.168.132.1")
    while not stop_event.is_set():
        try:
            command = command_queue.get(timeout=1) # Use a timeout to avoid busy-waiting
            print(f"Control thread received command: {command}")
            
            command_type = command['type']

            if command_type == "query" or command_type == "action":

                command_name = command['command']
                params = command['params']  
                params["self"] = tello

                if command_name == "follow":
                    with thread_lock:
                        drone_state["flight_mode"] = "follow"
                    continue

                method_to_call = getattr(Tello, command_name)
                response = method_to_call(**params)
                if response:
                    print("Command reponse: ", response)

                if command_name == "takeoff":
                    with thread_lock:
                        drone_state["flight_mode"] = "hover"

                if command_name == "land":
                    with thread_lock:
                        drone_state["flight_mode"] = "land"

                if command_name == "follow":
                    with thread_lock:
                        drone_state["flight_mode"] = "follow"

            elif command_type == "memory_question":
                print("MEMORY RESPONSE:")
                response = command['response']
                print(response)
                play_text_to_speech(response, radio)
            else:
                print("UNSUPPORTED COMMAND TYPE")

        except queue.Empty:
            # No command received, continue loop
            pass
        except Exception as e:
            print(f"Error in command_thread: {e}")
            stop_event.set()
    print("Control thread finished")

def process_text(text, command_queue, shared_memory):
    print(f"Processing text: {text}")
    with thread_lock: # Acquire lock to safely read from shared memory
        latest_cwm = shared_memory['cwm_data']
    response = ttc_manager.get_drone_api_command(text, latest_cwm)
    print("\n", response)

    if "json" in response:
        try:
            cleaned_string = response.strip().removeprefix("```json")
            cleaned_string = cleaned_string.removesuffix("```")
            cleaned_string = cleaned_string.strip()

            command = json.loads(cleaned_string)

            command_queue.put(command)
        except (json.JSONDecodeError, TypeError):
            # Handle cases where the response is not valid JSON
            print(f"Could not decode command from response: {response}")


def speech_thread(command_queue, shared_memory):
    """
    Listens for speech and puts recognized commands into the command queue.
    """
    print("Speech thread started")
    try:
        recorder = AudioToTextRecorder(language="en", no_log_file=True, spinner=True)
        print("STT initialized")
        while not stop_event.is_set():
            print("STT Listening")
            text = recorder.text()
            print("Transcription: ", text)
            process_text(text, command_queue, shared_memory)

    except Exception as e:
        print(f"Error in speech thread: {e}")
    finally:
        print("Speech thread finished")
        stop_event.set() # Ensure other threads know to stop if speech thread fails

def memory_thread(shared_memory, last_frame):
    """
    This thread periodically calls get_updated_cwm and stores the result
    in a thread-safe shared memory object.
    """
    print("Memory thread started")
    cwm_manager = CWMManager()
    while not stop_event.is_set():
        # --- Update the shared memory ---
        with thread_lock: # Acquire lock to safely write to shared memory
            frame = last_frame["frame"]
        cv2.imwrite("last_frame.png", frame) 

        new_data = cwm_manager.get_updated_cwm("last_frame.png")

        with thread_lock: # Acquire lock to safely write to shared memory
            shared_memory['cwm_data'] = new_data
        
        print(f"MEMORY THREAD: CWM data has been updated.")
        # --- End of critical section ---

        # Wait for the next update interval, but exit immediately if stop_event is set
        stop_event.wait(timeout=1)

    print("Memory thread finished")


if __name__ == "__main__":
    try:
        # --- Thread-safe Queues for Communication ---
        command_queue = queue.Queue()

        # --- Shared Memory for CWM data with a Lock for thread-safe access ---
        thread_lock = threading.Lock()

        shared_memory = {'cwm_data': 'No data yet.'}
        last_frame = {'frame': None}
        drone_state = {"flight_mode": "land"}


        # --- Tello Initialization ---
        tello = Tello()
        tello.connect()
        tello.streamon()
        frame_read = tello.get_frame_read()
        print("Battery Level:", tello.get_battery())

        # Create and start the threads
        vision = threading.Thread(target=vision_thread, args=(tello, frame_read, last_frame, drone_state))
        control = threading.Thread(target=command_thread, args=(tello, command_queue, drone_state))
        keep_alive = threading.Thread(target=keep_alive_thread, args=(tello,))
        speech = threading.Thread(target=speech_thread, args=(command_queue, shared_memory))
        memory = threading.Thread(target=memory_thread, args=(shared_memory, last_frame))

        vision.start()
        control.start()
        keep_alive.start()
        speech.start()
        memory.start()


        # Wait for all threads to complete
        vision.join()
        control.join()
        keep_alive.join()
        speech.join()
        memory.join()

        print("All threads have been terminated.")

        print("Landing drone.")
        tello.land()
        tello.streamoff()
    except KeyboardInterrupt:
        print("SHUTTING DOWN")
        stop_event.set()