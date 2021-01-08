import base64
import urllib.parse
import requests
import json
import timeit
import time
import sys
import io
import cv2
import numpy as np
import re
import traceback
import os 
import random
import logging
import string
import zipfile
import shutil
from datetime import datetime

from configparser import SafeConfigParser
from utils import rcode

from unidecode import unidecode
from recognizers_text import Culture, ModelResult
from recognizers_date_time import DateTimeRecognizer
from Levenshtein import *
import codecs
import unidecode

from shapely.geometry import Point, Polygon
from preprocess import checkmonth, replace_char_to_number
from preprocess import LIST_FIRSTNAME_PREPROCESS, LIST_MIDNAME_PREPROCESS

from Matchfield import bankMatch, firstnameMatch, midnameMatch, typecardMatch
  
from flask import Flask, render_template, jsonify, request, Response, send_from_directory
from flask_restful import Resource, Api
from flask_cors import CORS

#####LOAD CONFIG####
config = SafeConfigParser()
config.read("config/services.cfg")
LOG_PATH = str(config.get('main', 'LOG_PATH'))
SERVER_IP = str(config.get('main', 'SERVER_IP'))
SERVER_PORT = int(config.get('main', 'SERVER_PORT'))
UPLOAD_FOLDER = str(config.get('main', 'UPLOAD_FOLDER'))
RESULT_FOLDER = str(config.get('main', 'RESULT_FOLDER')) 

if not os.path.exists(LOG_PATH):
    os.mkdir(LOG_PATH)

if not os.path.exists(UPLOAD_FOLDER):
    os.mkdir(UPLOAD_FOLDER)

if not os.path.exists(RESULT_FOLDER):
    os.mkdir(RESULT_FOLDER)

