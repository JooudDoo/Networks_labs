import threading
import time
from pathlib import Path

import logging
from flask import Flask, render_template, request,  jsonify, flash, redirect, Response

from MyParser import DNSParser

app = Flask(__name__)

handler = logging.FileHandler("test.log")
app.logger.addHandler(handler)
app.logger.setLevel(logging.DEBUG)

DNSPARSER = None
parserThreadStarted = False
parserThreadEnded = False

def runparser(url):
    global parserThreadEnded
    DNSPARSER = DNSParser(parsingTags=['name', 'price', 'availability'])
    app.logger.info(f'Started parsing url: {url}')
    DNSPARSER.parseDNSUrlCatalog(url)
    app.logger.info(f'parsed url: {url}')
    DNSPARSER.exportData('parsed_data.parse')
    app.logger.info('exported to file')
    parserThreadEnded = True
    del DNSPARSER

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dnsparser/parse', methods=['POST'])
def parse_link():
    global parserThreadStarted, parserThreadEnded
    app.logger.info(f"Fetch")
    url = request.form['link']

    if not url:
        return jsonify({'status': 'succes'})

    if not parserThreadStarted:
        parserThreadStarted = True
        app.logger.info(f"Created parsed thread {threading.active_count()}")
        parserThread = threading.Thread(target=runparser, args=[url])
        parserThread.start()
        return jsonify({'status': 'parsing'})
    elif parserThreadStarted and not parserThreadEnded:
        return jsonify({'status': 'parsing'})
    elif parserThreadStarted and parserThreadEnded:
        app.logger.info(f"Parser thread died")
        parserThreadStarted = False
        parserThreadEnded = False
        return jsonify({'status': 'succes'})

@app.route('/dnsparser/<index>/', methods=('GET', 'POST'))
def form(index):
    if index == '2':
        app.logger.info(Path("/home/sega/progs/flaskServer/parsed_data.parse.csv").is_file())
        if Path("/home/sega/progs/flaskServer/parsed_data.parse.csv").is_file():
            with open("/home/sega/progs/flaskServer/parsed_data.parse.csv", 'r', encoding='utf8') as f:
                csv = f.read()
            return Response(csv, mimetype="text/csv", headers={"Content-disposition":"attachment; filename=parsed_data.csv"})
    
    return render_template('form.html')

if __name__ == "__main__":
    app.run(host='0.0.0.0')