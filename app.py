import os
import json
from datetime import datetime
from telegram import Bot
from flask import Flask, request, render_template_string, session, redirect, Response
import asyncio
import requests as req

TOKEN = "8713000220:AAENljz2o39DfO5R7_c9fkD_555OeweiFPI"
CHAT_ID = "6737445640"
MOT_DE_PASSE = "Ba1002@@"
FICHIERS_JSON = "fichiers.json"

app = Flask(__name__)
app.secret_key = "cle_secrete_babacloud"

def charger_fichiers():
    if os.path.exists(FICHIERS_JSON):
        with open(FICHIERS_JSON, "r") as f:
            return json.load(f)
    return []

def sauvegarder_fichier(nom, taille, file_id):
    fichiers = charger_fichiers()
    fichiers.append({
        "nom": nom,
        "taille": f"{round(taille/1024, 1)} Ko",
        "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "file_id": file_id
    })
    with open(FICHIERS_JSON, "w") as f:
        json.dump(fichiers, f)

HTML_LOGIN = """
<!DOCTYPE html>
<html>
<head>
    <title>BabaCloud - Connexion</title>
    <style>
        body { font-family: Arial; background: #1a1a2e; color: white; text-align: center; padding: 50px; }
        h1 { color: #e94560; }
        input { padding: 10px; margin: 10px; border-radius: 8px; border: none; width: 250px; }
        button { padding: 10px 30px; background: #e94560; color: white; border: none; border-radius: 8px; cursor: pointer; }
        .erreur { color: #ff6b6b; }
    </style>
</head>
<body>
    <h1>☁️ BabaCloud</h1>
    <p>Entre ton mot de passe pour accéder</p>
    <input type="password" id="mdp" placeholder="Mot de passe"><br>
    <button onclick="login()">🔐 Entrer</button>
    {% if erreur %}<p class="erreur">❌ Mot de passe incorrect !</p>{% endif %}
    <form id="form" method="POST" action="/login">
        <input type="hidden" name="mdp" id="mdp_hidden">
    </form>
    <script>
        document.querySelector('button').onclick = function() {
            document.getElementById('mdp_hidden').value = document.getElementById('mdp').value;
            document.getElementById('form').submit();
        }
    </script>
</body>
</html>
"""

HTML_CLOUD = """
<!DOCTYPE html>
<html>
<head>
    <title>BabaCloud</title>
    <style>
        body { font-family: Arial; background: #1a1a2e; color: white; padding: 30px; }
        h1 { color: #e94560; text-align: center; }
        .upload-box { text-align: center; margin: 20px 0; }
        input[type=file], button { padding: 10px; margin: 10px; border-radius: 8px; border: none; }
        button { background: #e94560; color: white; cursor: pointer; padding: 10px 30px; }
        .logout { background: #444; font-size: 12px; padding: 5px 15px; float: right; }
        table { width: 100%; border-collapse: collapse; margin-top: 30px; }
        th { background: #e94560; padding: 12px; text-align: left; }
        td { padding: 10px; border-bottom: 1px solid #333; }
        tr:hover { background: #2a2a4e; }
        .vide { text-align: center; color: #888; padding: 30px; }
        .message { text-align: center; color: #4caf50; font-size: 18px; }
        .dl { background: #16213e; color: #e94560; border: 1px solid #e94560; padding: 5px 15px; border-radius: 6px; cursor: pointer; text-decoration: none; }
    </style>
</head>
<body>
    <button class="logout" onclick="window.location='/logout'">🚪 Déconnexion</button>
    <h1>☁️ BabaCloud</h1>

    <div class="upload-box">
        <form method="POST" action="/upload" enctype="multipart/form-data">
            <input type="file" name="file" required><br>
            <button type="submit">📤 Uploader</button>
        </form>
        {% if message %}<p class="message">{{ message }}</p>{% endif %}
    </div>

    <h2>📋 Mes fichiers ({{ fichiers|length }})</h2>
    {% if fichiers %}
    <table>
        <tr>
            <th>📄 Nom</th>
            <th>📦 Taille</th>
            <th>📅 Date</th>
            <th>⬇️ Action</th>
        </tr>
        {% for f in fichiers %}
        <tr>
            <td>{{ f.nom }}</td>
            <td>{{ f.taille }}</td>
            <td>{{ f.date }}</td>
            <td><a class="dl" href="/download/{{ loop.index0 }}">⬇️ Télécharger</a></td>
        </tr>
        {% endfor %}
    </table>
    {% else %}
    <p class="vide">Aucun fichier uploadé pour l'instant</p>
    {% endif %}
</body>
</html>
"""

@app.route("/")
def home():
    if not session.get("connecte"):
        return redirect("/login")
    return render_template_string(HTML_CLOUD, fichiers=charger_fichiers(), message=None)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("mdp") == MOT_DE_PASSE:
            session["connecte"] = True
            return redirect("/")
        return render_template_string(HTML_LOGIN, erreur=True)
    return render_template_string(HTML_LOGIN, erreur=False)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/upload", methods=["POST"])
def upload():
    if not session.get("connecte"):
        return redirect("/login")
    file = request.files["file"]
    taille = len(file.read())
    file.seek(0)
    file.save(file.filename)

    async def send():
        bot = Bot(token=TOKEN)
        with open(file.filename, "rb") as f:
            msg = await bot.send_document(chat_id=CHAT_ID, document=f)
        return msg.document.file_id

    file_id = asyncio.run(send())
    sauvegarder_fichier(file.filename, taille, file_id)
    os.remove(file.filename)
    return render_template_string(HTML_CLOUD, fichiers=charger_fichiers(), message="✅ Fichier envoyé dans ton cloud !")

@app.route("/download/<int:index>")
def download(index):
    if not session.get("connecte"):
        return redirect("/login")
    fichiers = charger_fichiers()
    if index >= len(fichiers):
        return "Fichier introuvable", 404
    fichier = fichiers[index]
    file_id = fichier["file_id"]
    nom = fichier["nom"]

    info = req.get(f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={file_id}").json()
    file_path = info["result"]["file_path"]
    file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"

    data = req.get(file_url).content
    return Response(data, headers={
        "Content-Disposition": f"attachment; filename={nom}",
        "Content-Type": "application/octet-stream"
    })

if __name__ == "__main__":
    app.run(debug=True)