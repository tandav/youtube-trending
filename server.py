
from flask import Flask, request, send_from_directory

# set the project root directory as the static folder, you can set others.
app = Flask(__name__, static_folder='', static_url_path='')

@app.route('/')
def get_file():
    return send_from_directory('', filename='image.pdf', as_attachment=False)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
