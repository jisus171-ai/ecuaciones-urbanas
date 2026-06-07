import os
import csv
import json
import uuid
import base64
import shutil
import urllib.request
import urllib.error
from datetime import datetime
from flask import Flask, request, jsonify, send_file, Response

app = Flask(__name__, static_folder="static")

CSV_FILE = "registros_ecuaciones_urbanas.csv"
CAPTURE_DIR = "static/captures"
DATASET_DIR = "dataset_ecuaciones_urbanas"
DATASET_ZIP = "dataset_ecuaciones_urbanas.zip"

CLASS_FOLDERS = {
    "triciclo de tamales": "tamales",
    "carrito de papas y botanas": "papas_botanas",
    "carrito de raspados": "raspados",
    "triciclo de pan y café": "pan_cafe",
    "otro": "otro",
    "no identificado": "no_identificado"
}

CSV_HEADERS = [
    "fecha_hora",
    "tipologia_detectada",
    "tipologia_final",
    "categoria_personalizada",
    "fue_corregida",
    "confianza_ia",
    "ecuacion_final",
    "elemento_clave",
    "latitud",
    "longitud",
    "precision_metros",
    "color_detectado",
    "imagen_captura",
    "imagen_dataset"
]

os.makedirs(CAPTURE_DIR, exist_ok=True)
os.makedirs(DATASET_DIR, exist_ok=True)

for folder in CLASS_FOLDERS.values():
    os.makedirs(os.path.join(DATASET_DIR, folder), exist_ok=True)


def ensure_csv():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(CSV_HEADERS)
        return

    try:
        with open(CSV_FILE, "r", newline="", encoding="utf-8") as f:
            current_headers = next(csv.reader(f), [])

        if current_headers != CSV_HEADERS:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            os.rename(CSV_FILE, f"registros_ecuaciones_urbanas_backup_{stamp}.csv")

            with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(CSV_HEADERS)

    except Exception:
        with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(CSV_HEADERS)


def save_base64_image(image_data_uri, filepath):
    if not image_data_uri or "," not in image_data_uri:
        return False

    try:
        _, encoded = image_data_uri.split(",", 1)

        with open(filepath, "wb") as img_file:
            img_file.write(base64.b64decode(encoded))

        return True

    except Exception:
        return False


