import datetime
import os
from email.utils import parseaddr

import requests
from gmail import Gmail

DEBUG = True

OAUTH_URL = 'https://accounts.google.com/o/oauth2/auth'
OAUTH_URL_TOKEN = 'https://accounts.google.com/o/oauth2/token'
CLIENT_ID = '626558672627-v4rg26hb07gpo4od97b3o1s078avfdk0.apps.googleusercontent.com'
CLIENT_SECRET = 'wzT01GwvmqMGxR7sDMw-Sxrh'

ALIASES = [
    "rob@rentapplication",
    ]
USERNAME = "rob@rentapplication.net"
ACCESS_TOKEN = 'ya29.pADR7aHI1-VN1q_7AUj0h9iZqbBDblVWChnRa2lugO3WRPIZg5jWqt9p6ijFkOZ2KLBCcjD_FDFYjQ'
REFRESH_TOKEN = '1/KVqj63s7TTMnglL4-LLu2gs4uolkKZaBF_JlzohGiyYMEudVrK5jSpoR30zcRFq6'


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

DAYS = 30
MIN_THREAD_LENGTH = 2

def refresh_token():
    write("Original token didn't work, refreshing token.")
    r = requests.post(OAUTH_URL_TOKEN, data={
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'refresh_token': REFRESH_TOKEN,
        'grant_type': 'refresh_token',
    })
    new_access_token  = r.json()['access_token']
    return new_access_token

def email_in_aliases(email, aliases):
    if not email:
        return False
    return any(alias.lower() in email.lower() for alias in aliases)

def write(string):
    print(string)

class Conversation(object):
    """
    Just a convenience object to make sense of the gmail threads.

    Takes a list of gmail Messages.
    """

    def __init__(self, thread, **kwargs):
        self.thread = thread
        self.last_email = self.thread[0]
        self.thread_id = self.last_email.thread_id
        self.length = len(self.thread)
        self.subject = self.last_email.subject

    def get_gmail_url(self):
        gmail_hex_conversation_id = hex(int(self.thread_id)).split("x")[1]
        return "https://mail.google.com/mail/#all/%s" % gmail_hex_conversation_id

    def get_last_response_time(self):
        if self.thread.length < 2:
            raise Exception
        return (self.self.thread[0].sent_at - self.thread[1].sent_at)

    def get_response_times(self, thread=None):
        """
        Returns a list of tuples containing the (responder, response_time_in_seconds)
        """
        thread = thread or self.thread
        if len(thread) < 2:
            return [dict(fr=thread[0].to, response_time=None), ]
        else:
            return self.get_response_times(thread[:-1]) + \
                   [dict(fr=thread[-2].fr,
                         response_time=(thread[-2].sent_at - thread[-1].sent_at).seconds), ]



    def __repr__(self):
        return "[%s msgs] %s" % (self.length, self.subject)

