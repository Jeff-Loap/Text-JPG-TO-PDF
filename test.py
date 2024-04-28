from flask import Flask, request, render_template
from werkzeug.utils import secure_filename
from pytesseract import image_to_string
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from textblob import TextBlob
import io
import pytesseract

# 设置tesseract-ocr的路径
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# 创建Flask应用实例
app = Flask(__name__)


# 第一次处理：将文本添加到PDF中
def add_text_to_pdf(p, text, x, y, space, max_width):
    formatted_line = ""

    # 按行分割文本
    for line in text.split('\n'):
        if formatted_line:
            if line and line[0] != ' ':
                formatted_line += line.strip()
                continue
            else:
                formatted_line += '\n'

        # 遍历行中的每个字符
        for char in line:
            if char != ' ':
                formatted_line += char
            else:
                formatted_line += " "

            # 如果当前行的宽度超过最大宽度，则绘制当前行并重新开始新行
            if p.stringWidth(formatted_line) > max_width:
                p.drawString(x, y, formatted_line.strip())
                y -= space
                formatted_line = ""

        # 如果formatted_line非空，则绘制它
        if formatted_line.strip():
            p.drawString(x, y, formatted_line.strip())
            y -= space
            formatted_line = ""

        # 如果y坐标小于行间距，则开始新的一页
        if y < space:
            p.showPage()
            y = letter[1] - 100

    return y


# 第二次处理：调整单词断行
def adjust_word_breaks(text):
    adjusted_text = ""
    for line in text.split('\n'):
        if adjusted_text:
            if line and line[0] != ' ':
                words = line.strip().split()
                current_word = words[0]
                for word in words[1:]:
                    # 如果加上当前单词后长度超过限制，则新起一行
                    if len(adjusted_text.split()[-1] + ' ' + current_word + ' ' + word) > 70:
                        adjusted_text += '\n' + current_word
                        current_word = word
                    else:
                        adjusted_text += ' ' + current_word
                        current_word = word
                # 对当前单词进行同样的检查
                if len(adjusted_text.split()[-1] + ' ' + current_word) > 70:
                    adjusted_text += '\n' + current_word
                else:
                    adjusted_text += ' ' + current_word
                continue
            else:
                adjusted_text += '\n'

        adjusted_text += line.strip() + ' '

    return adjusted_text.strip()


# 第三次处理：修复OCR行断行
def fix_ocr_line_breaks(text, max_line_length=80):
    """
    修复OCR行断行，通过合并分割的单词并保持段落结构。

    :param text: 可能存在不正确行断行的输入文本。
    :param max_line_length: 文本行在换行前的最大长度。
    :return: 具有固定行断行的新字符串。
    """
    paragraphs = text.split('\n')  # 将文本分割成段落
    fixed_text = ""

    for paragraph in paragraphs:
        words = paragraph.split()  # 将段落分割成单词
        current_line = ""
        for word in words:
            # 如果当前行最后一个字符是空格，并且下一个单词以空格开始，说明单词被错误分割
            if current_line.endswith(' ') and word.startswith(' '):
                # 删除当前行的空格并连接单词
                current_line = current_line.rstrip() + word.lstrip()
            elif len(current_line) + len(word) <= max_line_length or not current_line:
                # 如果单词可以放入当前行，则将其添加到当前行
                current_line += (" " + word) if current_line else word
            else:
                # 如果当前行已满，将其添加到固定文本并开始新行
                fixed_text += current_line + '\n'
                current_line = word  # 新行以当前单词开始

        # 如果当前行非空，则将其添加到固定文本
        if current_line:
            fixed_text += current_line + '\n'

        # 在每个段落之后添加一个额外的换行符
        fixed_text += '\n'

    # 移除最后一个换行符
    return fixed_text.strip()



# 第四次处理：添加拼写检查函数
# 拼写检查函数
def correct_spelling_errors(text):
    corrected_text = TextBlob(text).correct()
    return str(corrected_text)

# 第五次处理：实现段落分行功能
def add_paragraph_breaks(text, max_line_length=80):
    formatted_text = ""
    for line in text.split('\n'):
        formatted_text += line.strip() + '\n'

    return formatted_text.strip()


# Flask 路由处理函数
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        image_file = request.files['image']
        filename = secure_filename(image_file.filename)
        image_file.save(filename)

        # 使用Tesseract执行OCR
        text = image_to_string(filename, lang='eng', config='--oem 3 --psm 6')

        print("原始OCR文本:")
        print(text)  # 打印原始OCR文本

        # 调整单词断行
        adjusted_text = adjust_word_breaks(text)

        print("\n调整单词断行后的文本:")
        print(adjusted_text)  # 打印调整单词断行后的文本

        # 修复OCR行断行
        fixed_text = fix_ocr_line_breaks(adjusted_text)

        print("\n修复OCR行断行后的文本:")
        print(fixed_text)  # 打印修复OCR行断行后的文本

        # 使用TextBlob修正拼写错误
        corrected_text = correct_spelling_errors(fixed_text)

        print("\n修正拼写错误后的文本:")
        print(corrected_text)  # 打印修正拼写错误的文本

        pdf_buffer = io.BytesIO()
        p = canvas.Canvas(pdf_buffer, pagesize=letter)

        x = 100  # 开始的x坐标
        y = letter[1] - 100  # 开始的y坐标
        space = 15  # 行间距

        # 将修正拼写错误的文本添加到PDF中
        add_text_to_pdf(p, corrected_text, x, y, space, letter[0] * 0.8)

        p.save()

        # 发送PDF文件
        response = app.response_class(pdf_buffer.getvalue(), mimetype='application/pdf')
        return response

    return render_template('index.html')


# 程序入口
if __name__ == '__main__':
    app.run(debug=True)