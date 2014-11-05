import datetime
import os
from email.utils import parseaddr

import requests
from gmail import Gmail

# OAUTH_URL = 'https://accounts.google.com/o/oauth2/auth'
# OAUTH_URL_TOKEN = 'https://accounts.google.com/o/oauth2/token'
# CLIENT_ID = '626558672627-v4rg26hb07gpo4od97b3o1s078avfdk0.apps.googleusercontent.com'
# CLIENT_SECRET = 'wzT01GwvmqMGxR7sDMw-Sxrh'

ALIASES = [
    "eric@rentapplication",
    "eric@rocketlease",
    "ericzliu@gmail",
    ]
# USERNAME = "rob@rentapplication.net"
# ACCESS_TOKEN = 'ya29.pADR7aHI1-VN1q_7AUj0h9iZqbBDblVWChnRa2lugO3WRPIZg5jWqt9p6ijFkOZ2KLBCcjD_FDFYjQ'
# REFRESH_TOKEN = '1/KVqj63s7TTMnglL4-LLu2gs4uolkKZaBF_JlzohGiyYMEudVrK5jSpoR30zcRFq6'

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

# def refresh_token():
#     write("Original token didn't work, refreshing token.")
#     r = requests.post(OAUTH_URL_TOKEN, data={
#         'client_id': CLIENT_ID,
#         'client_secret': CLIENT_SECRET,
#         'refresh_token': REFRESH_TOKEN,
#         'grant_type': 'refresh_token',
#     })
#     new_access_token  = r.json()['access_token']
#     return new_access_token

def day_of_week(num):
    if num == 1:
        return "M"
    elif num == 2:
        return "T"
    elif num == 3:
        return "W"
    elif num == 4:
        return "Th"
    elif num == 5:
        return "F"
    elif num == 6:
        return "Sa"
    elif num == 0:
        return "Su"
    else:
        raise Exception

def email_in_aliases(email, aliases):
    if not email:
        return False
    return any(alias.lower() in email.lower() for alias in aliases)

def write(string):
    return
    # print(string)

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


def convert_conversation_object_to_dict(conversation):
    """Just to make it picklable"""
    return dict(length = conversation.length,
                last_email = convert_email_object_to_dict(conversation.last_email),
                get_gmail_url=conversation.get_gmail_url(),
                subject=conversation.subject,
               )

def convert_email_object_to_dict(email):
    """Converts a gmail.Email object into a dict to make it picklable"""
    return dict(subject=email.subject,
                fr=parseaddr(email.fr),
                to=parseaddr(email.to),
                sent_at=email.sent_at,
               )