# def main():
if True:
    # Log in to Gmail
    g = Gmail()
    try:
        g.authenticate(USERNAME, ACCESS_TOKEN)
    except Exception, e:
        NEW_ACCESS_TOKEN = refresh_token()
        try:
            g.authenticate(USERNAME, NEW_ACCESS_TOKEN)
        except Exception, e:
            raise Exception, "Unable to log in."

    write( "Login success!")

    # Pull all emails
    now = datetime.datetime.now()
    after = now - datetime.timedelta(days=DAYS)
    emails = g.all_mail().mail(
                prefetch=True,
                after = after,
             )
    total_email_count = len(emails)
    write("Retrieved %s emails." % total_email_count)

    # Clean emails
    could_not_fetch = [email for email in emails if not email.body]
    emails = [email for email in emails if email.body]

    no_thread_id = [email for email in emails if not email.thread_id]
    print len(no_thread_id)
    print len(could_not_fetch)
    emails = [email for email in emails if email.thread_id]

    ignored_for_email = [email for email in emails if \
                             (email_in_aliases(email.fr, IGNORE_EMAILS) or \
                              email_in_aliases(email.to, IGNORE_EMAILS))]
    emails            = [email for email in emails if \
                         not (email_in_aliases(email.fr, IGNORE_EMAILS) or \
                              email_in_aliases(email.to, IGNORE_EMAILS))]

    ignored_for_subject = [email for email in emails if \
                           email_in_aliases(
                               email.subject,
                               IGNORE_SUBJECT_KEYWORDS)]
    emails              = [email for email in emails if \
                           not email_in_aliases(
                               email.subject,
                               IGNORE_SUBJECT_KEYWORDS)]

    ignored_for_body    = [email for email in emails if \
                           email_in_aliases(
                               email.body,
                               IGNORE_BODY_KEYWORDS)]
    emails              = [email for email in emails if \
                           not email_in_aliases(
                               email.body,
                               IGNORE_BODY_KEYWORDS)]

    write("Finished grabbing emails")

    # Group emails by thread
    threads = {}

    for email in emails:
        if not email.thread_id in threads.keys():
            threads[email.thread_id] = []
        threads[email.thread_id].append(email)

    write("Removed bad emails")

    # Sort and pull off the last responder
    last_responder_was_me = []
    last_responder_was_counterparty = []
    selfies = []

    for key in threads.keys():
        thread = threads[key]
        #if len(thread) > 5:
        #    import ipdb;
        #    ipdb.set_trace()
        thread.sort(cmp=lambda x,y:cmp(x.sent_at, y.sent_at), reverse=True)
        conversation = Conversation(thread)
        last_email = conversation.last_email


        # import ipdb
        # if "rentapp" in last_email.fr and "rentapp" in last_email.to:
        #     ipdb.set_trace()
        # I wrote it to someone other than me
        if (email_in_aliases(last_email.fr, ALIASES) and \
            not email_in_aliases(last_email.to, ALIASES)):
            last_responder_was_me.append(conversation)
        # I wrote it to myself
        elif (email_in_aliases(last_email.fr, ALIASES) and \
              email_in_aliases(last_email.to, ALIASES)):
            selfies.append(conversation)
        # Someone else wrote it
        else:
            last_responder_was_counterparty.append(conversation)

    inbound_emails = [email for email in emails \
                          if (email_in_aliases(email.to, ALIASES) and \
                          not email_in_aliases(email.fr, ALIASES))]
    outbound_emails = [email for email in emails \
                          if (email_in_aliases(email.fr, ALIASES) and \
                          not email_in_aliases(email.to, ALIASES))]
    selfie_emails = [email for email in emails \
                          if (email_in_aliases(email.fr, ALIASES) and \
                          email_in_aliases(email.to, ALIASES))]
    other_emails = [email for email in emails \
                          if (not email_in_aliases(email.fr, ALIASES) and \
                          not email_in_aliases(email.to, ALIASES))]
    write("Sorted emails")
    write("selfies, last_responder_was_me, last_responder_was_counterparty")

    write("* " * 25)

    write("# Inbox Total: %s" % g.inbox().count())
    write("# Inbox Unread: %s" % g.inbox().count(unread=True))
    write("# Total Emails: %s" % total_email_count)
    write("# Ignored based on sender or recipient email: %s" % len(ignored_for_email))
    write("# Ignored based on subject: %s" % len(ignored_for_subject))
    write("# Ignored based on body content: %s" % len(ignored_for_body))
    write("-----------------------------------")
    write("# Remaining Emails: %s" % len(emails))
    write("# Threads: %s" % len(threads))
    write("")
    write("# Inbound emails: %s" % len(inbound_emails))
    write("# Outbound emails: %s" % len(outbound_emails))
    write("# Selfie emails: %s" % len(selfie_emails))
    write("# Other (lists, bccs): %s" % len(other_emails))
    write("")
    write("# Threads where I didn't get a response: %s" % len(last_responder_was_me))
    for conversation in last_responder_was_me:
        write(u"    * [{thread_length}] To:{to}, Subject:{subject}".format(
            thread_length=conversation.length,
            to=conversation.last_email.to,
            subject=conversation.last_email.subject)
            )
    write("")
    write("# Threads where I didn't respond: %s" % len(last_responder_was_counterparty))
    for conversation in last_responder_was_counterparty:
        if conversation.length > MIN_THREAD_LENGTH:
            write(u"    * [{thread_length}] From:{fr}, Subject:{subject}".format(
                thread_length=conversation.length,
                fr=conversation.last_email.fr,
                subject=conversation.last_email.subject,
                ))
    write("")
    write("# Outbound -> # Response: %s -> %s" % (len(outbound_emails), len(outbound_emails) - len(last_responder_was_me) ))

    # print [i.get_last_response_time(i.thread) for i in last_responder_was_counterparty if i.length > 2]

    response_times = []
    for thread in (last_responder_was_counterparty + last_responder_was_me):
        response_times.extend(thread.get_response_times())

    senders = {}
    for response_time in response_times:
        sender = response_time.get("fr")
        name, email_address = parseaddr(sender)
        if not email_address in senders.keys():
            senders[email_address] = []
        senders[email_address].append(response_time.get("response_time"))

    print "look at senders"




#if __name__ == "__main__":
#    main()

        # find all the singles
        # single sent to me = inbound unanswered
        # single sent by me = outbound unresponded
        # mul

    # for i, email in enumerate(emails[:]):
        # print email
        # body = email.body.replace("=\r\n", "")
        # soup = BeautifulSoup(body)

    # play with your gmail...
    # g.logout()


# Add user response times / rates
# links for each
# wire up oauth
# render html
