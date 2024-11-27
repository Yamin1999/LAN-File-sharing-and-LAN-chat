from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash, Response
from flask_socketio import SocketIO, emit
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import json
import re
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import time
import shutil
import pytz


app = Flask(__name__, static_url_path='/static')
app.config['SECRET_KEY'] = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['CHAT_UPLOADS'] = 'chat_uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create chat uploads directory if it doesn't exist
if not os.path.exists(app.config['CHAT_UPLOADS']):
    os.makedirs(app.config['CHAT_UPLOADS'])

db = SQLAlchemy(app)
socketio = SocketIO(app)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif','jfif','webp','ico'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_name = db.Column(db.String(100), nullable=False)
    sender_ip = db.Column(db.String(50), nullable=False)
    message = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(20), default='text')  # 'text', 'image'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'sender': self.sender_name,
            'message': self.message,
            'message_type': self.message_type,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        }

# Create database tables
with app.app_context():
    db.create_all()


    
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024  # 1GB size limit

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

## ip to name
ip_to_name = {

}

# Store active chat users
active_users = {}

# Message handling functions
def save_message(sender_name, sender_ip, message_text):
    """Save a message to the database"""
    message = ChatMessage(
        sender_name=sender_name,
        sender_ip=sender_ip,
        message=message_text
    )
    db.session.add(message)
    db.session.commit()
    return message

def get_recent_messages(limit=50):
    """Get recent messages from the database"""
    messages = ChatMessage.query.order_by(
        ChatMessage.timestamp.desc()
    ).limit(limit).all()
    return [msg.to_dict() for msg in reversed(messages)]

def process_message_content(message):
    # Convert URLs to clickable links
    url_pattern = r'(https?://\S+)'
    message = re.sub(url_pattern, r'<a href="\1" target="_blank">\1</a>', message)
    return message

@socketio.on('connect')
def handle_connect():
    client_ip = request.remote_addr
    username = ip_to_name.get(client_ip, client_ip)
    
    active_users[request.sid] = {
        'username': username,
        'ip': client_ip
    }
    
    unique_users = {}
    for user in active_users.values():
        unique_users[user['ip']] = user['username']
    
    emit('user_list', list(unique_users.values()), broadcast=True)
    emit('chat_history', get_recent_messages())

@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in active_users:
        del active_users[request.sid]
        
        unique_users = {}
        for user in active_users.values():
            unique_users[user['ip']] = user['username']
        
        emit('user_list', list(unique_users.values()), broadcast=True)

@socketio.on('chat_message')
def handle_message(data):
    if request.sid in active_users:
        user = active_users[request.sid]
        processed_message = process_message_content(data['message'])
        message = save_message(user['username'], user['ip'], processed_message)
        emit('new_message', message.to_dict(), broadcast=True)

