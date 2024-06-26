import cv2
import numpy as np
import threading
import time
import queue

import random

from deepface import DeepFace
from vision.AiManager import AiManager
from vision.DataManager import DataManager
 
mongo = DataManager()

aimanager = AiManager(3)


shared_queue = queue.Queue()

def process_frame(frame):
    h, w = frame.shape[:2]
    blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)), 1.0, (300, 300), (104.0, 177.0, 123.0))
    aimanager.face_detector.setInput(blob)
    detections = aimanager.face_detector.forward()

    e = {
            'happy': 0,
            'sad': 0,
            'angry': 0,
            'surprise': 0,
            'fear': 0,
            'neutral': 0,
            'disgust': 0
        }

    for i in range(detections.shape[2]):
        confidence = detections[0, 0, i, 2]
        if confidence > 0.5:
            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
            (x, y, x1, y1) = box.astype("int")
            face_roi = frame[y:y1, x:x1]

            # Perform emotion analysis on the face ROI
            result = DeepFace.analyze(face_roi, actions=['emotion'], enforce_detection=False)
            # Determine the dominant emotion
            e[result[0]['dominant_emotion']] += 1

    # Código de deepface
    shared_queue.put(e)

    print("Processing frame in a separate thread")

def data_process(dic):
    print("Sending data in other frame")

    random_number = random.randint(1, 15)

    if random_number == 1:
        mongo.post_data(dic)
        print("Data sent to MongoDB")
    print(dic)



if __name__ == '__main__':

    cap = cv2.VideoCapture(1)

    frame_counter_haar = 0
    frame_counter_deep = 0

    #manager.start_threads()

    bboxes = None

    fo = 0
    dis = 0

    while True:

        p, img = cap.read()

        if not p:
            break

        frame_counter_haar += 1
        frame_counter_deep += 1



        #img = cv2.resize(img, (w, h))

        if frame_counter_haar == 5:

            bboxes, fo, dis = aimanager.findFace(img)
            frame_counter_haar = 0

        if frame_counter_deep == 20:
            threading.Thread(target=process_frame, args=(img.copy(),)).start()

            data = {"timestamp": int(time.time()), "focused": fo, "distracted": dis}
            data_fromthread = shared_queue.get()

            combined_dict = {}


            for key, value in data.items():
                combined_dict[key] = value


            for key, value in data_fromthread.items():
                combined_dict[key] = value



            threading.Thread(target=data_process, args=(combined_dict,)).start()

            frame_counter_deep = 0

        if bboxes is not None:
            for (x, y, w, h) in bboxes:
                cv2.rectangle(img, (x, y), (x + w, y + h), (0, 0, 255), 2)

        cv2.imshow("Output", img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break


    #manager.wait_for_threads()
    cap.release()
    cv2.destroyAllWindows()
