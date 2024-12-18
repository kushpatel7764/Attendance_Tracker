from flask import Flask, render_template, request, send_file
from datetime import datetime
import os
from google.cloud import storage
import io
import db
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "./semiotic-lamp-431814-j7-c9786b187abe.json"

class_number = None
app = Flask(__name__)

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/index.html')
def home_index():
    return render_template('index.html')

@app.route('/init_classes.html')
def init_classes():
    return render_template("init_classes.html")

@app.route('/selection.html')
def selection():
    return render_template("selection.html")

@app.route('/show_attendance.html')
def show_attendance():
    # Retrieve filter parameters from the request
    first_name = request.args.get('first_name', default=None)
    last_name = request.args.get('last_name', default=None)
    date = request.args.get('date', default=None)
    class_filter = request.args.get('class', default=None)
    status = request.args.get('status', default=None)

    # Retrieve column visibility preferences from the checkboxes
    show_class = request.args.get('show_class') is not None  # If "checked", it will be in the request args
    show_date = request.args.get('show_date') is not None    


    # Base query
    query = "SELECT * FROM Attendance WHERE 1=1"
    params = []

    # Add filters to the query dynamically
    if first_name:
        query += " AND FirstName = %s"
        params.append(first_name)
    if last_name:
        query += " AND LastName = %s"
        params.append(last_name)
    if date:
        query += " AND date = %s"
        params.append(date)
    if class_filter:
        query += " AND Class = %s"
        params.append(class_filter)
    if status:
        query += " AND Status = %s"
        params.append(status)
    attendance_data = db.get_query(query, tuple(params))
    return render_template("show_attendance.html", data=attendance_data, show_class=show_class, show_date=show_date)

@app.route('/paper.html')
def paper():
    return render_template("paper.html")

@app.route('/username.html')
def username():
    return render_template("username.html")

@app.route('/computer.html')
def computer():
    return render_template("computer.html")

@app.route('/submit_classes', methods=['POST']) 
def submit_classes(): 
    class_descriptions = request.form.getlist('class_description') 
    username = request.form.get('class_input')  # Safely get the input
    if not username:
        return "Error: Unique Username must be provided.", 400
    # Create a directory to store the file if it doesn't exist
    if not os.path.exists('output'): 
        os.makedirs('output') 
        # Write the class descriptions to a file 
    file_path = f'output/{username}.txt'
    with open(file_path, 'w') as f: 
        for i, description in enumerate(class_descriptions, start=1): 
            f.write(f"Class {i}:\n") 
            f.write(f"{description}\n") 
            f.write("\n") 
            
    # Upload the file to Google Cloud Storage
    upload_to_gcs(file_path, username)
    return f"Class descriptions saved to class_descriptions.txt!"

def upload_to_gcs(file_path, username):
    """Uploads a file to Google Cloud Storage."""
    # Initialize a client with explicit credentials
    storage_client = storage.Client()
    cloud_location_split = "gs://semiotic-lamp-431814-j7.appspot.com/image.png".split("//")
    print(f" cloud_location is {cloud_location_split}")
    cloud_location = cloud_location_split[1].split("/")
    #First part of cloudlocation is bucket name
    bucket_name = cloud_location[0]
    #the rest is prefix
    prefix = "/".join(cloud_location[1:])
    bucket = storage_client.get_bucket(bucket_name)

    
    # Define the destination blob name
    blob_name = f"{username}.txt"
    blob = bucket.blob(blob_name)
    
    # Upload the file
    blob.upload_from_filename(file_path)
    storage_client.close()
    print(f"File {file_path} uploaded to {blob_name} in bucket {bucket_name}.")

@app.route("/submit_username", methods=["GET","POST"])
def submit_username():
    data = None
    error = None

    if request.method == 'POST':
        username = request.form.get('username')  # Username input
        class_number = request.form.get('class_number')  # Class number input

        try:
            # Define the Google Cloud bucket and file location
            bucket_name = "semiotic-lamp-431814-j7.appspot.com"  # Replace with your bucket name
            file_name = f"{username}.txt"  # File name is based on the username

            # Initialize Google Cloud Storage Client
            storage_client = storage.Client()
            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(file_name)

            # Check if file exists and download content
            if not blob.exists():
                error = f"File {file_name} not found in the bucket."
                return render_template('computer.html', data=data, error=error)

            content = blob.download_as_text()  # Download the content and decode
            print("Downloaded Content:", content)

            # Process file content: Check for class number
            # Assuming file structure: "Class<number>:<content>"
            class_entries = content.splitlines()  # Split file content into lines
            capture = False  # Flag to capture lines belonging to the class

            collected_data = []  # List to store student names
            for line in class_entries:
                line = line.strip()

                if line.startswith(f"Class {class_number}:"):
                    capture = True  # Start capturing student names
                    continue

                # If another class starts, stop capturing
                if line.startswith("Class") and capture:
                    break

                # Capture student names if within the class block
                if capture and line:
                    collected_data.append(line)
                
            # Check if any data was captured
            if collected_data:
                data = "\n".join(collected_data)  # Combine names for display
            else:
                error = f"No data found for Class {class_number}."
        except Exception as e:
            error = f"An error occurred: {str(e)}"

    return render_template('computer.html', data=data, error=error, class_number=class_number)

@app.route('/submit', methods=['POST'])
def submit():
    data = []
    row_count = 0
    while f'studentName_{row_count}' in request.form:  # Loop through all studentName fields
        name = request.form.get(f'studentName_{row_count}').strip()  # Get student names
        class_number = request.form.get('class_number').strip()
        status = None
        # Get the selected status (Present, Absent, Late)
        for status_option in ['Present', 'Absent', 'Late', 'Excused']:
            if request.form.get(f'status_{row_count}') == status_option:
                status = status_option
                break
        
        if name and status:
            data.append({"name": name, "status": status})
        
        row_count += 1  # Increment the row counter

    if not data:
        return render_template('computer.html', data=None, error="No data to submit!")

    # Get today's date
    today_date = datetime.now().strftime("%Y-%m-%d")
    
    for student in data:
        name = student["name"]
        first_name = name.split(" ")[0]
        last_name = name.split(" ")[1]
        status = student["status"]
        db.create(first_name, last_name, status, class_number, today_date)
        
        
    return render_template('computer.html', attendance_data=data, date=today_date)

if __name__ == '__main__':
    app.run(debug=True)