FRONTEND_HTML = r"""
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>Ecuaciones Urbanas</title>

<link rel="manifest" href="/static/manifest.json">
<meta name="theme-color" content="#121214">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Ecuaciones">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<link rel="apple-touch-icon" href="/static/icon-192.png">

<style>
:root {
    --bg: #121214;
    --paper: #f3f0e8;
    --paper2: #e7e1d4;
    --ink: #111;
    --text: #f3f4f6;
    --muted: #aeb2ba;
    --line: #d9d2c4;
    --panel: #1a1a1e;
}

* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

html,
body {
    width: 100%;
    height: 100%;
}

body {
    font-family: Helvetica, Arial, sans-serif;
    background: var(--bg);
    color: var(--text);
    overflow: hidden;
}

.screen {
    display: none;
    width: 100vw;
    height: 100vh;
    overflow: hidden;
    position: relative;
}

.screen.active {
    display: flex;
}

button,
input {
    font-family: Helvetica, Arial, sans-serif;
}

.back-arrow,
.home-button {
    position: absolute;
    top: 28px;
    height: 44px;
    border-radius: 999px;
    border: 1px solid currentColor;
    background: transparent;
    color: inherit;
    cursor: pointer;
    z-index: 20;
}

.back-arrow {
    left: 28px;
    width: 44px;
    font-size: 1.35rem;
    display: flex;
    align-items: center;
    justify-content: center;
    padding-bottom: 2px;
}

.home-button {
    right: 28px;
    padding: 0 18px;
    font-size: 0.64rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

.back-arrow:hover,
.home-button:hover {
    background: rgba(255,255,255,0.08);
}

.btn {
    border: 1px solid #3f3f46;
    background: #27272a;
    color: var(--text);
    padding: 14px 22px;
    border-radius: 999px;
    font-weight: 700;
    font-size: 0.95rem;
    cursor: pointer;
    text-transform: lowercase;
    min-width: 160px;
}

.btn:hover {
    background: #3f3f46;
}

.btn:disabled {
    opacity: 0.4;
    cursor: not-allowed;
}

.btn-primary {
    background: var(--paper);
    color: var(--ink);
    border-color: var(--paper);
}

.btn-light {
    background: transparent;
    color: var(--ink);
    border-color: var(--ink);
}

.btn-light:hover {
    background: var(--ink);
    color: var(--paper);
}

.kicker {
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--line);
    margin-bottom: 20px;
}

.title-large {
    font-size: clamp(3.2rem, 8vw, 7.3rem);
    line-height: 0.9;
    letter-spacing: -0.075em;
    font-weight: 700;
    text-transform: lowercase;
}

.subtitle {
    margin: 24px auto 0;
    color: var(--muted);
    line-height: 1.55;
    font-size: 1rem;
    max-width: 620px;
    text-align: center;
}

.center-content {
    max-width: 900px;
    width: 100%;
    text-align: center;
    display: flex;
    flex-direction: column;
    align-items: center;
}

.method-buttons,
.confirm-buttons,
.correct-grid {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 18px;
    margin-top: 44px;
    flex-wrap: wrap;
    width: 100%;
}

/* PORTADA */

#screen-cover {
    background: var(--paper);
    color: var(--ink);
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 48px;
}

.cover-links {
    position: absolute;
    right: 24px;
    bottom: 20px;
    display: flex;
    gap: 14px;
}

.cover-links a {
    font-size: 0.78rem;
    color: #6d675f;
    text-decoration: none;
}

.cover-kicker {
    font-size: 0.82rem;
    font-weight: 700;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: #6f6a60;
    margin-bottom: 22px;
}

.cover-title {
    font-size: clamp(4rem, 9vw, 8.5rem);
    font-weight: 700;
    letter-spacing: -0.075em;
    line-height: 0.9;
    text-transform: lowercase;
}

.cover-subtitle {
    font-size: 1rem;
    color: #555;
    margin-top: 26px;
    margin-bottom: 42px;
}

/* PANTALLAS */

#screen-method,
#screen-confirm,
#screen-correct {
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 48px;
}

#screen-camera,
#screen-upload {
    align-items: center;
    justify-content: center;
    padding: 72px;
}

/* CÁMARA */

.camera-stage {
    width: min(100%, 1080px);
    height: min(76vh, 700px);
    display: grid;
    grid-template-columns: 1.25fr 0.75fr;
    gap: 32px;
    align-items: center;
}

.camera-frame {
    width: 100%;
    height: 100%;
    background: #050506;
    border: 1px solid #2d2d34;
    border-radius: 18px;
    overflow: hidden;
    position: relative;
}

#video,
#captured-preview {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

#video {
    transform: scaleX(-1);
}

#captured-preview-container {
    position: absolute;
    inset: 0;
    display: none;
    background: #050506;
}

.camera-info {
    display: flex;
    flex-direction: column;
    justify-content: center;
}

.screen-heading {
    font-size: clamp(2.5rem, 5vw, 5rem);
    line-height: 0.95;
    letter-spacing: -0.06em;
    font-weight: 700;
    text-transform: lowercase;
}

.screen-text {
    margin-top: 22px;
    color: var(--muted);
    line-height: 1.55;
    font-size: 1rem;
}

.screen-actions {
    display: flex;
    gap: 12px;
    margin-top: 34px;
    flex-wrap: wrap;
}

/* SUBIR ARCHIVO */

.upload-stage {
    width: min(100%, 1020px);
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 34px;
    align-items: center;
}

.upload-zone {
    min-height: 500px;
    border: 1px dashed #555866;
    border-radius: 24px;
    background: #18181d;
    color: #c9cbd2;
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 36px;
    cursor: pointer;
}

.upload-preview {
    width: 100%;
    height: 500px;
    border-radius: 24px;
    overflow: hidden;
    background: #080809;
    border: 1px solid #2d2d34;
    display: none;
}

.upload-preview img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

/* VALIDACIÓN */

.confirm-type {
    font-size: clamp(2.6rem, 5vw, 5rem);
    line-height: 0.95;
    letter-spacing: -0.06em;
    font-weight: 700;
    text-transform: lowercase;
    margin-top: 22px;
}

.confirm-note {
    margin-top: 24px;
    color: #b8bbc3;
    font-size: 1rem;
    line-height: 1.5;
    max-width: 620px;
}

.confidence-pill {
    margin-top: 26px;
    display: inline-block;
    padding: 8px 14px;
    border-radius: 999px;
    border: 1px solid #444851;
    color: #d7d9de;
    font-size: 0.82rem;
    text-transform: lowercase;
}

.confidence-pill.low {
    border-color: #8b6b3c;
    color: #ffdfaa;
}

.correct-grid .btn {
    min-width: 220px;
}

.other-box {
    display: none;
    margin-top: 28px;
    width: 100%;
    max-width: 500px;
}

.other-input {
    width: 100%;
    padding: 14px 18px;
    border-radius: 16px;
    border: 1px solid #444851;
    background: #1a1a1e;
    color: #f3f4f6;
    font-size: 1rem;
    margin-bottom: 14px;
    outline: none;
    text-transform: lowercase;
}

/* PÓSTER */

#screen-poster {
    background: #151518;
    align-items: center;
    justify-content: center;
    flex-direction: column;
    padding: 24px;
}

.poster {
    width: min(380px, 88vw);
    aspect-ratio: 5 / 7.3;
    height: auto;
    background: var(--paper);
    color: var(--ink);
    padding: 24px 20px 28px;
    display: grid;
    grid-template-rows: auto 45% auto;
    gap: 22px;
    box-shadow: 0 25px 50px rgba(0,0,0,0.45);
}

.poster-header {
    text-align: center;
    font-size: 0.66rem;
    font-weight: 700;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    line-height: 1;
    font-family: Helvetica, Arial, sans-serif;
}

.canvas-wrap {
    width: 100%;
    height: 100%;
    min-height: 0;
    margin: 0 auto;
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
}

#poster-canvas {
    width: 100%;
    height: 100%;
    display: block;
}

.placeholder {
    position: absolute;
    color: #777;
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    text-align: center;
    padding: 20px;
    left: 50%;
    top: 50%;
    transform: translate(-50%, -50%);
}

.poster-footer {
    text-align: center;
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.poster-title {
    font-family: Helvetica, Arial, sans-serif;
    font-size: 1.62rem;
    font-weight: 700;
    letter-spacing: -0.045em;
    text-transform: lowercase;
    line-height: 0.92;
}

.equation-box {
    background: var(--paper2);
    border: 1px solid var(--line);
    padding: 9px 11px;
    width: 100%;
}

.equation {
    font-family: "Courier New", "Lucida Console", monospace;
    font-weight: 700;
    font-size: 0.78rem;
    line-height: 1.20;
    text-transform: lowercase;
}

.poster-actions {
    width: min(340px, 84vw);
    display: flex;
    gap: 10px;
    margin-top: 14px;
    justify-content: center;
    flex-wrap: wrap;
}

.poster-status {
    margin-top: 10px;
    font-size: 0.78rem;
    color: #9ea3ad;
    min-height: 18px;
    text-align: center;
}

/* LOADING */

.loading {
    position: fixed;
    inset: 0;
    background: rgba(21,21,24,0.92);
    z-index: 100;
    display: none;
    align-items: center;
    justify-content: center;
    flex-direction: column;
    gap: 18px;
}

.spinner {
    width: 42px;
    height: 42px;
    border: 3px solid rgba(217,210,196,0.16);
    border-top-color: var(--paper);
    border-radius: 50%;
    animation: spin 1s linear infinite;
}

.loading-text {
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: lowercase;
}

@keyframes spin {
    to { transform: rotate(360deg); }
}

.toast {
    position: fixed;
    right: 24px;
    bottom: 24px;
    background: var(--panel);
    border: 1px solid #2d2d34;
    color: var(--text);
    padding: 12px 18px;
    border-radius: 6px;
    font-weight: 700;
    font-size: 0.78rem;
    display: none;
    max-width: 520px;
    z-index: 200;
}

@media(max-width:980px) {
    .camera-stage,
    .upload-stage {
        grid-template-columns: 1fr;
        height: auto;
    }

    .camera-frame {
        height: 46vh;
    }

    .upload-zone,
    .upload-preview {
        min-height: 320px;
        height: 320px;
    }

    .poster {
        width: min(320px, 90vw);
    }

    .poster-actions {
        width: min(320px, 90vw);
    }
}

@page {
    size: 5cm 7.3cm;
    margin: 0;
}

@media print {
    html,
    body {
        width: 5cm !important;
        height: 7.3cm !important;
        margin: 0 !important;
        padding: 0 !important;
        overflow: hidden !important;
        background: white !important;
    }

    .screen:not(#screen-poster),
    .poster-actions,
    .poster-status,
    .back-arrow,
    .home-button,
    .loading,
    .toast {
        display: none !important;
    }

    #screen-poster {
        display: flex !important;
        width: 5cm !important;
        height: 7.3cm !important;
        background: white !important;
        padding: 0 !important;
        margin: 0 !important;
        align-items: stretch !important;
        justify-content: stretch !important;
    }

    .poster {
        width: 5cm !important;
        height: 7.3cm !important;
        padding: 0.28cm 0.24cm 0.34cm !important;
        gap: 0.20cm !important;
        box-shadow: none !important;
        display: grid !important;
        grid-template-rows: auto 45% auto !important;
        margin: 0 !important;
    }

    .poster-header {
        font-size: 7.2pt !important;
    }

    .canvas-wrap {
        width: 100% !important;
        height: 100% !important;
        min-height: 0 !important;
    }

    .poster-title {
        font-family: Helvetica, Arial, sans-serif !important;
        font-size: 14.5pt !important;
        line-height: 0.92 !important;
    }

    .equation-box {
        padding: 0.10cm !important;
    }

    .equation {
        font-size: 5.8pt !important;
        line-height: 1.15 !important;
    }
}
</style>
</head>

<body>

<section id="screen-cover" class="screen active">
    <div class="cover-links">
        <a href="/download/qgis_csv">descargar registros</a>
        <a href="/download/dataset_zip">descargar dataset</a>
    </div>

    <div>
        <div class="cover-kicker">archivo visual</div>
        <h1 class="cover-title">ecuaciones urbanas</h1>
        <p class="cover-subtitle">clasificación visual del comercio ambulante</p>
        <button class="btn btn-light" id="btn-start">comenzar</button>
    </div>
</section>

<section id="screen-method" class="screen">
    <button class="back-arrow" id="back-method">←</button>
    <button class="home-button go-home">inicio</button>

    <div class="center-content">
        <div class="kicker">paso 01</div>
        <h2 class="title-large">¿cómo quieres registrar el puesto?</h2>
        <p class="subtitle">Puedes tomar una fotografía directamente con la cámara o subir una imagen existente desde tu dispositivo.</p>

        <div class="method-buttons">
            <button class="btn btn-primary" id="btn-use-camera">usar cámara</button>
            <button class="btn" id="btn-use-upload">subir archivo</button>
        </div>
    </div>
</section>

<section id="screen-camera" class="screen">
    <button class="back-arrow" id="back-camera">←</button>
    <button class="home-button go-home">inicio</button>

    <div class="camera-stage">
        <div class="camera-frame">
            <video id="video" autoplay playsinline muted></video>
            <div id="captured-preview-container">
                <img id="captured-preview" src="">
            </div>
        </div>

        <div class="camera-info">
            <div class="kicker">cámara</div>
            <h2 class="screen-heading">encuadra el puesto</h2>
            <p class="screen-text">Captura una imagen donde se distingan los elementos principales del puesto.</p>

            <div class="screen-actions">
                <button class="btn" id="btn-camera">activar cámara</button>
                <button class="btn" id="btn-capture" disabled>capturar</button>
                <button class="btn btn-primary" id="btn-analyze-camera" disabled>analizar imagen</button>
            </div>
        </div>
    </div>
</section>

<section id="screen-upload" class="screen">
    <button class="back-arrow" id="back-upload">←</button>
    <button class="home-button go-home">inicio</button>

    <div class="upload-stage">
        <div class="upload-zone" id="drop-zone">
            <input type="file" id="file-input" accept="image/*" capture="environment" style="display:none;">
            <div>
                <div class="kicker">archivo</div>
                <h2 class="screen-heading">sube una imagen</h2>
                <p class="screen-text">Selecciona una fotografía donde el puesto y sus objetos principales sean visibles.</p>
            </div>
        </div>

        <div>
            <div class="upload-preview" id="upload-preview">
                <img id="upload-preview-img" src="">
            </div>

            <div class="screen-actions">
                <button class="btn" id="btn-select-file">seleccionar archivo</button>
                <button class="btn btn-primary" id="btn-analyze-upload" disabled>analizar imagen</button>
            </div>
        </div>
    </div>
</section>

<section id="screen-confirm" class="screen">
    <button class="back-arrow" id="back-confirm">←</button>
    <button class="home-button go-home">inicio</button>

    <div class="center-content">
        <div class="kicker">tipología encontrada</div>
        <div class="confirm-type" id="confirm-type">sin identificar</div>
        <div class="confidence-pill" id="confidence-pill">confianza: media</div>

        <p class="confirm-note" id="confirm-note">¿La clasificación es correcta?</p>

        <div class="other-box" id="confirm-other-box">
            <input class="other-input" id="confirm-other-category-input" type="text" placeholder="escribe qué tipo de puesto es">
            <textarea class="other-input other-textarea" id="confirm-other-elements-input" placeholder="escribe los elementos que lo componen, por ejemplo: hielera + mesa plegable + vasos"></textarea>
        </div>

        <div class="confirm-buttons">
            <button class="btn btn-primary" id="btn-confirm-generate">sí, generar poster</button>
            <button class="btn" id="btn-correct">corregir clasificación</button>
        </div>
    </div>
</section>

<section id="screen-correct" class="screen">
    <button class="back-arrow" id="back-correct">←</button>
    <button class="home-button go-home">inicio</button>

    <div class="center-content">
        <div class="kicker">corregir clasificación</div>
        <h2 class="title-large">¿cuál es la tipología correcta?</h2>

        <div class="correct-grid">
            <button class="btn btn-primary correct-option" data-type="triciclo de tamales">tamales</button>
            <button class="btn correct-option" data-type="carrito de papas y botanas">papas / botanas / chicharrones</button>
            <button class="btn correct-option" data-type="carrito de raspados">raspados</button>
            <button class="btn correct-option" data-type="triciclo de pan y café">pan / café</button>
            <button class="btn correct-option" data-type="otro">otro</button>
            <button class="btn correct-option" data-type="no identificado">no identificado</button>
        </div>

        <div class="other-box" id="other-category-box">
            <input class="other-input" id="other-category-input" type="text" placeholder="escribe la categoría">
            <textarea class="other-input other-textarea" id="other-elements-input" placeholder="escribe los elementos que lo componen, por ejemplo: hielera + mesa plegable + vasos"></textarea>
            <button class="btn btn-primary" id="btn-confirm-other">confirmar categoría</button>
        </div>
    </div>
</section>

<section id="screen-poster" class="screen">
    <button class="back-arrow" id="back-poster">←</button>
    <button class="home-button go-home">inicio</button>

    <section class="poster">
        <div class="poster-header">ecuaciones urbanas</div>

        <div class="canvas-wrap">
            <canvas id="poster-canvas" width="900" height="1180"></canvas>
            <div class="placeholder" id="placeholder">captura o sube una fotografía para comenzar</div>
        </div>

        <div class="poster-footer">
            <div class="poster-title" id="p-title">ecuación por resolver</div>
            <div class="equation-box">
                <div class="equation" id="p-equation">esperando ecuación</div>
            </div>
        </div>
    </section>

    <div class="poster-actions">
        <button class="btn" id="btn-download" disabled>descargar jpg</button>
        <button class="btn" id="btn-new">nuevo registro</button>
    </div>

    <div class="poster-status" id="poster-status"></div>
</section>

<div class="loading" id="loading">
    <div class="spinner"></div>
    <div class="loading-text" id="loading-msg">resolviendo ecuación urbana...</div>
</div>

<canvas id="hidden-canvas" style="display:none;"></canvas>
<canvas id="small-canvas" style="display:none;"></canvas>
<div class="toast" id="toast">mensaje</div>

<script>
const video = document.getElementById("video");
const capturedContainer = document.getElementById("captured-preview-container");
const capturedPreview = document.getElementById("captured-preview");
const fileInput = document.getElementById("file-input");
const dropZone = document.getElementById("drop-zone");
const uploadPreview = document.getElementById("upload-preview");
const uploadPreviewImg = document.getElementById("upload-preview-img");

const btnStart = document.getElementById("btn-start");
const btnUseCamera = document.getElementById("btn-use-camera");
const btnUseUpload = document.getElementById("btn-use-upload");
const btnCamera = document.getElementById("btn-camera");
const btnCapture = document.getElementById("btn-capture");
const btnAnalyzeCamera = document.getElementById("btn-analyze-camera");
const btnAnalyzeUpload = document.getElementById("btn-analyze-upload");
const btnSelectFile = document.getElementById("btn-select-file");
const btnPrint = document.getElementById("btn-print");
const btnDownload = document.getElementById("btn-download");
const btnNew = document.getElementById("btn-new");
const btnConfirmGenerate = document.getElementById("btn-confirm-generate");
const btnCorrect = document.getElementById("btn-correct");

const posterCanvas = document.getElementById("poster-canvas");
const posterCtx = posterCanvas.getContext("2d");
const hiddenCanvas = document.getElementById("hidden-canvas");
const hiddenCtx = hiddenCanvas.getContext("2d");
const smallCanvas = document.getElementById("small-canvas");
const smallCtx = smallCanvas.getContext("2d");
const placeholder = document.getElementById("placeholder");

const confirmType = document.getElementById("confirm-type");
const confirmNote = document.getElementById("confirm-note");
const confidencePill = document.getElementById("confidence-pill");
const posterStatus = document.getElementById("poster-status");

const loading = document.getElementById("loading");
const loadingMsg = document.getElementById("loading-msg");
const toast = document.getElementById("toast");

const otherCategoryBox = document.getElementById("other-category-box");
const otherCategoryInput = document.getElementById("other-category-input");
const otherElementsInput = document.getElementById("other-elements-input");
const btnConfirmOther = document.getElementById("btn-confirm-other");

const confirmOtherBox = document.getElementById("confirm-other-box");
const confirmOtherCategoryInput = document.getElementById("confirm-other-category-input");
const confirmOtherElementsInput = document.getElementById("confirm-other-elements-input");

let screenHistory = [];
let stream = null;
let isCameraActive = false;
let loadedImage = null;
let loadedImageDataUrl = "";
let lastInputMode = "method";

let detectedCategory = "no identificado";
let finalCategory = "no identificado";
let customOtherCategory = "";
let customOtherElements = "";
let highlightColorHex = "#766c62";
let lastEquation = "";
let lastElement = "";
let confidenceLevel = "media";
let corrected = false;

// Filtro final fijo: Manchas por Sombra
const FIXED_RESOLUTION = 320;
const FIXED_DOT_SCALE = 0.83;
const FIXED_THRESHOLD = 0.29;
const FIXED_CONTRAST = 10;
const FIXED_BRIGHTNESS = -66;
const FIXED_EDGE_STRENGTH = 1.00;
const FIXED_DENSITY = 0.99;
const FIXED_NOISE = 0.04;
const FIXED_SOFTNESS = 0.5;

const PRINT_POSTER_WIDTH_CM = 5;
const PRINT_POSTER_HEIGHT_CM = 7.3;
const EXPORT_DPI = 300;
const PX_PER_CM = EXPORT_DPI / 2.54;
const EXPORT_W = Math.round(PRINT_POSTER_WIDTH_CM * PX_PER_CM);
const EXPORT_H = Math.round(PRINT_POSTER_HEIGHT_CM * PX_PER_CM);

const TYPE_DISPLAY = {
    "triciclo de tamales": "triciclo de tamales",
    "carrito de papas y botanas": "carrito de papas y botanas",
    "carrito de raspados": "carrito de raspados",
    "triciclo de pan y café": "triciclo de pan y café",
    "otro": "otro",
    "no identificado": "no identificado"
};

const TYPE_EQUATIONS = {
    "triciclo de tamales": "vaporera de metal + triciclo de carga = triciclo de tamales",
    "carrito de papas y botanas": "bolsas de frituras + chicharrones dorados = carrito de papas y botanas",
    "carrito de raspados": "jarabes de colores + hielo = carrito de raspados",
    "triciclo de pan y café": "canasto de pan + termo de café = triciclo de pan y café",
    "otro": "elemento de venta + estructura ambulante = otro",
    "no identificado": "imagen ambigua + información insuficiente = no identificado"
};

const TYPE_COLORS = {
    "triciclo de tamales": "#d69b00",
    "carrito de papas y botanas": "#f05a00",
    "carrito de raspados": "#007bd8",
    "triciclo de pan y café": "#218a36",
    "otro": "#8a22c8",
    "no identificado": "#665c52"
};

function showScreen(id, saveHistory = true) {
    const current = document.querySelector(".screen.active");

    if (saveHistory && current && current.id !== id) {
        screenHistory.push(current.id);
    }

    document.querySelectorAll(".screen").forEach(screen => {
        screen.classList.remove("active");
    });

    document.getElementById(id).classList.add("active");
}

function goBack() {
    const previous = screenHistory.pop();
    if (previous) {
        showScreen(previous, false);
    }
}

function goHome() {
    stopCamera();
    screenHistory = [];
    showScreen("screen-cover", false);
}

document.getElementById("back-method").addEventListener("click", goBack);

document.getElementById("back-camera").addEventListener("click", () => {
    stopCamera();
    goBack();
});

document.getElementById("back-upload").addEventListener("click", goBack);
document.getElementById("back-confirm").addEventListener("click", goBack);
document.getElementById("back-correct").addEventListener("click", goBack);
document.getElementById("back-poster").addEventListener("click", goBack);

document.querySelectorAll(".go-home").forEach(btn => {
    btn.addEventListener("click", goHome);
});

btnStart.addEventListener("click", () => showScreen("screen-method"));

btnUseCamera.addEventListener("click", async () => {
    lastInputMode = "camera";
    showScreen("screen-camera");
    await startCamera();
});

btnUseUpload.addEventListener("click", () => {
    lastInputMode = "upload";
    showScreen("screen-upload");
});

btnNew.addEventListener("click", () => {
    resetAll();
    showScreen("screen-method", false);
});

btnCamera.addEventListener("click", async () => {
    if (isCameraActive) {
        stopCamera();
    } else {
        await startCamera();
    }
});

async function startCamera() {
    try {
        stream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: "environment" },
            audio: false
        });

        video.srcObject = stream;
        isCameraActive = true;
        btnCamera.textContent = "apagar cámara";
        btnCapture.disabled = false;
        capturedContainer.style.display = "none";
        video.style.display = "block";
    } catch (err) {
        showToast("no se pudo acceder a la cámara. intenta subir un archivo.");
    }
}

function stopCamera() {
    if (stream) {
        stream.getTracks().forEach(track => track.stop());
    }

    video.srcObject = null;
    isCameraActive = false;
    btnCamera.textContent = "activar cámara";
    btnCapture.disabled = true;
}

btnCapture.addEventListener("click", () => {
    if (!isCameraActive || !stream) return;

    const tempCanvas = document.createElement("canvas");
    tempCanvas.width = video.videoWidth;
    tempCanvas.height = video.videoHeight;

    const tempCtx = tempCanvas.getContext("2d");
    tempCtx.translate(tempCanvas.width, 0);
    tempCtx.scale(-1, 1);
    tempCtx.drawImage(video, 0, 0, tempCanvas.width, tempCanvas.height);

    const dataUrl = tempCanvas.toDataURL("image/jpeg", 0.92);

    capturedPreview.src = dataUrl;
    video.style.display = "none";
    capturedContainer.style.display = "block";

    stopCamera();
    loadImage(dataUrl);
    btnAnalyzeCamera.disabled = false;
});

btnSelectFile.addEventListener("click", () => fileInput.click());
dropZone.addEventListener("click", () => fileInput.click());

fileInput.addEventListener("change", event => {
    handleFiles(event.target.files);
});

dropZone.addEventListener("dragover", event => {
    event.preventDefault();
    dropZone.style.borderColor = "#f3f0e8";
});

dropZone.addEventListener("dragleave", () => {
    dropZone.style.borderColor = "#555866";
});

dropZone.addEventListener("drop", event => {
    event.preventDefault();
    dropZone.style.borderColor = "#555866";
    handleFiles(event.dataTransfer.files);
});

function handleFiles(files) {
    if (!files || files.length === 0) return;

    const file = files[0];

    if (!file.type.startsWith("image/")) {
        showToast("el archivo debe ser una imagen.");
        return;
    }

    const reader = new FileReader();

    reader.onload = event => {
        loadImage(event.target.result);
        uploadPreviewImg.src = event.target.result;
        uploadPreview.style.display = "block";
        btnAnalyzeUpload.disabled = false;
    };

    reader.readAsDataURL(file);
}

function resetOther() {
    customOtherCategory = "";
    customOtherElements = "";

    if (otherCategoryInput) otherCategoryInput.value = "";
    if (otherElementsInput) otherElementsInput.value = "";
    if (otherCategoryBox) otherCategoryBox.style.display = "none";

    if (confirmOtherCategoryInput) confirmOtherCategoryInput.value = "";
    if (confirmOtherElementsInput) confirmOtherElementsInput.value = "";
    if (confirmOtherBox) confirmOtherBox.style.display = "none";
}

function buildOtherEquation(displayType) {
    const elements = customOtherElements.trim();

    if (elements) {
        return `${elements} = ${displayType}`;
    }

    return `elemento de venta + estructura ambulante = ${displayType}`;
}

function loadImage(src) {
    const img = new Image();

    img.onload = () => {
        loadedImage = img;
        loadedImageDataUrl = src;
        detectedCategory = "no identificado";
        finalCategory = "no identificado";
        highlightColorHex = "#766c62";
        lastEquation = "";
        lastElement = "";
        confidenceLevel = "media";
        corrected = false;
        posterStatus.textContent = "";
        resetOther();
        resetPoster();
        renderPopArt();
    };

    img.src = src;
}

function resetPoster() {
    document.getElementById("p-title").textContent = "ecuación por resolver";
    document.getElementById("p-equation").textContent = "esperando ecuación";
}

function resetAll() {
    stopCamera();

    screenHistory = [];
    loadedImage = null;
    loadedImageDataUrl = "";
    detectedCategory = "no identificado";
    finalCategory = "no identificado";
    highlightColorHex = "#766c62";
    lastEquation = "";
    lastElement = "";
    confidenceLevel = "media";
    corrected = false;
    lastInputMode = "method";

    resetOther();

    capturedPreview.src = "";
    capturedContainer.style.display = "none";
    uploadPreviewImg.src = "";
    uploadPreview.style.display = "none";

    btnAnalyzeCamera.disabled = true;
    btnAnalyzeUpload.disabled = true;
    if (btnPrint) btnPrint.disabled = true;
    btnDownload.disabled = true;

    placeholder.style.display = "block";
    posterStatus.textContent = "";

    posterCtx.fillStyle = "#f3f0e8";
    posterCtx.fillRect(0, 0, posterCanvas.width, posterCanvas.height);

    resetPoster();
}

function getContainRect(imgW, imgH, targetW, targetH) {
    const imgRatio = imgW / imgH;
    const targetRatio = targetW / targetH;

    let w, h, x, y;

    if (imgRatio > targetRatio) {
        w = targetW;
        h = targetW / imgRatio;
        x = 0;
        y = (targetH - h) / 2;
    } else {
        h = targetH;
        w = targetH * imgRatio;
        x = (targetW - w) / 2;
        y = 0;
    }

    return { x, y, w, h };
}

function getPalette(category) {
    const palettes = {
        "triciclo de tamales": {
            light: "#ffe46b",
            mid: "#e0aa00",
            dark: "#7a5600"
        },

        "carrito de papas y botanas": {
            light: "#ffae42",
            mid: "#f06a00",
            dark: "#8a2e00"
        },

        "carrito de raspados": {
            light: "#7fd3ff",
            mid: "#0089e8",
            dark: "#00427a"
        },

        "triciclo de pan y café": {
            light: "#8bdc7b",
            mid: "#2f9a42",
            dark: "#14501f"
        },

        "otro": {
            light: "#d5a7f0",
            mid: "#8a52b8",
            dark: "#4a2869"
        },

        "no identificado": {
            light: "#b9afa5",
            mid: "#766c62",
            dark: "#3f3933"
        }
    };

    return palettes[category] || palettes["no identificado"];
}

function hexToRgb(hex) {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);

    return result ? {
        r: parseInt(result[1], 16),
        g: parseInt(result[2], 16),
        b: parseInt(result[3], 16)
    } : { r: 150, g: 150, b: 150 };
}

function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
}

function getPixelGray(data, x, y, w, h) {
    x = clamp(Math.round(x), 0, w - 1);
    y = clamp(Math.round(y), 0, h - 1);

    const idx = (y * w + x) * 4;
    return data[idx];
}

function stableNoise(x, y) {
    const n = Math.sin(x * 12.9898 + y * 78.233) * 43758.5453;
    return n - Math.floor(n);
}

function drawImageCoverToCanvas(ctx, img, targetW, targetH) {
    const imgRatio = img.width / img.height;
    const targetRatio = targetW / targetH;

    let sx = 0;
    let sy = 0;
    let sw = img.width;
    let sh = img.height;

    if (imgRatio > targetRatio) {
        sh = img.height;
        sw = sh * targetRatio;
        sx = (img.width - sw) / 2;
    } else {
        sw = img.width;
        sh = sw / targetRatio;
        sy = (img.height - sh) / 2;
    }

    ctx.drawImage(img, sx, sy, sw, sh, 0, 0, targetW, targetH);
}

function renderFilteredPopArt(targetCtx, sourceImage, targetX, targetY, targetW, targetH, color) {
    const cols = FIXED_RESOLUTION;
    const rows = Math.max(1, Math.round(cols * (targetH / targetW)));

    hiddenCanvas.width = cols;
    hiddenCanvas.height = rows;
    hiddenCtx.clearRect(0, 0, cols, rows);
    drawImageCoverToCanvas(hiddenCtx, sourceImage, cols, rows);

    let imgData = hiddenCtx.getImageData(0, 0, cols, rows);
    let data = imgData.data;

    // Filtro final aprobado:
    // Duotono / pop-art con trama azul sobre fondo crema.
    // Mantiene la foto reconocible sin volverse rectángulo sólido.
    const contrast = 22;
    const brightness = -36;
    const factor = (259 * (contrast + 255)) / (255 * (259 - contrast));

    for (let i = 0; i < data.length; i += 4) {
        let r = data[i];
        let g = data[i + 1];
        let b = data[i + 2];

        let gray = 0.299 * r + 0.587 * g + 0.114 * b;
        gray = factor * (gray - 128) + 128 + brightness;
        gray = clamp(gray, 0, 255);

        data[i] = gray;
        data[i + 1] = gray;
        data[i + 2] = gray;
        data[i + 3] = 255;
    }

    hiddenCtx.putImageData(imgData, 0, 0);

    smallCanvas.width = cols;
    smallCanvas.height = rows;
    smallCtx.clearRect(0, 0, cols, rows);
    smallCtx.filter = "blur(0.35px)";
    smallCtx.drawImage(hiddenCanvas, 0, 0);
    smallCtx.filter = "none";

    imgData = smallCtx.getImageData(0, 0, cols, rows);
    data = imgData.data;

    const cellW = targetW / cols;
    const cellH = targetH / rows;
    const maxRadius = Math.min(cellW, cellH) * 0.74;
    const effectiveThreshold = 0.055;

    targetCtx.save();
    targetCtx.globalCompositeOperation = "source-over";

    // Fondo limpio dentro del rectángulo de imagen.
    targetCtx.fillStyle = "#f3f0e8";
    targetCtx.fillRect(targetX, targetY, targetW, targetH);

    for (let y = 0; y < rows; y++) {
        for (let x = 0; x < cols; x++) {
            const idx = (y * cols + x) * 4;
            const gray = data[idx] / 255;
            const darkness = 1 - gray;

            // Curva balanceada: suficiente azul en sombras y medios tonos,
            // pero deja blancos para que la imagen no se tape.
            let value = clamp((darkness - 0.015) / 0.985, 0, 1);
            value = Math.pow(value, 0.82);

            value += (stableNoise(x, y) - 0.5) * 0.012;
            value = clamp(value, 0, 1);

            if (value < effectiveThreshold) continue;

            const normalized = clamp(
                (value - effectiveThreshold) / Math.max(0.001, (1 - effectiveThreshold)),
                0,
                1
            );

            const radius = maxRadius * FIXED_DOT_SCALE * (0.10 + normalized * 0.98);
            if (radius < 0.045) continue;

            const cx = targetX + x * cellW + cellW / 2;
            const cy = targetY + y * cellH + cellH / 2;

            targetCtx.beginPath();
            targetCtx.arc(cx, cy, radius, 0, Math.PI * 2);
            targetCtx.fillStyle = `rgb(${color.r}, ${color.g}, ${color.b})`;
            targetCtx.fill();

            // Refuerzo solo en sombras fuertes para dar presencia tipo impreso.
            if (normalized > 0.78) {
                targetCtx.beginPath();
                targetCtx.arc(cx, cy, radius * 0.34, 0, Math.PI * 2);
                targetCtx.fill();
            }
        }
    }

    targetCtx.restore();
}

function renderPopArt() {
    if (!loadedImage) return;

    placeholder.style.display = "none";
    if (btnPrint) btnPrint.disabled = false;
    btnDownload.disabled = false;

    const category = finalCategory || detectedCategory || "no identificado";
    const color = hexToRgb(TYPE_COLORS[category] || TYPE_COLORS["no identificado"]);

    posterCtx.fillStyle = "#f3f0e8";
    posterCtx.fillRect(0, 0, posterCanvas.width, posterCanvas.height);

    renderFilteredPopArt(
        posterCtx,
        loadedImage,
        0,
        0,
        posterCanvas.width,
        posterCanvas.height,
        color
    );
}

async function analyzeCurrentImage() {
    if (!loadedImage) {
        showToast("primero carga o captura una imagen.");
        return;
    }

    loading.style.display = "flex";
    loadingMsg.textContent = "analizando tipología...";

    try {
        const uploadCanvas = document.createElement("canvas");
        const maxDim = 900;

        let w = loadedImage.width;
        let h = loadedImage.height;

        if (w > maxDim || h > maxDim) {
            if (w > h) {
                h = Math.round((h * maxDim) / w);
                w = maxDim;
            } else {
                w = Math.round((w * maxDim) / h);
                h = maxDim;
            }
        }

        uploadCanvas.width = w;
        uploadCanvas.height = h;
        uploadCanvas.getContext("2d").drawImage(loadedImage, 0, 0, w, h);

        const b64Image = uploadCanvas.toDataURL("image/jpeg", 0.9);

        const response = await fetch("/api/analyze", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ image: b64Image })
        });

        const data = await response.json().catch(() => null);

        if (!response.ok) {
            throw new Error(data?.error || "la red falló al procesar.");
        }

        if (!data) {
            throw new Error("el servidor no devolvió una respuesta válida.");
        }

        if (data.error) {
            throw new Error(data.error);
        }

        detectedCategory = (data.puesto_type || "no identificado").toLowerCase();
        finalCategory = detectedCategory;
        customOtherCategory = "";
        highlightColorHex = data.highlight_color_hex || TYPE_COLORS[detectedCategory] || "#766c62";
        confidenceLevel = (data.confidence_level || "media").toLowerCase();

        const elements = Array.isArray(data.key_elements)
            ? data.key_elements
            : ["elemento no identificado"];

        lastEquation = (data.urban_equation || TYPE_EQUATIONS[detectedCategory] || TYPE_EQUATIONS["no identificado"]).toLowerCase();
        lastElement = (elements[0] || "sin identificar").toLowerCase();
        corrected = false;

        updateConfirmScreen();
        showScreen("screen-confirm");
    } catch (err) {
        console.error(err);
        showToast(err.message || "error analizando con el servidor.");
    } finally {
        loading.style.display = "none";
    }
}

function updateConfirmScreen() {
    confirmType.textContent = TYPE_DISPLAY[detectedCategory] || detectedCategory;

    confidencePill.className = "confidence-pill";

    if (confidenceLevel === "baja") {
        confidencePill.classList.add("low");
    }

    confidencePill.textContent = "confianza: " + confidenceLevel;

    if (confirmOtherBox) {
        confirmOtherBox.style.display = detectedCategory === "otro" ? "block" : "none";
    }

    if (confidenceLevel === "baja" || detectedCategory === "no identificado") {
        confirmNote.textContent = "La clasificación no fue concluyente. Puedes generar el póster o corregir la clasificación manualmente.";
    } else if (detectedCategory === "otro") {
        confirmNote.textContent = "Se detectó otro tipo de puesto. Escribe la categoría específica y los elementos que la componen antes de generar el póster.";
    } else {
        confirmNote.textContent = "¿La clasificación es correcta?";
    }
}

function getDisplayCategory() {
    if (finalCategory === "otro" && customOtherCategory.trim()) {
        return customOtherCategory.trim().toLowerCase();
    }

    return TYPE_DISPLAY[finalCategory] || finalCategory;
}

function updatePosterTexts() {
    const displayType = getDisplayCategory();

    let equation = corrected
        ? (TYPE_EQUATIONS[finalCategory] || lastEquation)
        : (lastEquation || TYPE_EQUATIONS[finalCategory]);

    if (finalCategory === "otro" && customOtherCategory.trim()) {
        equation = buildOtherEquation(displayType);
    }

    document.getElementById("p-title").textContent = displayType;
    document.getElementById("p-equation").textContent = equation.toLowerCase();
}

btnAnalyzeCamera.addEventListener("click", () => analyzeCurrentImage());
btnAnalyzeUpload.addEventListener("click", () => analyzeCurrentImage());

btnCorrect.addEventListener("click", () => {
    showScreen("screen-correct");
});

document.querySelectorAll(".correct-option").forEach(btn => {
    btn.addEventListener("click", async () => {
        finalCategory = btn.dataset.type;
        corrected = finalCategory !== detectedCategory;
        highlightColorHex = TYPE_COLORS[finalCategory] || "#766c62";

        if (finalCategory === "otro") {
            otherCategoryBox.style.display = "block";
            otherCategoryInput.focus();
            return;
        }

        resetOther();
        await finalizeAndShowPoster();
    });
});

btnConfirmOther.addEventListener("click", async () => {
    const value = otherCategoryInput.value.trim();
    const elementsValue = otherElementsInput ? otherElementsInput.value.trim() : "";

    if (!value) {
        showToast("escribe una categoría para 'otro'.");
        return;
    }

    if (!elementsValue) {
        showToast("escribe los elementos que componen esta tipología.");
        return;
    }

    finalCategory = "otro";
    customOtherCategory = value.toLowerCase();
    customOtherElements = elementsValue.toLowerCase();
    lastElement = customOtherElements;
    corrected = true;
    highlightColorHex = TYPE_COLORS["otro"];

    await finalizeAndShowPoster();
});

btnConfirmGenerate.addEventListener("click", async () => {
    finalCategory = detectedCategory;
    corrected = false;

    if (finalCategory === "otro") {
        const value = confirmOtherCategoryInput ? confirmOtherCategoryInput.value.trim() : "";
        const elementsValue = confirmOtherElementsInput ? confirmOtherElementsInput.value.trim() : "";

        if (!value) {
            showToast("escribe qué tipo de puesto es.");
            if (confirmOtherCategoryInput) confirmOtherCategoryInput.focus();
            return;
        }

        if (!elementsValue) {
            showToast("escribe los elementos que componen esta tipología.");
            if (confirmOtherElementsInput) confirmOtherElementsInput.focus();
            return;
        }

        customOtherCategory = value.toLowerCase();
        customOtherElements = elementsValue.toLowerCase();
        lastElement = customOtherElements;
        highlightColorHex = TYPE_COLORS["otro"];
    }

    await finalizeAndShowPoster();
});

function getLocationPromise() {
    return new Promise(resolve => {
        if (!navigator.geolocation) {
            resolve({
                latitud: "",
                longitud: "",
                precision_metros: ""
            });
            return;
        }

        navigator.geolocation.getCurrentPosition(
            pos => resolve({
                latitud: pos.coords.latitude,
                longitud: pos.coords.longitude,
                precision_metros: pos.coords.accuracy
            }),
            err => resolve({
                latitud: "",
                longitud: "",
                precision_metros: ""
            }),
            {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 0
            }
        );
    });
}

async function finalizeAndShowPoster() {
    if (!loadedImageDataUrl) {
        showToast("no hay imagen para guardar.");
        return;
    }

    loading.style.display = "flex";
    loadingMsg.textContent = "guardando imagen y ubicación...";

    try {
        const geo = await getLocationPromise();

        updatePosterTexts();
        renderPopArt();

        const displayType = getDisplayCategory();

        const equationToSave = finalCategory === "otro" && customOtherCategory.trim()
            ? buildOtherEquation(displayType)
            : (
                corrected
                    ? (TYPE_EQUATIONS[finalCategory] || lastEquation)
                    : (lastEquation || TYPE_EQUATIONS[finalCategory])
            );

        const payload = {
            tipologia_detectada: detectedCategory,
            tipologia_final: finalCategory,
            categoria_personalizada: finalCategory === "otro" ? customOtherCategory : "",
            elementos_personalizados: finalCategory === "otro" ? customOtherElements : "",
            fue_corregida: corrected ? "sí" : "no",
            confianza_ia: confidenceLevel,
            ecuacion_final: equationToSave,
            elemento_clave: finalCategory === "otro" && customOtherElements ? customOtherElements : lastElement,
            latitud: geo.latitud,
            longitud: geo.longitud,
            precision_metros: geo.precision_metros,
            color_detectado: highlightColorHex,
            image: loadedImageDataUrl
        };

        const response = await fetch("/api/save_record", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        const data = await response.json().catch(() => null);

        if (!response.ok || !data || data.ok === false) {
            throw new Error(data?.error || "no se pudo guardar el registro final.");
        }

        if (data.imagen_dataset) {
            posterStatus.textContent = geo.latitud && geo.longitud
                ? "imagen y ubicación guardadas"
                : "imagen guardada · ubicación no disponible";
        } else {
            posterStatus.textContent = "registro guardado · imagen no confirmada";
        }

        showScreen("screen-poster");
    } catch (err) {
        console.error(err);
        showToast(err.message || "error guardando el registro final.");
    } finally {
        loading.style.display = "none";
    }
}

btnDownload.addEventListener("click", () => {
    const captureCanvas = document.createElement("canvas");
    captureCanvas.width = EXPORT_W;
    captureCanvas.height = EXPORT_H;

    const ctx = captureCanvas.getContext("2d");

    const W = captureCanvas.width;
    const H = captureCanvas.height;

    const category = finalCategory || detectedCategory || "no identificado";
    const color = hexToRgb(TYPE_COLORS[category] || TYPE_COLORS["no identificado"]);

    ctx.fillStyle = "#f3f0e8";
    ctx.fillRect(0, 0, W, H);

    ctx.textAlign = "center";
    ctx.textBaseline = "top";

    const titleTxt = document.getElementById("p-title").textContent;
    const equationTxt = document.getElementById("p-equation").textContent;

    function drawWrappedCenteredText(ctx, text, centerX, startY, maxWidth, lineHeight) {
        const words = text.split(" ");
        const lines = [];
        let line = "";

        for (let n = 0; n < words.length; n++) {
            const testLine = line ? line + " " + words[n] : words[n];
            const metrics = ctx.measureText(testLine);

            if (metrics.width > maxWidth && line) {
                lines.push(line);
                line = words[n];
            } else {
                line = testLine;
            }
        }

        if (line) lines.push(line);

        lines.forEach((l, i) => {
            ctx.fillText(l, centerX, startY + i * lineHeight);
        });

        return startY + lines.length * lineHeight;
    }

    ctx.fillStyle = "#111";
    ctx.font = `700 ${Math.round(W * 0.046)}px Helvetica, Arial, sans-serif`;
    ctx.fillText("ECUACIONES URBANAS", W / 2, Math.round(H * 0.040));

    const imageRect = {
        x: Math.round(W * 0.06),
        y: Math.round(H * 0.170),
        w: Math.round(W * 0.88),
        h: Math.round(H * 0.450)
    };

    renderFilteredPopArt(
        ctx,
        loadedImage,
        imageRect.x,
        imageRect.y,
        imageRect.w,
        imageRect.h,
        color
    );

    ctx.fillStyle = "#111";
    ctx.font = `700 ${Math.round(W * 0.092)}px Helvetica, Arial, sans-serif`;

    let currentY = Math.round(H * 0.700);

    currentY = drawWrappedCenteredText(
        ctx,
        titleTxt,
        W / 2,
        currentY,
        Math.round(W * 0.90),
        Math.round(W * 0.105)
    );

    currentY += Math.round(H * 0.016);

    const eqBoxX = Math.round(W * 0.06);
    const eqBoxY = currentY;
    const eqBoxW = Math.round(W * 0.88);
    const eqBoxH = Math.round(H * 0.108);

    ctx.fillStyle = "#e7e1d4";
    ctx.fillRect(eqBoxX, eqBoxY, eqBoxW, eqBoxH);

    ctx.strokeStyle = "#d9d2c4";
    ctx.lineWidth = Math.max(1, Math.round(W * 0.002));
    ctx.strokeRect(eqBoxX, eqBoxY, eqBoxW, eqBoxH);

    ctx.fillStyle = "#111";
    ctx.font = `700 ${Math.round(W * 0.036)}px "Courier New", monospace`;

    const lineHeight = Math.round(W * 0.046);
    const words = equationTxt.split(" ");
    const lines = [];
    let line = "";

    for (let n = 0; n < words.length; n++) {
        const testLine = line ? line + " " + words[n] : words[n];

        if (ctx.measureText(testLine).width > eqBoxW - Math.round(W * 0.08) && line) {
            lines.push(line);
            line = words[n];
        } else {
            line = testLine;
        }
    }

    if (line) lines.push(line);

    const textStartY = eqBoxY + (eqBoxH - lines.length * lineHeight) / 2 + Math.round(W * 0.006);

    lines.forEach((l, i) => {
        ctx.fillText(l, W / 2, textStartY + i * lineHeight);
    });

    const dlLink = document.createElement("a");
    dlLink.download = `ecuacion_${titleTxt.replace(/\s+/g, "_")}.jpg`;
    dlLink.href = captureCanvas.toDataURL("image/jpeg", 0.95);

    document.body.appendChild(dlLink);
    dlLink.click();
    document.body.removeChild(dlLink);

    showToast("imagen jpg descargada en formato 5 x 7.3 cm.");
});

function showToast(msg) {
    toast.textContent = msg;
    toast.style.display = "block";

    setTimeout(() => {
        toast.style.display = "none";
    }, 4500);
}

if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
        navigator.serviceWorker.register("/static/service-worker.js").catch(error => {
            console.log("service worker error:", error);
        });
    });
}
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return Response(
        FRONTEND_HTML,
        mimetype="text/html",
        headers={
            "Content-Type": "text/html; charset=utf-8",
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )


@app.route("/api/analyze", methods=["POST"])
def analyze():
    try:
        data = request.json

        if not data or "image" not in data:
            return jsonify({"error": "no se proporcionó ninguna imagen."}), 400

        image_data_uri = data["image"]

        if "," not in image_data_uri:
            return jsonify({"error": "formato de imagen inválido."}), 400

        header, encoded = image_data_uri.split(",", 1)

        mime_type = "image/jpeg"

        if "image/png" in header:
            mime_type = "image/png"
        elif "image/webp" in header:
            mime_type = "image/webp"

        api_key = os.environ.get("GEMINI_API_KEY")

        if not api_key:
            return jsonify({"error": "api key de gemini no configurada."}), 401

        gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

        system_prompt = """
