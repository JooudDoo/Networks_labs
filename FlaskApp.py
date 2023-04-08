import threading
from pathlib import Path

import logging
from flask import Flask, render_template, request,  url_for, flash, redirect, Response

from MyParser import DNSParser

app = Flask(__name__)


handler = logging.FileHandler("test.log")
app.logger.addHandler(handler)
app.logger.setLevel(logging.DEBUG)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dnsparser/<index>/', methods=('GET', 'POST'))
def form(index):
    app.logger.info(index)
    if index == '1':
        if request.method == 'POST':
            url = request.form['url']
            app.logger.info(url)

            if url:

                def runparser():
                    parser = DNSParser(parsingTags=['name', 'price', 'availability'])
                    app.logger.info('Created instance of parser')
                    parser.parseDNSUrlCatalog(url, pages=1)
                    app.logger.info(f'parsed url: {url}')
                    parser.exportData('parsed_data.parse')
                    app.logger.info('exported to file')

                parserThread = threading.Thread(target=runparser, daemon=True)

                parserThread.start()

    elif index == '2':
        app.logger.info(Path("/home/sega/progs/flaskServer/parsed_data.parse.csv").is_file())
        if Path("/home/sega/progs/flaskServer/parsed_data.parse.csv").is_file():
            with open("/home/sega/progs/flaskServer/parsed_data.parse.csv", 'r', encoding='utf8') as f:
                csv = f.read()
            return Response(csv, mimetype="text/csv", headers={"Content-disposition":"attachment; filename=parsed_data.csv"})


    return render_template('form.html')

if __name__ == "__main__":
    app.run(host='0.0.0.0')