from flask import Flask, render_template, request
import os
import numpy as np
from werkzeug.utils import secure_filename

print("Starting Trashify application...")

app = Flask(__name__)

# ---------------- MODEL ----------------
try:
    from tensorflow.keras.models import load_model
    from tensorflow.keras.preprocessing import image

    model = load_model('models/updated_wastemodel.keras')
    HAS_MODEL = True
    print("Model loaded successfully.")
except Exception as e:
    print("Model load failed:", e)
    model = None
    HAS_MODEL = False


# ---------------- TRANSLATION ----------------
try:
    from deep_translator import GoogleTranslator
    HAS_TRANSLATOR = True
except Exception as e:
    print("Translator load failed:", e)
    HAS_TRANSLATOR = False


# ---------------- TTS ----------------
try:
    from gtts import gTTS
    HAS_GTTS = True
except Exception as e:
    print("gTTS failed:", e)
    HAS_GTTS = False


# ---------------- PANDAS ----------------
try:
    import pandas as pd
    HAS_PANDAS = True
except Exception as e:
    print("Pandas failed:", e)
    HAS_PANDAS = False


# ---------------- CONFIG ----------------
class_names = ['Battery','Biological','Clothes','Glass','Paper','Plastic','Shoes']

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# ---------------- CLASSIFICATION ----------------
def classify_image(img_path):
    if HAS_MODEL and model:
        try:
            img = image.load_img(img_path, target_size=(224, 224))
            img_array = image.img_to_array(img)
            img_array = img_array.astype("float32") / 255.0
            img_array = np.expand_dims(img_array, axis=0)

            prediction = model.predict(img_array)
            predicted_class = np.argmax(prediction[0])

            return class_names[predicted_class]
        except Exception as e:
            print("Classification error:", e)
            return "Unknown"
    return "Unknown"


# ---------------- ROUTES ----------------
@app.route('/')
def home():
    return render_template('home.html')


@app.route('/index')
def index():
    return render_template('index.html')


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/suggestions/<category>')
def suggestions_page(category):

    suggestions = {
        "Battery": {
            "videos": ["Dwa9xhvDwuU", "D7td95ySam8"],
            "websites": [
                {"name": "Karo Sambhav", "url": "https://www.karosambhav.com/"},
                {"name": "CPCB Battery Waste", "url": "https://cpcb.nic.in/battery-waste/"}
            ]
        },
        "Biological": {
            "videos": ["zy70DAaeFBI", "EIR6_LoCcps"],
            "websites": [
                {"name": "Daily Dump", "url": "https://www.dailydump.org/"}
            ]
        },
        "Clothes": {
            "videos": ["6UyBNtBNawA", "9DSXXtsALoM"],
            "websites": [
                {"name": "Goonj", "url": "https://goonj.org/donate/"}
            ]
        },
        "Plastic": {
            "videos": ["V7TcEnSOR3s", "uDl-akjTNQ4"],
            "websites": [
                {"name": "UNDP Plastic Waste", "url": "https://www.in.undp.org/content/india/en/home/projects/plastic-waste-management.html"}
            ]
        },
        "Paper": {
            "videos": ["HmhPuIKw0HY", "OQtXkBKsoqo"],
            "websites": [
                {"name": "ITC WOW", "url": "https://www.itcportal.com/media-centre/press-reports/2007/wow.aspx"}
            ]
        },
        "Glass": {
            "videos": ["xj5Fgg-tuzo", "6jQ7y_qQYUA"],
            "websites": [
                {"name": "Toter India", "url": "https://www.toter.in/"}
            ]
        },
        "Shoes": {
            "videos": ["1fsiGm3NMu0", "ZimS9e-3irs"],
            "websites": [
                {"name": "Greensole", "url": "https://www.greensole.in/"}
            ]
        }
    }

    selected = suggestions.get(category, {"videos": [], "websites": []})
    return render_template("suggestions.html", category=category, suggestions=selected)


# ---------------- PREDICT ----------------
@app.route('/predict', methods=['POST'])
def predict():

    if 'file' not in request.files:
        return "No file uploaded"

    file = request.files['file']

    if file.filename == '':
        return "No file selected"

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    # Predict
    predicted_label = classify_image(filepath)

    # Excel data
    if HAS_PANDAS:
        try:
            data = pd.read_excel('waste_info.xlsx')
            row = data[data['CategoryBelongs'].str.lower() == predicted_label.lower()]

            if not row.empty:
                row = row.iloc[0]
                category = row['CategoryBelongs']
                recyclable = row['Recyclable']
                bin_type = row['Bin']
                facts = [row[f'Fact{i}'] for i in range(1, 8)]
            else:
                raise Exception("Not found")

        except Exception as e:
            print("Excel error:", e)
            category, recyclable, bin_type = predicted_label, "Yes", "General"
            facts = ["No data available"] * 7
    else:
        category, recyclable, bin_type = predicted_label, "Yes", "General"
        facts = ["No data"] * 7

    # Bin image
    bin_image = f"{bin_type.lower()}_bin.jpeg"

    # ---------------- TRANSLATION ----------------
    lang_code = request.form.get('lang', 'en')

    if HAS_TRANSLATOR:
        translator = GoogleTranslator(source='auto', target=lang_code)

        translated_category = translator.translate(category)
        translated_bin_type = translator.translate(bin_type)
        translated_recyclable = translator.translate(str(recyclable))
        translated_classification_result = translator.translate("Classification Result")
        translated_category_heading = translator.translate("Category")
        translated_recyclable_heading = translator.translate("Recyclable")
        translated_recommended_bin = translator.translate("Recommended Bin")
        translated_did_you_know = translator.translate("Did You Know?")
        translated_facts = [translator.translate(str(f)) for f in facts]
        translated_audio_text = translator.translate(
            f"This is a {category}. It goes into {bin_type} bin."
        )

    else:
        translated_category = category
        translated_bin_type = bin_type
        translated_recyclable = recyclable
        translated_classification_result = "Classification Result"
        translated_category_heading = "Category"
        translated_recyclable_heading = "Recyclable"
        translated_recommended_bin = "Recommended Bin"
        translated_did_you_know = "Did You Know?"
        translated_facts = facts
        translated_audio_text = f"This is a {category}. It goes into {bin_type} bin."

    # ---------------- TTS ----------------
    audio_file = None
    if HAS_GTTS:
        try:
            tts = gTTS(text=translated_audio_text, lang=lang_code)
            audio_path = os.path.join("static", "audio.mp3")
            tts.save(audio_path)
            audio_file = "audio.mp3"
        except Exception as e:
            print("TTS error:", e)

    return render_template(
        "result.html",
        prediction=translated_category,
        filename=filename,
        audio=audio_file,
        category=translated_category,
        bin_type=translated_bin_type,
        bin_image=bin_image,
        recyclable=translated_recyclable,
        facts=translated_facts,
        classification_result=translated_classification_result,
        category_heading=translated_category_heading,
        recyclable_heading=translated_recyclable_heading,
        recommended_bin_heading=translated_recommended_bin,
        did_you_know_heading=translated_did_you_know
    )


# ---------------- RUN ----------------
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)