#####CREATE LOGGER#####
logging.basicConfig(filename=os.path.join(LOG_PATH, str(time.time())+".log"), filemode="w", level=logging.DEBUG, format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
console = logging.StreamHandler()
console.setLevel(logging.ERROR)
logging.getLogger("").addHandler(console)
logger = logging.getLogger(__name__)
#######################################
app = Flask(__name__, template_folder="templates", static_folder="static")

model = DateTimeRecognizer(Culture.English).get_datetime_model()


def get_box(info_box):
    bbox = info_box['box']
    text = info_box['text']
    point0 = bbox['point0']
    point1 = bbox['point1']
    point2 = bbox['point2']
    point3 = bbox['point3']

    point0 = [point0['x'], point0['y']]
    point1 = [point1['x'], point1['y']]
    point2 = [point2['x'], point2['y']]
    point3 = [point3['x'], point3['y']]

    bbox = [point0, point1, point2, point3]

    return bbox, text

def draw_box(image, bbox, color=(0,0,255)):
    # pts = np.array([[xs_af[0],ys_af[0]],[xs_af[1],ys_af[1]],[xs_af[2],ys_af[2]],[xs_af[3],ys_af[3]]], np.int32)
    pts = np.array(bbox)
    pts = pts.reshape((-1,1,2))
    image = cv2.polylines(image,[pts],True, color)

    return image 

def write_text(image, text, x, y):
    image = cv2.putText(image, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 2)

    return image

def draw_bankcard(image, my_predict):
    list_info_bankcard = []
    list_flag_bbox = []
    for info_predict in my_predict:
        bbox, text = get_box(info_predict)
        image = draw_box(image, bbox)
        image = write_text(image, text, bbox[0][0]+2, bbox[0][1]-3)
        list_info_bankcard.append([bbox, text])
        list_flag_bbox.append(False)
    
    return image, list_info_bankcard, list_flag_bbox

def extractTimestamp(raw_input):
    res = model.parse(raw_input)
    res = [x for x in res if (len(x.text) != 4 or (not x.text.isdigit))]
    res = [x for x in res if x.text!='thu' and (x.text[-1]!='p' or x.text[:-1].isdigit()==False)]
    if len(res) == 0:
        return None
    # for x in res:
    #   print(x.text)
    st = res[0].start
    en = res[-1].end 
    result = raw_input[st : en + 1]
    if any(map(str.isdigit, result)) == False:
        return None
    
    prefix = raw_input[:st].split()
    suffix = raw_input[en + 1:].split()

    if len(prefix):
        if any(map(str.isdigit, prefix[-1])):
            result = prefix[-1] + ' ' + result
            prefix = prefix[:-1]
        ind = -1
        if abs(ind) <= len(prefix) and (unidecode(prefix[ind].upper()) == 'NGAY' or prefix[ind][-1] == ':'):
            while abs(ind) < len(prefix) and prefix[ind][0].islower() or prefix[ind] == ':':
                ind -= 1
            result = ' '.join(prefix[ind:]) + ' ' + result

    if len(suffix):
        if any(map(str.isdigit, suffix[0])):
            result = result + ' ' + suffix[0]
            suffix = suffix[1:]
        ind = 0
        if ind < len(suffix) and suffix[ind][0] == '(':
            while ind + 1 < len(suffix) and suffix[ind][-1] != ')':
                ind += 1
            result = result + ' ' + ' '.join(suffix[:ind])
    
    for x in re.findall('[0-9]+', result):
        if len(x) >= 5:
            result = result.replace(x,'')

    garbage = ['thu','  ']
    for x in garbage:
        result = result.replace(x,'')

    return result.replace('thu','').strip() if len(result) > 4 else None

def get_date(list_info_bankcard, list_flag_bbox):
    list_text = []
    for i in range(len(list_info_bankcard)):
        info = list_info_bankcard[i]
        content = info[1]
        if content.find('/') != -1:
            month = content.split("/")[0]
            month = int(month[-2:])
            # preprocess month > 12
            if checkmonth(month):
                month //= 10
                month = str(month)
                year = content.split("/")[-1]
                content = '0' + month + '/' + year
            else:
                year = content.split("/")[-1]
                if month < 10:
                    content = '0' + str(month) + '/' + year
                else:
                    content = str(month) + '/' + year
            # print("content: ", content)
        text = extractTimestamp(content)
        if text != None:
            year = int(text.split("/")[-1])
            list_text.append([year, text])
            list_flag_bbox[i] = True
    
    # print(list_text)

    list_text.sort(key = lambda x: x[0])
    if len(list_text) == 0:
        return None, None

    return list_text[0][1], list_text[-1][1]

# get top bbox
def get_bank(list_info_bankcard):
    info = list_info_bankcard[0]
    text = info[1]
    text = bankMatch(text)
    
    return text

# get bot bbox
def get_name(list_info_bankcard):
    i = len(list_info_bankcard) - 1
    while(i>=0):
        info = list_info_bankcard[i]
        text = info[1]
        bbox = info[0]

        if len(text) >= 6:
            return text, bbox, i

        i -= 1
    
    return None, None

def get_type_card(list_info_bankcard, polygon_name):
    for info in list_info_bankcard:
        text = info[1]
        bbox = info[0]

        polygon_box = Polygon(bbox)
        if polygon_box.intersects(polygon_name):
            # ko xet name box
            if len(text) <= 6:
                text = typecardMatch(text)
                return text
    
    return None

def get_number(list_info_bankcard, list_flag_bbox, w, image):
    max_len = 0
    index_number = 0
    # number = ""
    # print(list_flag_bbox)

    for i in range(len(list_flag_bbox)):
        if list_flag_bbox[i] == False:
            # print(list_info_bankcard[i][1])
            # print(len(list_info_bankcard[i][1]))
            if len(list_info_bankcard[i][1]) >= max_len:
                index_number = i
                max_len = len(list_info_bankcard[i][1])
                # print(max_len)
    
    number = list_info_bankcard[index_number][1]
    list_flag_bbox[index_number] = True
    bbox_number = list_info_bankcard[index_number][0]
    bbox_polygon_number = [[0, bbox_number[0][1]], 
                            [w, bbox_number[1][1]], 
                            [w, (bbox_number[0][1]+bbox_number[3][1])//2], 
                            [0, (bbox_number[0][1]+bbox_number[3][1])//2]]

    # image = draw_box(image, bbox_polygon_number)

    polygon_number = Polygon(bbox_polygon_number)
    
    for i in range(len(list_info_bankcard)):
        if list_flag_bbox[i] == False:
            info = list_info_bankcard[i]
            text = info[1]
            bbox = info[0]
            polygon_box = Polygon(bbox)
            if polygon_box.intersects(polygon_number):
                if bbox_number[0][0] >= bbox[0][0]:
                    number = text + list_info_bankcard[index_number][1] 
                else:
                    number = list_info_bankcard[index_number][1] + text 
    
    number = replace_char_to_number(number)

    return number

def get_info_card(image, list_info_bankcard, list_flag_bbox):
    h, w, c = image.shape
    # get date
    valid_from, good_thru = get_date(list_info_bankcard, list_flag_bbox)

    # get bank
    bank = get_bank(list_info_bankcard)
    list_flag_bbox[0] = True

    # get name
    name, bbox_name, index_name = get_name(list_info_bankcard)
    list_flag_bbox[index_name] = True
    bbox_polygon_name = [[0, (bbox_name[0][1]+bbox_name[3][1])//2 -5], 
                        [w, (bbox_name[1][1]+bbox_name[2][1])//2 -5], 
                        [w, bbox_name[2][1]], [0, bbox_name[3][1]]]
    polygon_name = Polygon(bbox_polygon_name)

    image = draw_box(image, bbox_polygon_name)

    list_name = name.split()
    first_name = firstnameMatch(list_name[0])
    if first_name != None:
        list_name[0] = first_name

    i = 1
    index_midname = len(list_name) - 2
    while i == index_midname:
        mid_name = midnameMatch(list_name[i])
        if mid_name != 0:
            list_name[i] = mid_name
        i += 1
    
    name = ' '.join(map(str, list_name))


    # get type card
    type_card = get_type_card(list_info_bankcard, polygon_name)

    # print("list_flag_bbox: ", list_flag_bbox)
    # get number
    number = get_number(list_info_bankcard, list_flag_bbox, w, image)

    return bank, name, type_card, valid_from, good_thru, number

@app.route('/bankcard')
def home():
    return render_template('visual_bank.html')

# @app.route('/get_ori_img')
# def get_ori_img():
#     print("showed image")
#     filename = request.args.get('filename')
#     img = cv2.imread(os.path.join(UPLOAD_FOLDER, filename))
# #    img = cv2.resize(img, (750, 250)) 
#     ret, jpeg = cv2.imencode('.jpg', img)
#     return  Response((b'--frame\r\n'
#                      b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tostring() + b'\r\n\r\n'),
#                     mimetype='multipart/x-mixed-replace; boundary=frame')

    
@app.route('/predict', methods=['POST'])
def predict_card():
    if request.method == 'POST':
        try:
            file = request.files['file']
                
            image_file = file.read()
            image = cv2.imdecode(np.frombuffer(image_file, dtype=np.uint8), -1)

            now = datetime.now()
            date_time = now.strftime("%m_%d_%Y_%H_%M_%S")
            image_path = os.path.join(UPLOAD_FOLDER, date_time+'.jpg')
            print("image_path: ", image_path)
            cv2.imwrite(image_path, image)

            url = 'http://service.aiclub.cs.uit.edu.vn/gpu150/paddle_ocr/predict'
            
            is_success, buffer = cv2.imencode('.png', image)
            f = io.BytesIO(buffer)
            image_encoded = base64.encodebytes(f.getvalue()).decode('utf-8')
            ####################################
            start_time = time.time()
            data ={"images": [image_encoded]}
            headers = {'Content-type': 'application/json'}
            data_json = json.dumps(data)
            response = requests.post(url, data = data_json, headers=headers)
            response = response.json()

            data = response['data']
            predict = data['predict'][0]

            # image = cv2.imread(image_path)
            
            # image = cv2.resize(image, (500, 500))
            image, list_info_bankcard, list_flag_bbox = draw_bankcard(image, predict)
            bank, name, type_card, valid_from, good_thru, number = get_info_card(image, list_info_bankcard, list_flag_bbox)

            print("bank: ", bank)
            print("name: ", name)
            print("number: ", number)
            print("type_card: ", type_card)
            print("valid_from: ", valid_from)
            print("good_thru: ", good_thru)

            return_result ={
                'path': image_path,
                'bank': bank,
                'name': name,
                'type_card': type_card,
                'valid_from': valid_from,
                'good_thru': good_thru,
                'number': number
            }

            with open(os.path.join(RESULT_FOLDER, date_time +'.json'), 'w') as f:
                json.dump(return_result, f)

        except Exception as e:
            logger.error(str(e))
            logger.error(str(traceback.print_exc()))
            return_result = {'code': '1001', 'status': rcode.code_1001}

        finally:
            return jsonify(return_result)

@app.route('/get_ori_img')
def get_ori_img():
    print("showed image")
    imagepath = request.args.get('imagepath')
    print("image_path in get: ", imagepath)
    img = cv2.imread(imagepath)
    ret, jpeg = cv2.imencode('.jpg', img)
    return  Response((b'--frame\r\n'
                     b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tostring() + b'\r\n\r\n'),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/get_label', methods=['GET'])
def getLabel():
    imagepath = request.args.get('imagepath')
    try:
        filename = (imagepath.split('/')[-1]).split('.')[0]
        json_path = os.path.join(RESULT_FOLDER, filename +'.json')

        with open(json_path) as json_file:
            data = json.load(json_file)

        bank = data['bank']
        number = data['number']
        name = data['name']

        good_thru = data['good_thru']
        valid_from = data['valid_from']
        if good_thru != None:
            date = good_thru
        else:
            date = valid_from
        
        print("date: ", date)
        
        pay = data['type_card']

        return_result ={
            'bank': bank,
            'name': name,
            'date': date,
            'number': number,
            'pay': pay
        }
        print(return_result)

    except Exception as e:
        logger.error(str(e))
        logger.error(str(traceback.print_exc()))
        return_result = {'code': '1001', 'status': rcode.code_1001}
    finally:
        return jsonify(return_result)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5555, debug=True)