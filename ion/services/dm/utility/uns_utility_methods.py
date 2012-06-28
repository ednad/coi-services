
from pyon.public import get_sys_name, CFG
from interface.services.dm.idiscovery_service import DiscoveryServiceClient
import smtplib
import gevent
from gevent.timeout import Timeout

class fake_smtplib(object):

    def __init__(self,host):
        self.host = host
        self.sentmail = gevent.queue.Queue()

    @classmethod
    def SMTP(cls,host):
        log.info("In fake_smptplib.SMTP method call. class: %s, host: %s" % (str(cls), str(host)))
        return cls(host)

    def sendmail(self, msg_sender, msg_recipient, msg):
        log.info('Sending fake message from: %s, to: "%s"' % (msg_sender,  msg_recipient))
        self.sentmail.put((msg_sender, msg_recipient, msg))


def send_email(message, msg_recipient):
    '''
    A common method to send email with formatting

    @param message              Event
    @param msg_recipient        str
    '''

    # the 'from' email address for notification emails
    ION_NOTIFICATION_EMAIL_ADDRESS = 'ION_notifications-do-not-reply@oceanobservatories.org'
    # the default smtp server
    ION_SMTP_SERVER = 'mail.oceanobservatories.org'

    smtp_host = CFG.get_safe('server.smtp.host', ION_SMTP_SERVER)
    smtp_port = CFG.get_safe('server.smtp.port', 25)
    smtp_sender = CFG.get_safe('server.smtp.sender')
    smtp_password = CFG.get_safe('server.smtp.password')

    log.info('smtp_host: %s' % str(smtp_host))
    log.info('smtp_port: %s' % str(smtp_port))

    if CFG.get_safe('system.smtp',False): #Default is False - use the fake_smtp
        log.warning('Using the real SMTP library to send email notifications!')

        #@todo - for now hard wire for gmail account
        #msg_sender = 'ooici777@gmail.com'
        #gmail_pwd = 'ooici777'

        smtp_client = smtplib.SMTP(smtp_host)
        smtp_client.ehlo()
        smtp_client.starttls()
        smtp_client.login(smtp_sender, smtp_password)

        log.warning("Using smpt host: %s" % smtp_host)

    else:
        # Keep this as a warning
        log.warning('Using a fake SMTP library to simulate email notifications!')

        #@todo - what about port etc??? What is the correct interface to fake?
        smtp_client = fake_smtplib.SMTP(smtp_host)

    time_stamp = str( datetime.fromtimestamp(time.mktime(time.gmtime(float(message.ts_created)/1000))))

    event = message.type_
    origin = message.origin
    description = message.description


    # build the email from the event content
    msg_body = string.join(("Event: %s" %  event,
                            "",
                            "Originator: %s" %  origin,
                            "",
                            "Description: %s" % description ,
                            "",
                            "Time stamp: %s" %  time_stamp,
                            "",
                            "You received this notification from ION because you asked to be "\
                            "notified about this event from this source. ",
                            "To modify or remove notifications about this event, "\
                            "please access My Notifications Settings in the ION Web UI.",
                            "Do not reply to this email.  This email address is not monitored "\
                            "and the emails will not be read."),
        "\r\n")
    msg_subject = "(SysName: " + get_sys_name() + ") ION event " + event + " from " + origin
    msg_sender = ION_NOTIFICATION_EMAIL_ADDRESS

    msg = MIMEText(msg_body)
    msg['Subject'] = msg_subject
    msg['From'] = msg_sender
    msg['To'] = msg_recipient
    log.debug("UserEventProcessor.subscription_callback(): sending email to %s"\
    %msg_recipient)

    smtp_client.sendmail(smtp_sender, msg_recipient, msg.as_string())

    if CFG.get_safe('system.smtp',False):
        smtp_client.close()

        
def update_user_info():
    '''
    Method to update the user info dictionary... used by notification workers and the UNS
    '''
    #todo make this method more efficient and accept different parameters instead of using *

    search_string = 'search "name" is "*" from "users_index"'
    discovery = DiscoveryServiceClient()
    results  = discovery.parse(search_string)

    for result in results:
        user_name = result['_source'].name
        user_contact = result['_source'].contact
        notifications = result['_source'].variables.values()

        user_info[user_name] = { 'user_contact' : user_contact, 'notifications' : notifications}

    return user_info

def calculate_reverse_user_info(user_info = {}):
    '''
    Calculate a reverse user info... used by the notification workers and the UNS

    reverse_user_info = {'an_event_type' : ['user_1', 'user_2'..],
                        'an_event_subtype' : ['user_1', 'user_2'..],
                        'an_event_origin' : ['user_1', 'user_2'..],
                        'an_event_origin_type' : ['user_1', 'user_2'..],

    '''

    reverse_user_info = {}

    dict_1 = {}
    dict_2 = {}
    dict_3 = {}
    dict_4 = {}

    for key, value in user_info.iteritems:

        notifications = value['notifications']

        for notification in notifications:

            if dict_1[notification.event_type]:
                dict_1[notification.event_type].append(key)
            else:
                dict_1[notification.event_type] = [key]

            if dict_2[notification.event_subtype]:
                dict_2[notification.event_subtype].append(key)
            else:
                dict_2[notification.event_subtype] = [key]

            if dict_3[notification.origin]:
                dict_3[notification.origin].append(key)
            else:
                dict_3[notification.origin] = [key]

            if dict_4[notification.origin_type]:
                dict_4[notification.origin_type].append(key)
            else:
                dict_4[notification.origin_type] = [key]

            reverse_user_info['event_type'] = dict_1
            reverse_user_info['event_subtype'] = dict_2
            reverse_user_info['event_origin'] = dict_3
            reverse_user_info['event_origin_type'] = dict_4

    return reverse_user_info