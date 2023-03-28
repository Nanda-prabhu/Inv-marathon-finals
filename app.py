import os
import re
import smtplib
from datetime import datetime
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import cv2
import pandas as pd
import pymongo as mongo
import pytesseract
from flask import Flask, make_response, redirect, render_template, request
from pytesseract import Output
from werkzeug.utils import secure_filename

app = Flask(__name__)

from_gmail = os.environ.get("FROM_GMAIL")
from_gmail_key = os.environ.get("FROM_GMAIL_KEY")
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

def mail_otp(name, to_gmail, event):
    message = MIMEMultipart()
    html = f"""
    <html>
        <head></head>
            <body>
                <p>Hello {name},</p>
                <p>This is a confirmation mail for you registration in the below event</p>
                <p>Event name: {event['name']}</p>
                <p>Event date: {event['date'].strftime("%d-%m-%Y")}</p>
                <p>Event venue: {event['venue']}</p>
                <br>
                <img src="cid:image1">
            </body>
    </html>
    """
    body = MIMEText(html, 'html')
    message.attach(body)
    with open(f"./static/images/{event['poster']}", "rb") as f:
        img_data = f.read()
        image = MIMEImage(img_data, name="test0.png")
        image.add_header('Content-ID', '<image1>')
        image.add_header('Content-Disposition', 'inline', filename='image.jpg')
        message.attach(image)
    message["Subject"] = f"Confirmation mail for {event['name']}"
    message["From"] = from_gmail
    message["To"] = to_gmail
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(from_gmail, from_gmail_key)
        server.sendmail(from_gmail, to_gmail, message.as_string())

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

# @app.route("/about", methods=["GET"])
# def about():
#     return render_template("about.html")

# @app.route("/contact", methods=["GET"])
# def contact():
#     return render_template("contact.html")

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
            registration_limit = int(request.form.get("limit"))
            events_collection = db["events"]
            try:
                event_id = int(list(events_collection.find({}))[-1]["event_id"]) + 1
            except Exception as e:
                event_id = 1
            events_collection.insert_one(
                {
                    "event_id": event_id,
                    "poster": event_name + "." + poster.filename.split(".")[-1],
                    "name": event_name,
                    "date": event_date,
                    "time": event_time,
                    "venue": event_venue,
                    "limit": registration_limit,
                    "registered": 0,
                    "registrations": []
                }
            )
            message = {
                "title": "Success",
                "body": "You have successfully created a new event"
            }
            return render_template("information.html", message=message)
        return render_template("create_event.html")
    else:
        message = {
            "title": "Access denied",
            "body": "This role is not permitted to access this part of the site"
        }
        return render_template("information.html", message=message)

@app.route("/view-events", methods=["GET"])
def view_evevnt():
    role = request.cookies.get("role")
    events_collection = db["events"]
    events_collection_list = [event for event in events_collection.find({})][::-1]
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
            event_limit = int(request.form.get("limit"))
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
                        "venue": event_venue,
                        "limit": event_limit
                    }
                }
            )
            message = {
                "title": "Success",
                "body": "You have successfully edited the event"
            }
            return render_template("information.html", message=message)
        return render_template("edit_event.html", event=event)
    else:
        message = {
            "title": "Access denied",
            "body": "This role is not permitted to access this part of the site"
        }
        return render_template("information.html", message=message)

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
        message = {
            "title": "Success",
            "body": "You have successfully deleted the event"
        }
        return render_template("information.html", message=message)
    else:
        message = {
            "title": "Access denied",
            "body": "This role is not permitted to access this part of the site"
        }
        return render_template("information.html", message=message)

@app.route("/register", methods=["GET", "POST"])
def register():
    role = request.cookies.get("role")
    event_id = int(request.args.get("event_id"))
    if role == "student":
        events_collection = db["events"]
        event = events_collection.find_one(
            {
                "event_id": event_id
            }
        )
        if event["registered"] < event["limit"]:
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
                registrations = event["registrations"]
                for registration in registrations:
                    if registration["regno"] == regno:
                        message = {
                            "title": "Already registered",
                            "body": "This register number has already registered for the event"
                        }
                        return render_template("information.html", message=message)
                events_collection.update_one(
                    {
                        "event_id": event_id
                    },
                    {
                        "$set": {
                            "registered": event["registered"] + 1
                        },
                        "$push": {
                            "registrations": new_registration
                        }
                    }
                )
                mail_otp(name, email, event)
                message = {
                    "title": "Success",
                    "body": "You have successfully registered to this event"
                }
                return render_template("information.html", message=message)
            return render_template("register.html", event_id=event_id)
        else:
            message = {
                "title": "No more seats available",
                "body": "Looks like the event got filled out pretty fast"
            }
            return render_template("information.html", message=message)
    else:
        message = {
            "title": "Access denied",
            "body": "This role is not permitted to access this part of the site"
        }
        return render_template("information.html", message=message)

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
        if event:
            event_name = event["name"]
            registrations = event["registrations"]
            df = pd.DataFrame(registrations)
            df.to_excel(f"static/exports/{event_id}_{event_name}.xlsx", index=False)
            message = {
                "title": "Access denied",
                "body": "This role is not permitted to access this part of the site",
                "file": f"static/exports/{event_id}_{event_name}.xlsx"
            }
            return render_template("information.html", message=message)
        else:
            return redirect("/404-raise-error") # Non existant route to raise 404 error
    else:
        message = {
            "title": "Access denied",
            "body": "This role is not permitted to access this part of the site"
        }
        return render_template("information.html", message=message)

@app.route("/logout", methods=["GET"])
def logout():
    resp = make_response(redirect("/"))
    resp.set_cookie("role", "", expires=0)
    return resp

@app.errorhandler(404)
def page_not_found(e):
    message = {
        "title": "404",
        "body": "The page you are looking for does not exist"
    }
    return render_template("information.html", message=message)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")