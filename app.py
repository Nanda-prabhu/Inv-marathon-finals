import os
from datetime import datetime

import pymongo as mongo
from flask import Flask, make_response, redirect, render_template, request
from werkzeug.utils import secure_filename

import cv2
import pytesseract
import re
from pytesseract import Output

# from flask_cors import CORS

app = Flask(__name__)
# CORS(app, resources={r"*": {"origins": "*"}})
# app.config["CORS_HEADERS"] = "Content-Type, Access-Control-Allow-Origin"

url = f"mongodb://localhost:27017"
client = mongo.MongoClient(url)
db = client["404-found"]

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
date_extract_pattern = "[0-9]{1,2}\-[0-9]{1,2}\-[0-9]{4}"

poster_directory = "posters"

def ocr_from_image(imgsrc):
    img = cv2.imread(imgsrc)
    d = pytesseract.image_to_data(img, output_type=Output.DICT)
    lis = d['text']
    string = " ".join(lis)
    result = re.findall(date_extract_pattern, string)
    n = lis.index('VENUE')+2
    venue = ""
    y = []
    for i in range(3):
        if(lis[n] != " "):
            y.append(lis[n])
            n += 1
    return [" ".join(y), result[0]]

@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def index():
    message = ""
    if request.method == "POST":
        user_collection = db["users"]
        user_role = request.form.get("role")
        username = request.form.get("username")
        password = request.form.get("password")
        existing_user = user_collection.find_one(
            {
                "username": username
            }
        )
        if existing_user:
            if existing_user["password"] == password:
                if existing_user["role"] == "admin":
                    resp = make_response(redirect("/create-event"))
                    resp.set_cookie("role", user_role)
                    return resp
                else:
                    resp = make_response(redirect("/view-events"))
                    resp.set_cookie("role", user_role)        
                    return resp
        message = "Login failed"
    return render_template("login.html", message=message)

@app.route("/create-event", methods=["GET", "POST"])
def create_event():
    role = request.cookies.get("role")
    if role == "admin":
        if request.method == "POST":
            poster = request.files.get("poster")
            event_name = request.form.get("name")
            poster_file_path = os.path.join(poster_directory, secure_filename(event_name + "." + poster.filename.split(".")[-1]))
            poster.save(os.path.join("static", "images", event_name + "." + poster.filename.split(".")[-1]))
            try:
                print(f"--> OCR output: {ocr_from_image(poster_file_path)}")
            except:
                print("--> OCR failed")
            event_date = datetime.strptime(request.form.get("date"), "%Y-%m-%d")
            event_time = datetime.strptime(request.form.get("time"), "%H:%M")
            event_venue = request.form.get("venue")
            events_collection = db["events"]
            events_collection.insert_one(
                {
                    "event_id": int(list(events_collection.find({}))[-1]["event_id"]) + 1,
                    "poster": event_name + "." + poster.filename.split(".")[-1],
                    "name": event_name,
                    "date": event_date,
                    "time": event_time,
                    "venue": event_venue,
                    "registrations": []
                }
            )
            return redirect("/view-events")
        return render_template("create_event.html")
    else:
        return render_template("access_denied.html")

@app.route("/view-events", methods=["GET"])
def view_evevnt():
    events_collection = db["events"]
    events_collection_list = [event for event in events_collection.find({})]
    print(events_collection_list[-1])
    return render_template("view_events.html", events=events_collection_list)

# @app.route("edit-event", methods=["GET", "POST"])
# def edit_event():
#     # use create event page with prefilled values


# @app.route("/delete-event", methods=["POST"])
# def delete_event():
#     return True
# use url query to select by event id

@app.route("/register", methods=["GET", "POST"])
def register():
    role = request.cookies.get("role")
    event_name = request.args.get("event_name")
    if role == "student":
        if request.method == "POST":
            regno = request.form.get("regno")
            name = request.form.get("name")
            email = request.form.get("email")
            dept = request.form.get("dept")
            year = request.form.get("year")
            section = request.form.get("section")
            phone = request.form.get("phone")
            new_registration = {
                "regno": regno,
                "name": name,
                "email": email,
                "dept": dept,
                "year": year,
                "section": section,
                "phone": phone
            }
            events_collection = db["events"]
            events_collection.update_one(
                {
                    "name": event_name
                },
                {
                    "$push": {
                        "registrations": new_registration
                    }
                }
            )
            return "Success"
        return render_template("register.html", event_name=event_name)
    else:
        return render_template("access_denied.html")

# @app.route("/export")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")