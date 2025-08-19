

## Tech Stack

- **Frontend**: Streamlit
- **OCR**: OCR.space API + pdf2image
- **AI Processing**: Groq (Llama 3 70B)
- **PDF Processing**: pdfminer.six

## Installation

1. **Clone the repository**:
   ```bash
   git clone 

2. **Set up environment:

    ```bash
    python -m venv venv
    source venv/bin/activate  # Linux/Mac
    venv\Scripts\activate    # Windows

3. **Install dependencies:

    ```bash
    pip install -r requirements.txt

4. **Run the project:

   cd prescription_parser
   then run this command in terminal "streamlit run prescription_parser_ui.py"


5. **In the browser:

    Upload a prescription (PDF or image)
    Click "Analyze Prescription"
    View extracted information
    Download results as JSON

