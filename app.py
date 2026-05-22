from flask import Flask, render_template, request # type: ignore
import os
import numpy as np
from werkzeug.utils import secure_filename

print("Starting Trashify application with Robustness Patch...")
app = Flask(__name__)

# --- FALLBACK SYSTEM FOR DEPENDENCIES ---

# 1. TensorFlow / Model Fallback
try:
    from tensorflow.keras.models import load_model
    from tensorflow.keras.preprocessing import image
    model = load_model('models/updated_wastemodel.keras')
    print("TensorFlow and Model loaded successfully.")
    HAS_MODEL = True
except Exception as e:
    print(f"TensorFlow/Model Fallback: {e}")
    HAS_MODEL = False
    model = None

# 2. GoogleTrans Fallback
try:
    from googletrans import Translator
    HAS_TRANSLATOR = True
except Exception as e:
    print(f"GoogleTrans Fallback: {e}")
    HAS_TRANSLATOR = False
    class MockTranslator:
        class Result:
            def __init__(self, text): self.text = text
        def translate(self, text, dest='en'): return self.Result(text)
    Translator = MockTranslator

# 3. gTTS Fallback
try:
    from gtts import gTTS
    HAS_GTTS = True
except Exception as e:
    print(f"gTTS Fallback: {e}")
    HAS_GTTS = False
    def gTTS(text, lang='en'):
        class MockTTS:
            def save(self, path): print(f"Mock TTS save: {path}")
        return MockTTS()

# 4. Pandas / Excel Fallback
try:
    import pandas as pd
    HAS_PANDAS = True
except Exception as e:
    print(f"Pandas Fallback: {e}")
    HAS_PANDAS = False

# --- CONFIGURATION ---

# Class labels
class_names = ['Battery','Biological','Clothes','Glass','Paper','Plastic','Shoes']

# Upload folder inside 'static'
UPLOAD_FOLDER = 'static/uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- CORE FUNCTIONS ---

def classify_image(img_path):
    if HAS_MODEL and model:
        try:
            from tensorflow.keras.preprocessing import image

            img = image.load_img(img_path, target_size=(224, 224))
            img_array = image.img_to_array(img)

            img_array = img_array.astype("float32") / 255.0
            img_array = np.expand_dims(img_array, axis=0)

            prediction = model.predict(img_array)

            print("Prediction Probabilities:", prediction)

            predicted_class = np.argmax(prediction[0])

            print("Predicted Index:", predicted_class)
            print("Predicted Label:", class_names[predicted_class])

            confidence = np.max(prediction[0]) * 100
            print(f"Confidence: {confidence:.2f}%")

            return class_names[predicted_class]

        except Exception as e:
            print(f"Classification error: {e}")
            return "Unknown"

    return "Unknown"

# --- ROUTES ---

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
            {"name": "Karo Sambhav - E-waste recycling", "url": "https://www.karosambhav.com/"},
            {"name": "CPCB Guidelines on Battery Waste", "url": "https://cpcb.nic.in/battery-waste/"}
        ]
     },
     "Biological": {
        "videos": ["zy70DAaeFBI", "EIR6_LoCcps"],
        "websites": [
            {"name": "Daily Dump (composting solutions)", "url": "https://www.dailydump.org/"},
            {"name": "MyGate: Guide to Composting", "url": "https://mygate.com/blog/composting-wet-waste/"}
        ]
     },
     "Clothes": {
        "videos": ["6UyBNtBNawA", "9DSXXtsALoM"],
        "websites": [
            {"name": "Goonj (Donate clothes)", "url": "https://goonj.org/donate/"},
            {"name": "Share At Door Step", "url": "https://www.shareatdoorstep.com/"}
        ]
     },
     "Plastic": {
        "videos": ["V7TcEnSOR3s", "uDl-akjTNQ4"],
        "websites": [
            {"name": "UNDP India - Plastic Waste Mgmt", "url": "https://www.in.undp.org/content/india/en/home/projects/plastic-waste-management.html"},
            {"name": "Recykal", "url": "https://recykal.com/"}
        ]
     },
     "Paper": {
        "videos": ["HmhPuIKw0HY", "OQtXkBKsoqo"],
        "websites": [
            {"name": "ITC WOW - Recycle Paper Initiative", "url": "https://www.itcportal.com/media-centre/press-reports/2007/wow.aspx"},
            {"name": "Greenobin", "url": "https://www.greenobin.com/"}
        ]
     },
     "Glass": {
        "videos": ["xj5Fgg-tuzo", "6jQ7y_qQYUA"],
        "websites": [
            {"name": "Goli Soda (Sustainable Store)", "url": "https://golisodastore.com/"},
            {"name": "Toter (Waste Management India)", "url": "https://www.toter.in/"}
        ]
     },
     "Shoes": {
        "videos": ["1fsiGm3NMu0", "ZimS9e-3irs"],
        "websites": [
            {"name": "Greensole (Shoe Donation)", "url": "https://www.greensole.in/"},
            {"name": "Save Your Sole India", "url": "https://saveyoursole.co.in/"}
        ]
     }
    }

    selected = suggestions.get(category, {'videos': [], 'links': []})
    return render_template('suggestions.html', category=category, suggestions=selected)

