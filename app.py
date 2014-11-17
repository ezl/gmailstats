import pickle
import datetime
import urllib
import imaplib

import requests
from jinja2 import Template, Environment, FileSystemLoader
from jinja2.ext import Extension
from calculate_email_stats import calculate_email_stats

from bottle import (
    route,
    run,
    template,
    redirect,
    get,
    post,
    request,
    static_file,
    Bottle
    )


from settings import (
    OAUTH_URL,
    OAUTH_URL_TOKEN,
    CLIENT_ID,
    CLIENT_SECRET,
    REDIRECT_URI,
    ACCESS_TOKEN,
    REFRESH_TOKEN,
    )

app = Bottle()

USERNAME = None
env = Environment(extensions=['jinja2.ext.with_'], loader=FileSystemLoader('templates'))
env.filters['average'] = lambda x: sum(x) / float(len(x))

def refresh_token():
    r = requests.post(OAUTH_URL_TOKEN, data={
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'refresh_token': REFRESH_TOKEN,
        'grant_type': 'refresh_token',
    })
    try:
        new_access_token  = r.json()['access_token']
    except KeyError:
        raise Exception
    return new_access_token

@app.route('/static/<filename:path>')
def server_static(filename):
    return static_file(filename, root='static')

@app.get('/')
def homepage():
    template = env.get_template("homepage.html")
    context = {}
    return template.render(context)

@app.post('/')
def auth():
    global USERNAME
    global DAYS
    USERNAME = request.forms.get("email_address")
    DAYS = int(request.forms.get("days")) or 7
    user_url = "{}?{}".format(OAUTH_URL, urllib.urlencode({
                                  'client_id': CLIENT_ID,
                                  'scope': "https://mail.google.com/",
                                  'login_hint': USERNAME,
                                  'redirect_uri': REDIRECT_URI,
                                  'access_type': 'offline',
                                  'response_type': 'code',
                                  'approval_prompt': 'force',
                              }))
    redirect(user_url)

@app.route('/gmail_oauth_cb')
def oauth_cb():
    code = request.params['code']
    r = requests.post(OAUTH_URL_TOKEN, data={
        'code': code,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'redirect_uri': REDIRECT_URI,
        'grant_type': 'authorization_code',
    })
    global ACCESS_TOKEN
    global REFRESH_TOKEN
    ACCESS_TOKEN  = r.json()['access_token']
    if 'refresh_token' in r.json():
        REFRESH_TOKEN = r.json()['refresh_token']
    return redirect('/login_success')

@app.route('/log_in_again')
def log_in_again():
    template = env.get_template("log_in_again.html")
    context = {}
    return template.render(context)

@app.route('/login_success')
def login_success():
    template = env.get_template("login_success.html")
    context = {}
    return template.render(context)


@app.route('/nologin')
def nologin():
    return "Unable to log in."

@app.route('/stats')
def stats():
    template = env.get_template("stats.html")

    FILENAME = "obj.pickle"
    LOAD_FROM_PICKLE = False
    SAVE = False

    if LOAD_FROM_PICKLE is True:
        with open(FILENAME, "r") as f:
            context = pickle.load(f)
    else:
        # First prove we can authenticate.
        try:
            auth_string = 'user=%s\1auth=Bearer %s\1\1' % (USERNAME, ACCESS_TOKEN)
            imap_conn = imaplib.IMAP4_SSL('imap.gmail.com')
            imap_conn.debug = 4
            status, response = imap_conn.authenticate('XOAUTH2', lambda x: auth_string)
        except Exception, e:
            try:
                NEW_ACCESS_TOKEN = refresh_token()
                g.authenticate(USERNAME, NEW_ACCESS_TOKEN)
            except Exception, e:
                redirect("/log_in_again")

        # OK We can log in.  Now lets get to the fun stuff.

        ALIASES = [
            "eric@rentapplication",
            "eric@rocketlease",
            "ericzliu@gmail",
            ]

        IGNORE_EMAILS = [
            "followup",
            "meetup",
            "noreply",
            "no-reply",
            ]

        IGNORE_SUBJECT_KEYWORDS = [
            "receipts",
            "stripe",
            "payment",
            ]

        IGNORE_BODY_KEYWORDS = [
            "unsubscribe",
            ]

        print datetime.datetime.now()
        context = calculate_email_stats(
            USERNAME,
            ACCESS_TOKEN,
            DAYS,
            ALIASES=ALIASES,
            IGNORE_EMAILS=IGNORE_EMAILS,
            IGNORE_SUBJECT_KEYWORDS=IGNORE_SUBJECT_KEYWORDS,
            IGNORE_BODY_KEYWORDS=IGNORE_BODY_KEYWORDS,
            MIN_THREAD_LENGTH=2,
            )

        if SAVE is True:
            with open(FILENAME, "w") as f:
                pickle.dump(context, f)

    print datetime.datetime.now()
    # context.update(locals())

    return template.render(context)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
