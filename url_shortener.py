from flask import Flask, request, redirect, render_template_string, flash
import psycopg2
import hashlib
import string
import random

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Replace with a secure key

# Database connection configuration
DB_CONFIG = {
    'dbname': 'url_shortener',
    'user': 'postgres',
    'password': '',  # Replace with your PostgreSQL password
    'host': 'localhost',
    'port': '5432'
}

# Initialize database
def init_db():
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS urls (
            id SERIAL PRIMARY KEY,
            original_url TEXT NOT NULL,
            short_code TEXT UNIQUE NOT NULL
        )
    ''')
    conn.commit()
    cursor.close()
    conn.close()

# Generate short code
def generate_short_code(url):
    # Use first 7 characters of MD5 hash
    hash_object = hashlib.md5(url.encode())
    return hash_object.hexdigest()[:7]

# Generate random short code as fallback
def generate_random_code():
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(7))

# Home route with form
@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        original_url = request.form.get('url')
        if not original_url:
            flash('URL is required!')
            return redirect('/')
        
        # Ensure URL starts with http:// or https://
        if not original_url.startswith(('http://', 'https://')):
            original_url = 'http://' + original_url
            
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Try to generate unique short code
        short_code = generate_short_code(original_url)
        try:
            cursor.execute('INSERT INTO urls (original_url, short_code) VALUES (%s, %s)',
                          (original_url, short_code))
            conn.commit()
        except psycopg2.IntegrityError:
            # If short code exists, try random code
            short_code = generate_random_code()
            cursor.execute('INSERT INTO urls (original_url, short_code) VALUES (%s, %s)',
                          (original_url, short_code))
            conn.commit()
        finally:
            cursor.close()
            conn.close()
                
        short_url = request.url_root + short_code
        return render_template_string('''
            <!DOCTYPE html>
            <html>
            <head>
                <title>URL Shortener</title>
                <style>
                    body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
                    .message { color: green; }
                    input[type=text] { width: 100%; padding: 8px; margin: 10px 0; }
                    input[type=submit] { padding: 8px 16px; }
                </style>
            </head>
            <body>
                <h1>URL Shortener</h1>
                {% with messages = get_flashed_messages() %}
                    {% if messages %}
                        <div class="message">{{ messages[0] }}</div>
                    {% endif %}
                {% endwith %}
                <form method="post">
                    <input type="text" name="url" placeholder="Enter URL to shorten">
                    <input type="submit" value="Shorten">
                </form>
                {% if short_url %}
                    <p>Shortened URL: <a href="{{ short_url }}">{{ short_url }}</a></p>
                {% endif %}
            </body>
            </html>
        ''', short_url=short_url)
    
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>URL Shortener</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
                .message { color: green; }
                input[type=text] { width: 100%; padding: 8px; margin: 10px 0; }
                input[type=submit] { padding: 8px 16px; }
            </style>
        </head>
        <body>
            <h1>URL Shortener</h1>
            {% with messages = get_flashed_messages() %}
                {% if messages %}
                    <div class="message">{{ messages[0] }}</div>
                {% endif %}
            {% endwith %}
            <form method="post">
                <input type="text" name="url" placeholder="Enter URL to shorten">
                <input type="submit" value="Shorten">
            </form>
        </body>
        </html>
    ''')

# Redirect route
@app.route('/<short_code>')
def redirect_url(short_code):
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute('SELECT original_url FROM urls WHERE short_code = %s', (short_code,))
    result = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    if result:
        return redirect(result[0])
    else:
        flash('Invalid short URL!')
        return redirect('/')

if __name__ == '__main__':
    init_db()
    app.run(debug=True)