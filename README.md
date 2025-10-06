# Pro_URL_Shortener

A URL Shortener that provides secure, encrypted, compressed, and compact URLs for your input links.

---

## 🚀 Features

- **Secure Links**: Generates short URLs with enhanced security measures.
- **Encryption**: Ensures that the original URLs are encrypted for privacy.
- **Compression**: Reduces the length of URLs without losing information.
- **Custom Aliases**: Allows users to create custom short links.
- **User-Friendly Interface**: Provides an intuitive web interface for easy URL shortening.

---

## 🛠️ Technologies Used

- **Backend**: Python
- **Web Framework**: FastAPI
- **Frontend**: HTML (Bootstrap), CSS
- **Database**: Redis

---

## 📦 Installation

### Prerequisites

Ensure you have the following installed:

- Python 3.8+
- pip (Python package installer)

### Steps

1. **Clone the Repository**

   ```bash
   git clone https://github.com/sk3577311/Pro_URL_Shortener.git
   cd Pro_URL_Shortener
   
2. **Install Dependencies

   ```bash
   pip install -r requirements.txt
   
3. **Configure Environment Variables

   ```bash
   REDIS_HOST=localhost
   REDIS_PORT=6379
   REDIS_DB=0
   SECRET_KEY=your_secret_key
   
4. **Run Redis Server

   ```bash
   Linux/Mac: redis-server
   Windows: Use Redis Desktop Manager or install Redis via WSL
   Docker: docker run -p 6379:6379 redis
   Cloud redis: From browser
   
4. **Start the FastAPI Server

   ```bash
   uvicorn main:app --reload

🧪 **Usage**

1. Navigate to http://127.0.0.1:8000/ in your browser.
2. Enter the URL you want to shorten.
3. Optionally, enter a custom shortcode.
4. Click Shorten.
5. Use the returned short URL to redirect to the original link.

**API Endpoints**

1. POST /shorten – Create a new short URL
2. GET /{short_code} – Redirect to original URL
3. GET /stats/{short_code} – (if applicable) View stored URLs

**🤝 Contributing**

1. Fork the repository.
2. Create a new branch (git checkout -b feature-name).
3. Make your changes.
4. Commit your changes (git commit -m 'Add feature').
5. Push the branch (git push origin feature-name).
6. Create a pull request.