eres un antropólogo urbano y curador de arte contemporáneo con un ojo clínico para la cultura popular mexicana e hispanoamericana.

estás catalogando el comercio ambulante bajo el proyecto "ecuaciones urbanas".

clasifica la imagen en una de estas 6 categorías:

1. "triciclo de tamales":
- elemento clave: vaporera metálica, olla de aluminio, manta, vapor, triciclo de carga.
- si aparece una olla grande metálica, cilindro metálico, vaporera o bote de aluminio asociado a venta ambulante, clasifica como "triciclo de tamales".

2. "carrito de papas y botanas":
- elemento clave: papas fritas, chicharrones, botanas, frituras, churritos, ruedas, bolsas grandes transparentes con frituras, bolsas voluminosas de botanas, costales transparentes, vitrinas, salsas y carrito de venta.
- pon especial atención a botanas dentro de bolsas grandes: aunque las papas o chicharrones no estén sueltos, si se observan frituras doradas, bolsas transparentes grandes con botanas, chicharrones inflados, papas amarillas, churritos naranjas o empaques voluminosos, clasifica como "carrito de papas y botanas".

3. "carrito de raspados":
- elemento clave: botellas de jarabe, hielo, bloque de hielo, texto de raspados, cepillo para hielo, vasos, sabores de colores.

