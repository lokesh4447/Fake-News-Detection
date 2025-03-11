import numpy as np
import pandas as pd
from flask import Flask, render_template, request, flash, session, jsonify
from pymongo import MongoClient
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.models import load_model
from textblob import TextBlob
import random
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)

app.config['SECRET_KEY'] = 'ucfdxcghjhkjchxffchvjhugfutdx'

client = MongoClient('mongodb://localhost:27017/')
db = client['my_database']  
users_collection = db['users']  


OTP_LENGTH = 6
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
SMTP_USERNAME = 'noreplynewsdetection@gmail.com'
SMTP_PASSWORD = 'scyb ntyo qgmq diwa' 
SENDER_EMAIL = 'noreplynewsdetection@gmail.com'
otp_storage = {}


model = load_model('finalmodel.h5')


real_news = pd.read_csv('True.csv')
fake_news = pd.read_csv('Fake.csv')


data = pd.concat([real_news, fake_news], ignore_index=True)


data['content'] = data['title'] + " " + data['text']


max_words = 5000
tokenizer = Tokenizer(num_words=max_words)
tokenizer.fit_on_texts(data['content'])

def validate_user(username, password):
    user = users_collection.find_one({"email": username, "password": password})
    if user:
        return True
    else:
        return False
    
def generate_otp():
    return ''.join(random.choices(string.digits, k=OTP_LENGTH))


def send_otp_email(email, fullname, otp):
    msg = MIMEMultipart()
    fullname=fullname.title()
    msg['From'] = SENDER_EMAIL
    msg['To'] = email
    msg['Subject'] = 'Your OTP Verification Code from Fake-News Detector'

    body = f"""
    <html>
      <body>
        <p>Dear {fullname},</p>
        <p>Thank you for using News Detector!</p>
        <p>To complete your Sign-Up process, please use the following One-Time Password (OTP) for verification:</p>
        <p>Your OTP Code: <h2><strong>{otp}</strong></h2></p>
        <p>Please enter this code on the News Detector Sign-up page to verify your email address.</p>
        <p>If you did not initiate this request, please ignore this email.</p>
        <p>Thank you for choosing News Detector!</p>
      </body>
    </html>
    """
    msg.attach(MIMEText(body, 'html'))

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(SENDER_EMAIL, email, msg.as_string())


@app.route('/send-otp', methods=['POST'])
def send_otp():
    data = request.json
    email = data.get('email')
    fullname = data.get('fullname')
    otp = generate_otp()
    otp_storage[email] = {'otp': otp, 'fullname':fullname}
    send_otp_email(email, fullname, otp)
    return jsonify({'success': True})

@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    data = request.json
    email = data.get('email')
    otp = data.get('otp')
    stored_data = otp_storage.get(email)

    if stored_data and stored_data['otp'] == otp:
        del otp_storage[email]
        return jsonify({'success': True})
    else:
        return jsonify({'success': False})
    

def predict_news(news):
    news_content = news['title'] + " " + news['text']
    sentiment = TextBlob(news_content).sentiment.polarity
    keyword_flag = 1 if any(word in news_content.lower() for word in [
    'murder', 'theft', 'rape', 'assault', 'robbery', 'fraud', 'arson', 
    'kidnapping', 'burglary', 'embezzlement', 'terrorism', 'bombing', 'floods',
    'homicide', 'manslaughter', 'extortion', 'cybercrime', 'drugs', 
    'trafficking', 'corruption', 'scandal', 'violence', 'abduction', 
    'blackmail', 'smuggling', 'vandalism', 'bribery', 'money laundering', 
    'espionage', 'poisoning', 'sabotage', 'rioting', 'looting', 'shooting', 
    'stabbing', 'lynching', 'genocide', 'massacre', 'explosion', 'riot', 
    'revolt', 'insurrection', 'mutiny', 'coup', 'rebellion', 'treason', 
    'terrorist', 'hostage', 'atrocity', 'mass killing', 'kidnap', 
    'hostage', 'siege', 'war crime', 'human trafficking', 'forced labor' ,'raped' , 'india-worldcup-2024' ,'crime'
]) else 0

    sequence = tokenizer.texts_to_sequences([news_content])
    padded_sequence = pad_sequences(sequence, maxlen=200)  
    sentiment_and_keyword = np.array([[sentiment, keyword_flag]])
    combined_input = np.concatenate([padded_sequence, sentiment_and_keyword], axis=1)
    prediction = model.predict(combined_input)
    print(prediction)
    return "Real news" if prediction[0][0] >= 0.003 else "Fake news"

@app.route('/')
def home():
    return render_template('landing.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.json
        username = data.get('username')  
        password = data.get('password')
        if username and password:  
            if validate_user(username, password):
                flash('Login successful!', 'success')
                return jsonify({'status': 'success'}), 200
            else:
                flash('Invalid username or password.', 'danger')
        else:
            flash('Username and password are required.', 'danger')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return render_template('signup.html')  

    if request.method == 'POST':
        try:
            data = request.json
            fullname = data.get('fullname')
            email = data.get('email')
            password = data.get('password')

            
            users_collection.insert_one({
                'fullname': fullname,
                'email': email,
                'password': password
            })

            return jsonify({'status': 'success'}), 200
        except Exception as e:
            print(f"Error occurred: {e}")
            return jsonify({'status': 'error', 'message': 'Incorrect User Name or Password'}), 500

@app.route('/chat')
def chat():
    if 'username' in session:
        return render_template('chat.html', username=session['username'], email=session['email'])
    return render_template('chatpage.html')

@app.route('/update')
def update():
    if 'username' in session:
        username = session['username']
        email = session['email']
        return render_template('chat.html', username=username, email=email)
    else:
        return render_template('update.html')

@app.route('/logout')
def logout():
    session.pop('username', None)  
    return render_template('landing.html')

@app.route('/predict', methods=['POST'])
def predict():
    data = request.json
    title = data.get('mytitle')
    text = data.get('mydes')
    
    if not title or not text:
        return jsonify({'status': 'error', 'message': 'Title and text are required'}), 400
    
    news_data = {'title': title, 'text': text}
    result = predict_news(news_data)
    
    return jsonify({'status': 'success', 'result': result}), 200

if __name__ == '__main__':
    app.run(debug=True)
