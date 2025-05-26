import os
import re
from flask import Flask, request, render_template, send_from_directory
from docx import Document
from bs4 import BeautifulSoup
import difflib
from werkzeug.utils import secure_filename

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'results'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Tokenizer
def tokenize(text):
    return re.findall(r'\w+|[^\w\s]', text, re.UNICODE)

# Read DOCX
def read_docx(file_path):
    doc = Document(file_path)
    paragraphs = [tokenize(para.text) for para in doc.paragraphs if para.text.strip()]
    return [token for para in paragraphs for token in para + ['\n']]

# Extract visible HTML
def extract_visible_text(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    paragraphs = soup.get_text(separator='\n', strip=True).split('\n')
    return [token for para in paragraphs for token in tokenize(para) + ['\n']]

# Generate comparison HTML
def generate_side_by_side_html(docx_tokens, web_tokens):
    diff = list(difflib.ndiff(docx_tokens, web_tokens))
    docx_html = ''
    web_html = ''

    for word in diff:
        if word == '\n':
            docx_html += '<br>\n'
            web_html += '<br>\n'
        elif word.startswith('  '):
            docx_html += f'<span style="color:green;">{word[2:]} </span>'
            web_html += f'<span style="color:green;">{word[2:]} </span>'
        elif word.startswith('- '):
            docx_html += f'<span style="background-color: #ff6666;">{word[2:]} </span>'
        elif word.startswith('+ '):
            web_html += f'<span style="color:blue;">{word[2:]} </span>'

    return docx_html, web_html

@app.route('/', methods=['GET', 'POST'])
def upload_files():
    if request.method == 'POST':
        docx_files = request.files.getlist('docx_file')
        html_files = request.files.getlist('html_file')

        if docx_files and html_files and len(docx_files) == len(html_files):
            result_links = []

            for docx_file, html_file in zip(docx_files, html_files):
                docx_filename = secure_filename(docx_file.filename)
                html_filename = secure_filename(html_file.filename)
                docx_path = os.path.join(UPLOAD_FOLDER, docx_filename)
                html_path = os.path.join(UPLOAD_FOLDER, html_filename)
                docx_file.save(docx_path)
                html_file.save(html_path)

                docx_tokens = read_docx(docx_path)
                with open(html_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                web_tokens = extract_visible_text(html_content)

                docx_html, web_html = generate_side_by_side_html(docx_tokens, web_tokens)
                result_filename = f'{os.path.splitext(docx_filename)[0]}_comparison.html'
                result_path = os.path.join(OUTPUT_FOLDER, result_filename)
                with open(result_path, 'w', encoding='utf-8') as f:
                    f.write(render_template('comparison_template.html', docx_html=docx_html, web_html=web_html))

                result_links.append(result_filename)

            return render_template('result_list.html', files=result_links)

    return render_template('upload_form.html')

# Add this route here, below the upload_files route
@app.route('/results/<path:filename>')
def download_result(filename):
    return send_from_directory(OUTPUT_FOLDER, filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)