@socketio.on('image_upload')
def handle_image_upload(data):
    if request.sid in active_users:
        user = active_users[request.sid]
        image_data = data['image']
        filename = secure_filename(data['filename'])
        message_text = data.get('message', '')
        
        if allowed_file(filename):
            # Generate unique filename
            base, ext = os.path.splitext(filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_filename = f"{base}_{timestamp}{ext}"
            save_path = os.path.join(app.config['CHAT_UPLOADS'], unique_filename)
            
            # Save the image
            with open(save_path, 'wb') as f:
                f.write(image_data)
            
            # Create image URL - Make sure this matches your server configuration
            image_url = url_for('uploaded_file', filename=unique_filename)
            
            # Create HTML content with both image and text
            message_content = f'<div class="message-image"><img src="{image_url}" alt="Shared image"></div>'
            if message_text:
                message_content += f'<div class="message-text">{message_text}</div>'
            
            message = ChatMessage(
                sender_name=user['username'],
                sender_ip=user['ip'],
                message=message_content,
                message_type='image'
            )
            db.session.add(message)
            db.session.commit()
            
            emit('new_message', message.to_dict(), broadcast=True)

@app.route('/chat_uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['CHAT_UPLOADS'], filename)

# Your existing file handling functions
def get_uploader_ip(filename):
    try:
        with open('ip_address_map.json', 'r') as f:
            data = json.load(f)
        return data.get(filename, "Unknown IP")
    except FileNotFoundError:
        return "Unknown IP"

def update_ip_address_map(filename, ip_address, json_file='ip_address_map.json'):
    # Initialize the dictionary for storing IP and filename pairs
    ip_address_map = {}
    
    # Check if the JSON file exists and parse it
    if os.path.exists(json_file):
        with open(json_file, 'r') as f:
            try:
                ip_address_map = json.load(f)
            except json.JSONDecodeError:
                # Handle empty or corrupted file
                ip_address_map = {}
    
    # Update the dictionary with the new IP and filename
    ip_address_map[filename] = ip_to_name.get(ip_address, ip_address)
    
    # Write the updated dictionary back to the JSON file
    with open(json_file, 'w') as f:
        json.dump(ip_address_map, f, indent=4)
    
    return ip_address_map

def delete_ip_address_from_json(filename, json_file='ip_address_map.json'):
    # Initialize the dictionary for storing IP and filename pairs
    ip_address_map = {}
    
    # Check if the JSON file exists and parse it
    if os.path.exists(json_file):
        with open(json_file, 'r') as f:
            try:
                ip_address_map = json.load(f)
            except json.JSONDecodeError:
                # Handle empty or corrupted file
                return
    if(ip_address_map[filename]):
        del ip_address_map[filename]
    
    with open(json_file, 'w') as f:
        json.dump(ip_address_map, f, indent=4)
    return ip_address_map

def clear_ip_address_json(json_file='ip_address_map.json'):
    ip_address_map = {}
    if os.path.exists(json_file):
        with open(json_file, 'w') as f:
            try:
                json.dump(ip_address_map, f, indent=4)
            except json.JSONDecodeError:
                return
    return ip_address_map

def get_file_size(file_path):
    size_bytes = os.path.getsize(file_path)
    if size_bytes == 0:
        return "0 B"
    units = ('B', 'KB', 'MB', 'GB', 'TB')
    i = 0
    while size_bytes >= 1024 and i < len(units)-1:
        size_bytes /= 1024.
        i += 1
    return f"{size_bytes:.2f} {units[i]}"


def perform_daily_cleanup():
    """Perform daily cleanup of chat messages and uploads"""
    with app.app_context():
        # Get current time in Bangladesh timezone
        bd_tz = pytz.timezone('Asia/Dhaka')
        current_time = datetime.now(bd_tz)
        
        # Cleanup database
        ChatMessage.query.delete()
        db.session.commit()
        
        # Clear chat uploads folder
        uploads_path = app.config['CHAT_UPLOADS']
        if os.path.exists(uploads_path):
            for filename in os.listdir(uploads_path):
                file_path = os.path.join(uploads_path, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    print(f'Failed to delete {file_path}. Reason: {e}')
        
        print(f"Daily cleanup performed at {current_time}")


# Routes
@app.route('/')
def index():
    files = []
    for filename in os.listdir(app.config['UPLOAD_FOLDER']):
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        files.append({
            'name': filename,
            'size': get_file_size(file_path),
            'ip': get_uploader_ip(filename)
        })
    return render_template('index.html', files=files)

@app.route('/chat')
def chat():
    return render_template('chat.html', ip_to_name=ip_to_name)
    
@app.route('/readme')
def readme():
    return render_template('readme.html')

@app.route('/tftp')
def tftp():
    return render_template('tftp.html')

@app.route('/download/Panda')
def download_panda():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'Panda.exe', as_attachment=True)

@app.route('/upload', methods=['POST'])
def upload_file():
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    print("ip" + ip)

    if 'file' not in request.files:
        return 'No file part', 400
    
    file = request.files['file']
    if file.filename == '':
        return 'No selected file', 400
    
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # If file already exists, append number to filename
        base, ext = os.path.splitext(filename)
        counter = 1
        while os.path.exists(file_path):
            filename = f"{base}_{counter}{ext}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            counter += 1
        update_ip_address_map(filename, ip)   
        try:
            file.save(file_path)
            return "file uploaded successfully", 200
        except Exception as e:
            return f'Error uploading file: {str(e)}', 500
    
    return 'Invalid file', 400

@app.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    if not os.path.isfile(file_path):
        return Response("<script>window.location.href = '/';</script>", mimetype="text/html")
    
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
    
@app.route('/delete/<filename>', methods=['POST'])
def delete_file(filename):
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            delete_ip_address_from_json(filename)
            return 'File deleted successfully', 200
        else:
            return 'File not found', 404
    except Exception as e:
        return f'Error deleting file: {str(e)}', 500

@app.route('/clear', methods=['POST'])
def clear_files():
    files = os.listdir(app.config['UPLOAD_FOLDER'])
    for file in files:
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], file))
            clear_ip_address_json()
        except Exception as e:
            flash(f'Error deleting {file}: {str(e)}')
            continue
    flash('All files deleted successfully')
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Track the last cleanup time
    last_cleanup_date = None
    
    # Create a thread for continuous cleanup checking
    import threading
    def cleanup_thread():
        global last_cleanup_date
        while True:
            # Get current time in Bangladesh timezone
            bd_tz = pytz.timezone('Asia/Dhaka')
            current_time = datetime.now(bd_tz)
            
            # Check if it's a new day and time is after midnight
            if (last_cleanup_date is None or 
                current_time.date() != last_cleanup_date.date() and 
                current_time.hour == 0 and 
                current_time.minute == 0):
                
                perform_daily_cleanup()
                last_cleanup_date = current_time
            
            # Sleep for a minute to reduce CPU usage
            time.sleep(60)
    
    # Start cleanup thread
    cleanup_checker = threading.Thread(target=cleanup_thread, daemon=True)
    cleanup_checker.start()
    
    # Run the socketio server
    socketio.run(app, host='192.168.0.103', port=5000, debug=True)