4. "triciclo de pan y café":
- elemento clave: canasto de pan, pan dulce, conchas, bolsa de pan, termo de café, triciclo.

5. "otro":
- usa esta categoría cuando sí se observa un puesto ambulante o semifijo de comida, pero no pertenece a tamales, papas/botanas, raspados ni pan/café.
- ejemplos: tacos, tortas, elotes, esquites, dulces, aguas frescas, cocos, comida preparada, hot dogs, hamburguesas, fruta, jugos u otro comercio alimentario.

6. "no identificado":
- usa esta categoría cuando la imagen no permite identificar con claridad un puesto.
- ejemplos: imagen borrosa, oscura, demasiado cercana, sin elementos de venta claros, objeto tapado o fotografía accidental.

responde únicamente con json válido, sin markdown, sin explicación y sin texto extra.
todos los textos deben estar en minúsculas.

estructura obligatoria:
{
  "puesto_type": "triciclo de tamales | carrito de papas y botanas | carrito de raspados | triciclo de pan y café | otro | no identificado",
  "urban_equation": "elemento principal + elemento secundario = tipo de puesto",
  "key_elements": ["elemento 1", "elemento 2", "elemento 3"],
  "highlight_color_hex": "#hexadecimal",
  "confidence_level": "alta | media | baja"
}
"""

        payload = {
            "contents": [{
                "parts": [
                    {"text": system_prompt},
                    {"inlineData": {"mimeType": mime_type, "data": encoded}}
                ]
            }],
            "generationConfig": {"responseMimeType": "application/json"}
        }

        req = urllib.request.Request(
            gemini_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )

        with urllib.request.urlopen(req) as response:
            res_json = json.loads(response.read().decode("utf-8"))

        candidates = res_json.get("candidates", [])

        if not candidates:
            return jsonify({"error": "gemini no devolvió candidatos."}), 500

        parts = candidates[0].get("content", {}).get("parts", [])

        if not parts or "text" not in parts[0]:
            return jsonify({"error": "gemini no devolvió texto válido."}), 500

        try:
            parsed = json.loads(parts[0]["text"])

        except json.JSONDecodeError:
            return jsonify({
                "error": "gemini respondió algo que no es json válido.",
                "raw_response": parts[0]["text"]
            }), 500

        return jsonify(parsed)

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="ignore")
        return jsonify({"error": f"error de gemini http {e.code}: {error_body}"}), 500

    except Exception as e:
        return jsonify({"error": f"error interno del servidor: {str(e)}"}), 500


@app.route("/api/save_record", methods=["POST"])
def save_record():
    try:
        ensure_csv()
        data = request.json or {}

        fecha_hora = datetime.now().isoformat(timespec="seconds")
        tipologia_detectada = data.get("tipologia_detectada", "no identificado")
        tipologia_final = data.get("tipologia_final", "no identificado")
        categoria_personalizada = data.get("categoria_personalizada", "")
        fue_corregida = data.get("fue_corregida", "no")
        confianza_ia = data.get("confianza_ia", "media")
        ecuacion_final = data.get("ecuacion_final", "")
        elemento_clave = data.get("elemento_clave", "")
        latitud = data.get("latitud", "")
        longitud = data.get("longitud", "")
        precision_metros = data.get("precision_metros", "")
        color_detectado = data.get("color_detectado", "")
        image_data_uri = data.get("image", "")

        unique_id = uuid.uuid4().hex
        capture_filename = f"captura_{unique_id}.jpg"
        capture_filepath = os.path.join(CAPTURE_DIR, capture_filename)

        folder_name = CLASS_FOLDERS.get(tipologia_final, "no_identificado")
        dataset_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{unique_id[:8]}.jpg"
        dataset_filepath = os.path.join(DATASET_DIR, folder_name, dataset_filename)

        imagen_captura = capture_filepath if save_base64_image(image_data_uri, capture_filepath) else ""
        imagen_dataset = dataset_filepath if save_base64_image(image_data_uri, dataset_filepath) else ""

        with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                fecha_hora,
                tipologia_detectada,
                tipologia_final,
                categoria_personalizada,
                fue_corregida,
                confianza_ia,
                ecuacion_final,
                elemento_clave,
                latitud,
                longitud,
                precision_metros,
                color_detectado,
                imagen_captura,
                imagen_dataset
            ])

        return jsonify({
            "ok": True,
            "message": "registro guardado",
            "csv_file": CSV_FILE,
            "imagen_captura": imagen_captura,
            "imagen_dataset": imagen_dataset
        })

    except Exception as e:
        return jsonify({"ok": False, "error": f"error guardando registro: {str(e)}"}), 500


@app.route("/download/qgis_csv")
def download_qgis_csv():
    ensure_csv()
    return send_file(
        CSV_FILE,
        as_attachment=True,
        download_name="registros_ecuaciones_urbanas.csv",
        mimetype="text/csv"
    )


@app.route("/download/dataset_zip")
def download_dataset_zip():
    if os.path.exists(DATASET_ZIP):
        os.remove(DATASET_ZIP)

    shutil.make_archive("dataset_ecuaciones_urbanas", "zip", DATASET_DIR)

    return send_file(
        DATASET_ZIP,
        as_attachment=True,
        download_name="dataset_ecuaciones_urbanas.zip",
        mimetype="application/zip"
    )


if __name__ == "__main__":
    ensure_csv()
    port = int(os.environ.get("PORT", 8010))
    app.run(host="0.0.0.0", port=port)