# def main():
def calculate_email_stats(
    USERNAME,
    ACCESS_TOKEN,
    DAYS,
    ALIASES=[],
    IGNORE_EMAILS=[],
    IGNORE_SUBJECT_KEYWORDS=[],
    IGNORE_BODY_KEYWORDS=[],
    MIN_THREAD_LENGTH=0,
    ):
    """
    Calculate a bunch of stats and return a dict of values for rendering.
    """

    ALIASES.append(USERNAME)
    # Log in to Gmail
    g = Gmail()
    g.authenticate(USERNAME, ACCESS_TOKEN)

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
    only_sender_was_me = []

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

        if all([email_in_aliases(email.fr, ALIASES) for email in conversation.thread]):
            only_sender_was_me.append(conversation)

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

    email_days = set(email.sent_at.date() for email in emails)
    emails_received_by_day = [(email_day, len([email for email in inbound_emails if email.sent_at.date() == email_day])) for email_day in email_days]
    emails_sent_by_day = [(email_day, len([email for email in outbound_emails if email.sent_at.date() == email_day])) for email_day in email_days]

    emails_received_by_day.sort(cmp=lambda x,y: cmp(x,y))
    emails_sent_by_day.sort(cmp=lambda x,y: cmp(x,y))

    emails_received_by_day = [{"date": "{} {}".format(day_of_week(date.weekday()), date.day), "count": count} for (date, count) in emails_received_by_day]
    emails_sent_by_day = [{"date": "{} {}".format(day_of_week(date.weekday()), date.day), "count": count} for (date, count) in emails_sent_by_day]

    write("Sorted emails")

    write("* " * 25)

    inbox_total = g.inbox().count()
    inbox_unread = g.inbox().count(unread=True)
    total_email_count = total_email_count
    ignored_for_email = ignored_for_email
    ignored_for_subject = ignored_for_subject
    ignored_for_body = ignored_for_body

    num_remaining_emails = len(emails)
    num_threads = len(threads)
    num_inbound_emails = len(inbound_emails)
    num_outbound_emails = len(outbound_emails)
    num_selfie_emails =  len(selfie_emails)
    num_other_emails = len(other_emails)

    num_last_responder_was_me = len(last_responder_was_me)
    num_last_responder_was_counterparty =  len(last_responder_was_counterparty)

    response_times = []
    for thread in (last_responder_was_counterparty + last_responder_was_me):
        response_times.extend(thread.get_response_times())

    senders = {}
    for response_time in response_times:
        if not response_time.get("fr"):
            continue
        sender = response_time.get("fr").lower()
        name, email_address = parseaddr(sender)
        if not email_address in senders.keys():
            senders[email_address] = {'response_times':[]}
        senders[email_address]['response_times'].append(response_time.get("response_time"))

    emails_sent_per_person = [(sender, len(senders[sender].get("response_times"))) for sender in senders.keys()]
    emails_sent_per_person.sort(cmp=lambda x,y: cmp(x[1], y[1]), reverse=True)

    for sender in senders.keys():
        senders[sender]['num_no_response'] = len([response_time is None for response_time in senders[sender]['response_times']])
        senders[sender]['response_times'] = [response_time for response_time in senders[sender]['response_times'] if not response_time is None]

    my_response_times = []
    for sender in senders.keys():
        if email_in_aliases(sender, ALIASES):
            my_response_times.extend(senders[sender].get("response_times"))
    my_response_times = [int(t/3600) for t in my_response_times]


    last_responder_was_me = [convert_conversation_object_to_dict(i) for i in last_responder_was_me]
    last_responder_was_counterparty = [convert_conversation_object_to_dict(i) for i in last_responder_was_counterparty]
    only_sender_was_me = [convert_conversation_object_to_dict(i) for i in only_sender_was_me]
    only_sender_was_me.sort(cmp=lambda x,y: cmp(x.get("length"), y.get("length")), reverse=True)
    emails_sent_per_person.sort(cmp=lambda x,y: cmp(x[1], y[1]), reverse=True)

    ignored_for_email = [convert_email_object_to_dict(i) for i in ignored_for_email]
    ignored_for_subject = [convert_email_object_to_dict(i) for i in ignored_for_subject]
    ignored_for_body = [convert_email_object_to_dict(i) for i in ignored_for_body]

    #_last_responder_was_me = []
    #for conversation in last_responder_was_me:
    #    _last_responder_was_me.append(
    #        dict(thread_length=conversation.length,
    #             to=conversation.last_email.to,
    #             url=conversation.get_gmail_url(),
    #             subject=conversation.last_email.subject))
    #last_responder_was_me = _last_responder_was_me
    
    #_last_responder_was_counterparty = []
    #for conversation in last_responder_was_counterparty:
    #    if conversation.length > MIN_THREAD_LENGTH:
    #        _last_responder_was_counterparty.append(
    #            dict(
    #                thread_length=conversation.length,
    #                fr=conversation.last_email.fr,
    #                 url=conversation.get_gmail_url(),
    #                subject=conversation.last_email.subject))
    #last_responder_was_counterparty = _last_responder_was_counterparty

    keys = [
        "inbox_total",
        "inbox_unread",
        "total_email_count",
        "ignored_for_email",
        "ignored_for_subject",
        "ignored_for_body",
        "num_remaining_emails",
        "num_threads",
        "num_inbound_emails",
        "num_outbound_emails",
        "num_selfie_emails",
        "num_other_emails",
        "num_last_responder_was_me",
        "num_last_responder_was_counterparty",
        "last_responder_was_me",
        "last_responder_was_counterparty",
        "only_sender_was_me",
        "senders",
        "response_times",
        "my_response_times",
        "emails_sent_per_person",
        "DAYS",
        "emails_sent_by_day",
        "emails_received_by_day",
        ]
    return dict([(key, locals()[key]) for key in keys])

