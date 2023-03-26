import os
import re
from datetime import datetime

import cv2
import pandas as pd
import pymongo as mongo
import pytesseract
from flask import Flask, make_response, redirect, render_template, request
from pytesseract import Output
from werkzeug.utils import secure_filename

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
            try:
                event_id = int(list(events_collection.find({}))[-1]["event_id"]) + 1
            except:
                event_id = 1
            events_collection = db["events"]
            events_collection.insert_one(
                {
                    "event_id": event_id,
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
    role = request.cookies.get("role")
    events_collection = db["events"]
    events_collection_list = [event for event in events_collection.find({})]
    return render_template("view_events.html", events=events_collection_list, role=role)

@app.route("/edit-event", methods=["GET", "POST"])
def edit_event():
    role = request.cookies.get("role")
    if role == "admin":
        event_id = int(request.args.get("event_id"))
        events_collection = db["events"]
        event = events_collection.find_one(
            {
                "event_id": event_id
            }
        )
        if event:
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
                events_collection.update_one(
                    {
                        "event_id": event_id
                    },
                    {
                        "$set": {
                            "event_id": int(list(events_collection.find({}))[-1]["event_id"]) + 1,
                            "poster": event_name + "." + poster.filename.split(".")[-1],
                            "name": event_name,
                            "date": event_date,
                            "time": event_time,
                            "venue": event_venue
                        }
                    }
                )
                return redirect("/view-events")
            return render_template("edit_event.html", event=event)
        else:
            return "404 Event id not found <a href='/view-events'>view-events</a>"
    else:
        return render_template("access_denied.html")

@app.route("/delete-event", methods=["GET", "POST"])
def delete_event():
    role = request.cookies.get("role")
    if role == "admin":
        event_id = int(request.args.get("event_id"))
        events_collection = db["events"]
        events_collection.delete_one(
            {
                "event_id": event_id
            }
        )
        return redirect("/view-events")
    else:
        return render_template("access_denied.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    role = request.cookies.get("role")
    event_id = int(request.args.get("event_id"))
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
            registrations = events_collection.find_one(
                {
                    "event_id": event_id
                }
            )["registrations"]
            for registration in registrations:
                if registration["regno"] == regno:
                    return "<h1>Already registered <a href='/view-events'>view-events</a></h1>"
            events_collection.update_one(
                {
                    "event_id": event_id
                },
                {
                    "$push": {
                        "registrations": new_registration
                    }
                }
            )
            return "Success <a href='/view-events'>view-events</a>"
        return render_template("register.html", event_id=event_id)
    else:
        return render_template("access_denied.html")

@app.route("/export", methods=["GET"])
def export():
    role = request.cookies.get("role")
    if role == "admin":
        event_id = int(request.args.get("event_id"))
        events_collection = db["events"]
        event = events_collection.find_one(
            {
                "event_id": event_id
            }
        )
        event_name = event["name"]
        registrations = event["registrations"]
        df = pd.DataFrame(registrations)
        df.to_excel(f"static/exports/{event_id}_{event_name}.xlsx", index=False)
        return f"Exported <a href='static/exports/{event_id}_{event_name}.xlsx' download='static/exports/{event_id}_{event_name}.xlsx'>Click to download</a>"
    else:
        return render_template("access_denied.html")

@app.route("/logout", methods=["GET"])
def logout():
    resp = make_response(redirect("/"))
    resp.set_cookie("role", "", expires=0)
    return resp

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")