import streamlit as st
import json
import os
from pdfminer.high_level import extract_text as pdf_extract_text
from groq import Groq
import pdf2image
import requests
from dotenv import load_dotenv
import os

load_dotenv()

groq_client = Groq(api_key = os.getenv("GROQ_API_KEY"))
OCR_SPACE_API_KEY = os.getenv("OCR_SPACE_API_KEY")

st.set_page_config(
    page_title="Prescription Parser",
    page_icon="💊",
    layout="wide"
)

st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border-radius: 5px;
        padding: 0.5em 1em;
    }
    .stFileUploader>div>div>div>div {
        color: #4CAF50;
    }
    .med-card {
        border-left: 5px solid #4CAF50;
        padding: 1em;
        margin: 1em 0;
        background-color: black;
        border-radius: 5px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)

def ocr_space_file(filename):
    """Free cloud OCR using OCR.Space API"""
    payload = {
        'apikey': OCR_SPACE_API_KEY,
        'language': 'eng',
        'isOverlayRequired': False,
        'OCREngine': 2  
    }
    
    with open(filename, 'rb') as f:
        response = requests.post(
            'https://api.ocr.space/parse/image',
            files={filename: f},
            data=payload,
        )
    
    if response.status_code == 200:
        result = response.json()
        if result['IsErroredOnProcessing']:
            st.error(f"OCR Error: {result['ErrorMessage']}")
            return None
        return result['ParsedResults'][0]['ParsedText']
    return None

def extract_text_from_file(file_path):
    """Handle both digital PDFs and scanned images"""
    try:
        if file_path.lower().endswith('.pdf'):
            text = pdf_extract_text(file_path)
            if text and len(text.strip()) > 100:
                return text
            
            try:
                images = pdf2image.convert_from_path(file_path, dpi=300)
                text = ""
                for img in images:
                    img_path = "temp_img.png"
                    img.save(img_path, 'PNG')
                    ocr_result = ocr_space_file(img_path)
                    if ocr_result:
                        text += ocr_result + "\n"
                    os.remove(img_path)
                return text.strip() if text else None
            except Exception as e:
                st.warning(f"PDF to image conversion failed: {str(e)}")
                return None
        
        elif file_path.lower().endswith(('.jpg', '.jpeg', '.png')):
            return ocr_space_file(file_path)
        
        else:
            raise ValueError("Unsupported file format. Please provide PDF or image (JPG/PNG)")
            
    except Exception as e:
        st.error(f"Extraction error: {str(e)}")
        return None

def get_medicine_details(medicine_name):
    """Fetch detailed pharmacological information about a medicine"""
    try:
        response = groq_client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[
                {
                    "role": "system",
                    "content": """Provide detailed pharmacological information in JSON format about the given medicine including:
                    - active_ingredients (array)
                    - common_alternatives (array)
                    - mechanism_of_action (string)
                    Return ONLY valid JSON."""
                },
                {
                    "role": "user", 
                    "content": f"Medicine: {medicine_name}"
                }
            ],
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        st.error(f"Medicine details error: {str(e)}")
        return None

def parse_with_groq(text):
    """Parser using Groq's free Llama 3 70B model"""
    try:
        with st.spinner('Analyzing prescription...'):
            response = groq_client.chat.completions.create(
                model="llama3-70b-8192",  
                messages=[
                    {
                        "role": "system",
                        "content": """Extract prescription data as JSON with:
                        - doctor (string)
                        - patient (string)
                        - date (string)
                        - diagnosis (array)
                        - medicines (array of {name, strength, dosage, frequency, duration})
                        Return ONLY valid JSON."""
                    },
                    {
                        "role": "user", 
                        "content": f"Prescription text:\n{text}"
                    }
                ],
                response_format={"type": "json_object"},
            )
            
            prescription_data = json.loads(response.choices[0].message.content)
            
            if 'medicines' in prescription_data:
                for medicine in prescription_data['medicines']:
                    with st.spinner(f'Fetching details for {medicine["name"]}...'):
                        details = get_medicine_details(medicine['name'])
                        if details:
                            medicine.update(details)
            return prescription_data
    except Exception as e:
        st.error(f"Groq Error: {str(e)}")
        return None

def display_results(result):
    """Display the parsed results in a user-friendly format"""
    st.header("Prescription Analysis Results")
    
    # Summary Section
    with st.expander("📄 Prescription Summary", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"**👨‍⚕️ Doctor:** {result.get('doctor', 'Not specified')}")
        with col2:
            st.markdown(f"**👤 Patient:** {result.get('patient', 'Not specified')}")
        with col3:
            st.markdown(f"**📅 Date:** {result.get('date', 'Not specified')}")
        
        if 'diagnosis' in result and result['diagnosis']:
            st.markdown("**🩺 Diagnosis:**")
            for diag in result['diagnosis']:
                st.markdown(f"- {diag}")
    
    # Medications Section
    st.subheader("💊 Medications")
    if 'medicines' in result and result['medicines']:
        for med in result['medicines']:
            with st.container():
                st.markdown(f"""
                <div class="med-card">
                    <h3>{med.get('name', 'Unknown')} {med.get('strength', '')}</h3>
                    <p><strong>Dosage:</strong> {med.get('dosage', 'Not specified')}</p>
                    <p><strong>Frequency:</strong> {med.get('frequency', 'Not specified')}</p>
                    <p><strong>Duration:</strong> {med.get('duration', 'Not specified')}</p>
                """, unsafe_allow_html=True)
                
                if 'mechanism_of_action' in med:
                    with st.expander("🧪 Pharmacological Details"):
                        st.subheader("**Mechanism of Action:**") 
                        st.markdown(med['mechanism_of_action'])
                        
                        if 'active_ingredients' in med and med['active_ingredients']:
                            st.subheader("**Active Ingredients:**")
                            for ing in med['active_ingredients']:
                                st.markdown(f"- {ing}")
                        
                        if 'common_alternatives' in med and med['common_alternatives']:
                            st.subheader("**Common Alternatives:**")
                            for alt in med['common_alternatives']:
                                st.markdown(f"- {alt}")
                
                st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.warning("No medications found in the prescription")

def main():
    st.title("💊 Prescription Parser")
    st.markdown("Upload a prescription (PDF or image) to extract structured information")
    
    uploaded_file = st.file_uploader(
        "Choose a prescription file", 
        type=['pdf', 'jpg', 'jpeg', 'png'],
        accept_multiple_files=False
    )
    
    if uploaded_file is not None:
        file_path = f"temp_{uploaded_file.name}"
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # st.subheader("File Preview")
        # if uploaded_file.type == "application/pdf":
        #     try:
        #         images = pdf2image.convert_from_path(file_path, first_page=1, last_page=1)
        #         st.image(images[0], caption="First page of PDF", use_container_width=True)
        #     except:
        #         st.warning("Could not display PDF preview")
        # else:
        #     st.image(Image.open(file_path), caption="Uploaded Image", use_container_width=True)
        
        if st.button("Analyze Prescription", type="primary"):
            with st.spinner('Extracting text from document...'):
                text = extract_text_from_file(file_path)
            
            if text:
                st.subheader("Extracted Text")
                with st.expander("View extracted text"):
                    st.text(text)
                
                result = parse_with_groq(text)
                if result:
                    display_results(result)
                    
                    json_data = json.dumps(result, indent=2)
                    st.download_button(
                        label="Download Results as JSON",
                        data=json_data,
                        file_name="prescription_analysis.json",
                        mime="application/json"
                    )
            else:
                st.error("Failed to extract text from the document")
        
        os.remove(file_path)

if __name__ == "__main__":
    main()
