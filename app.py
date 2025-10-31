from flask import Flask, request, redirect, session, render_template_string, url_for
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
import os
import threading
from new_music import run_recommendation_script  # import your function

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "dev_secret")

# Spotify credentials & scope
SPOTIFY_CLIENT_ID = os.environ["SPOTIFY_CLIENT_ID"]
SPOTIFY_CLIENT_SECRET = os.environ["SPOTIFY_CLIENT_SECRET"]
SPOTIFY_REDIRECT_URI = os.environ.get["BASE_URL"] + "/spotify_auth"
SCOPE = "playlist-modify-public playlist-modify-private user-library-read"

# ===== Templates =====
INDEX_HTML = """
<!doctype html>
<html>
<head><title>Music Recs</title></head>
<body>
    <h1>Grayson's Enhanced Music Recs</h1>
    {% if 'access_token' in session %}
        <p>Logged in as Spotify user.</p>
        <a href="{{ url_for('setup_page') }}"><button>Go to Setup</button></a>
        <form action="{{ url_for('logout') }}" method="POST">
            <button type="submit">Logout</button>
        </form>

    {% else %}
        <a href="{{ url_for('login') }}"><button>Login with Spotify</button></a>
    {% endif %}
</body>
</html>
"""

SETUP_HTML = """
<!doctype html>
<html>
<head>
    <title>Setup Notifications</title>
    <script>
        function validateForm() {
            let phone = document.forms["recsForm"]["phone"].value;
            let regex = /^\+\d{11,15}$/;
            if (!regex.test(phone)) {
                alert("Invalid phone number format. Use +15132268634 format.");
                return false;
            }
            return true;
        }
    </script>
</head>
<body>
    <h2>Setup Notifications</h2>
    <form name="recsForm" action="{{ url_for('run_script') }}" method="POST" onsubmit="return validateForm()">
        <label>Phone Number:</label><br>
        <input name="phone" type="text" placeholder="+15132268634" required><br><br>
        <button type="submit">Generate Recommendations</button>
    </form>
    <br>
    <form action="{{ url_for('logout') }}" method="POST">
        <button type="submit">Logout</button>
    </form>
</body>
</html>
"""

# ===== Routes =====
@app.route("/")
def index():
    return render_template_string(INDEX_HTML)

@app.route("/login")
def login():
    sp_oauth = SpotifyOAuth(
        SPOTIFY_CLIENT_ID,
        SPOTIFY_CLIENT_SECRET,
        SPOTIFY_REDIRECT_URI,
        scope=SCOPE
    )
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route("/spotify_auth")
def spotify_auth_callback():
    sp_oauth = SpotifyOAuth(
        SPOTIFY_CLIENT_ID,
        SPOTIFY_CLIENT_SECRET,
        SPOTIFY_REDIRECT_URI,
        scope=SCOPE
    )
    code = request.args.get("code")
    token_info = sp_oauth.get_access_token(code, as_dict=False)
    session["access_token"] = token_info["access_token"]
    session["refresh_token"] = token_info["refresh_token"]
    return redirect(url_for("setup_page"))

@app.route("/setup")
def setup_page():
    if "access_token" not in session:
        return redirect(url_for("index"))
    return render_template_string(SETUP_HTML)

@app.route("/run", methods=["POST"])
def run_script():
    if "access_token" not in session:
        return "Not logged in with Spotify", 403

    phone = request.form.get("phone")
    if not phone or not phone.startswith("+") or not phone[1:].isdigit():
        return "Invalid phone number format. Use +15132268634 format.", 400

    access_token = session["access_token"]
    refresh_token = session["refresh_token"]

    # Run script in background
    def background_job():
        run_recommendation_script(access_token, refresh_token, phone)

    threading.Thread(target=background_job).start()
    return "🎵 Your personalized recommendations are being generated! You’ll get a text when it’s done."

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