@app.route('/predict', methods=['POST'])
def predict():
    if 'file' not in request.files:
        return 'No file uploaded.'

    file = request.files['file']
    if file.filename == '':
        return 'No selected file.'

    # Save the uploaded image
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    # Classify the image
    predicted_label = classify_image(filepath)

    # Waste info fallback
    if HAS_PANDAS:
        try:
            waste_data = pd.read_excel('waste_info.xlsx')
            row = waste_data[waste_data['CategoryBelongs'].str.lower() == predicted_label.lower()]
            if not row.empty:
                row = row.iloc[0]
                category = row['CategoryBelongs']
                recyclable = row['Recyclable']
                bin_type = row['Bin']
                facts = [row[f'Fact{i}'] for i in range(1, 8)]
            else:
                raise Exception("Category not in Excel")
        except Exception as e:
            print(f"Excel error: {e}")
            category, recyclable, bin_type, facts = predicted_label, "Yes", "General", ["Fact " + str(i) for i in range(1, 8)]
    else:
        category, recyclable, bin_type, facts = predicted_label, "Yes", "General", ["Fact " + str(i) for i in range(1, 8)]

    # Bin image logic
    if category == "Glass": bin_image = "blue_bin.jpeg"
    elif category == "Shoes": bin_image = "shoe_recycling_bin.jpeg"
    elif category == "Battery": bin_image = "hazardous_waste_bin.jpeg"
    elif category == "Clothes": bin_image = "textile_recycling_bin.jpeg"
    else: bin_image = f"{bin_type.lower()}_bin.jpeg"

    # Translation
    lang_code = request.form.get('lang', 'en')
    translator = Translator()
    translated_category = translator.translate(category, dest=lang_code).text
    translated_bin_type = translator.translate(bin_type, dest=lang_code).text
    translated_recyclable = translator.translate(str(recyclable), dest=lang_code).text
    translated_classification_result = translator.translate("Classification Result", dest=lang_code).text
    translated_category_heading = translator.translate("Category", dest=lang_code).text
    translated_recyclable_heading = translator.translate("Recyclable", dest=lang_code).text
    translated_recommended_bin = translator.translate("Recommended Bin", dest=lang_code).text
    translated_did_you_know = translator.translate("Did You Know?", dest=lang_code).text
    translated_facts = [translator.translate(str(fact), dest=lang_code).text for fact in facts]

    # TTS
    audio_text = f"This is a {category}. This item is {recyclable if isinstance(recyclable, str) else 'recyclable'}. It goes into the {bin_type} bin."
    translated_audio_text = translator.translate(audio_text, dest=lang_code).text
    
    supported_tts_langs = ['en', 'hi', 'te', 'ta', 'kn', 'ml', 'gu', 'bn', 'mr', 'ur']
    if HAS_GTTS and lang_code in supported_tts_langs:
       try:
           tts = gTTS(text=translated_audio_text, lang=lang_code)
           audio_path = os.path.join('static', 'audio.mp3')
           tts.save(audio_path)
           audio_file = 'audio.mp3'
       except: audio_file = None
    else: audio_file = None

    return render_template('result.html',
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
                       did_you_know_heading=translated_did_you_know)

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=8080)
