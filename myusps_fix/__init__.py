"""My USPS interface."""
""" This is heavily modified to allow me to download mail images and build GIF """

import datetime
import os
import logging
import os.path
import pickle
import re
from bs4 import BeautifulSoup
from dateutil.parser import parse
import requests
from requests.auth import AuthBase

_LOGGER = logging.getLogger(__name__)
HTML_PARSER = 'html.parser'
LOGIN_FORM_TAG = 'form'
LOGIN_FORM_ATTRS = {'name': 'loginForm'}
PROFILE_TAG = 'div'
PROFILE_ATTRS = {'class': 'atg_store_myProfileInfo'}
NO_PACKAGES_TAG = 'p'
NO_PACKAGES_ATTRS = {'id': 'package-status'}
INFORMED_DELIVERY_TAG = 'div'
INFORMED_DELIVERY_ATTRS = {'id': 'realMail'}
MAIL_IMAGE_TAG = 'div'
MAIL_IMAGE_ATTRS = {'class': 'mailImageBox'}
DASHBOARD_TAG = 'div'
DASHBOARD_ATTRS = {'id': 'dash-detail'}
SHIPPED_FROM_TAG = 'div'
SHIPPED_FROM_ATTRS = {'class': 'mobile-from'}
LOCATION_TAG = 'span'
LOCATION_ATTRS = {'class': 'mypost-tracked-item-details-location'}
DATE_TAG = 'div'
DATE_ATTRS = {'class': 'mypost-tracked-item-details-date'}
STATUS_TAG = 'span'
STATUS_ATTRS = {'class': 'mypost-tracked-item-details-status'}
TRACKING_NUMBER_TAG = 'div'
TRACKING_NUMBER_ATTRS = {'style': 'word-break: break-word;'}
ERROR_TAG = 'span'
ERROR_ATTRS = {'class': 'error'}

BASE_URL = 'https://reg.usps.com'
MY_USPS_URL = BASE_URL + '/login?app=MyUSPS'
AUTHENTICATE_URL = BASE_URL + '/entreg/json/AuthenticateAction'
LOGIN_URL = BASE_URL + '/entreg/LoginAction'
DASHBOARD_URL = 'https://my.usps.com/mobileWeb/pages/myusps/HomeAction_input'
INFORMED_DELIVERY_URL = 'https://informeddelivery.usps.com/box/pages/secure/HomeAction_input.action'
INFORMED_DELIVERY_IMAGE_URL = 'https://informeddelivery.usps.com/box/pages/secure/'
PROFILE_URL = 'https://store.usps.com/store/myaccount/profile.jsp'

COOKIE_PATH = './usps_cookies.pickle'
ATTRIBUTION = 'Information provided by www.usps.com'
USER_AGENT = 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) ' \
             'Chrome/41.0.2228.0 Safari/537.36'
EFMJ_HEADER = 'x-efmj'
UUID_TOKEN_REGEX = re.compile(r'"uniqueStateKey",100,"(.+?)"', re.MULTILINE)
PAYLOAD_KEY_REGEX = re.compile(r'httpMethods:\["POST"\]\}\],"(.+?)"', re.MULTILINE)


class USPSError(Exception):
    """USPS error."""

    pass


def _save_cookies(requests_cookiejar, filename):
    """Save cookies to a file."""
    with open(filename, 'wb') as handle:
        pickle.dump(requests_cookiejar, handle)


def _load_cookies(filename):
    """Load cookies from a file."""
    with open(filename, 'rb') as handle:
        return pickle.load(handle)


def _get_elem(response, tag, attr):
    """Get element from a response."""
    parsed = BeautifulSoup(response.text, HTML_PARSER)
    return parsed.find(tag, attr)


def _require_elem(response, tag, attrs):
    """Require that an element exist."""
    login_form = _get_elem(response, LOGIN_FORM_TAG, LOGIN_FORM_ATTRS)
    if login_form is not None:
        raise USPSError('Not logged in')
    elem = _get_elem(response, tag, attrs)
    if elem is None:
        raise ValueError('No element found')
    return elem


def _get_location(row):
    """Get package location."""
    return ' '.join(list(row.find(LOCATION_TAG, LOCATION_ATTRS).strings)[0]
                    .split()).replace(' ,', ',')


def _get_status(row):
    """Get package status."""
    return row.find(STATUS_TAG, STATUS_ATTRS).string.strip().split(',')


def _get_shipped_from(row):
    """Get where package was shipped from."""
    shipped_from_elems = row.find(SHIPPED_FROM_TAG, SHIPPED_FROM_ATTRS).find_all('div')
    if len(shipped_from_elems) > 1 and shipped_from_elems[1].string:
        return shipped_from_elems[1].string.strip()
    return ''


def _get_date(row):
    """Get latest package date."""
    date_string = ' '.join(row.find(DATE_TAG, DATE_ATTRS).string.split())
    try:
        return str(parse(date_string))
    except ValueError:
        return None


def _get_tracking_number(row):
    """Get package tracking number."""
    return row.find(TRACKING_NUMBER_TAG, TRACKING_NUMBER_ATTRS).string.replace(' ', '').strip()


def _get_login_metadata(session):
    """Get login metadata."""
    resp = session.get(MY_USPS_URL)
    # Token for login form submission
    form = _get_elem(resp, LOGIN_FORM_TAG, LOGIN_FORM_ATTRS)
    token_elem = form.find('input', {'name': 'token'})
    # UUID token and payload key for GTM compatibility
    uuid_token_result = UUID_TOKEN_REGEX.search(resp.text)
    payload_key_result = PAYLOAD_KEY_REGEX.search(resp.text)
    if token_elem and uuid_token_result and payload_key_result:
        _LOGGER.debug('login form token: %s', token_elem.get('value'))
        _LOGGER.debug('gtm uuid token: %s', uuid_token_result.group(1))
        _LOGGER.debug('gtm payload key: %s', payload_key_result.group(1))
        return token_elem.get('value'), uuid_token_result.group(1), payload_key_result.group(1)
    raise USPSError('No login metadata found')


def _login(session):
    """Login."""
    _LOGGER.debug("attempting login")
    token, uuid_token, payload_key = _get_login_metadata(session)
    resp = session.post(AUTHENTICATE_URL, {
        'username':  session.auth.username,
        'password': session.auth.password
    }, headers={
        EFMJ_HEADER+'uniqueStateKey': uuid_token,
        EFMJ_HEADER+payload_key: ''
    })
    data = resp.json()
    if 'rs' not in data:
        raise USPSError('authentication failed')
    if data['rs'] != 'success':
        raise USPSError('authentication failed')
    resp = session.post(LOGIN_URL, {
        'username': session.auth.username,
        'password': session.auth.password,
        'token': token,
        'struts.token.name': 'token'
    })
    error = _get_elem(resp, ERROR_TAG, ERROR_ATTRS)
    if error is not None:
        raise USPSError(error.text.strip())
    _save_cookies(session.cookies, session.auth.cookie_path)


def authenticated(function):
    """Re-authenticate if session expired."""
    def wrapped(*args):
        """Wrap function."""
        try:
            return function(*args)
        except USPSError:
            _LOGGER.info("attempted to access page before login")
            _login(args[0])
            return function(*args)
    return wrapped


@authenticated
def get_profile(session):
    """Get profile data."""
    profile = _require_elem(session.get(PROFILE_URL), PROFILE_TAG, PROFILE_ATTRS)
    data = {}
    for row in profile.find_all('tr'):
        cells = row.find_all('td')
        if len(cells) == 2:
            key = ' '.join(cells[0].find_all(text=True)).strip().lower().replace(' ', '_')
            value = ' '.join(cells[1].find_all(text=True)).strip()
            data[key] = value
    return data


@authenticated
def get_packages(session):
    """Get package data."""
    _LOGGER.info("attempting to get package data")
    packages = []
    response = session.get(DASHBOARD_URL)
    no_packages = _get_elem(response, NO_PACKAGES_TAG, NO_PACKAGES_ATTRS)
    if no_packages is not None:
        return packages
    dashboard = _require_elem(response, DASHBOARD_TAG, DASHBOARD_ATTRS)
    for row in dashboard.find('ul').find_all('li', recursive=False):
        status = _get_status(row)
        packages.append({
            'tracking_number': _get_tracking_number(row),
            'primary_status': status[0].strip(),
            'secondary_status': status[1].strip() if len(status) == 2 else '',
            'date': _get_date(row),
            'location': _get_location(row),
            'shipped_from': _get_shipped_from(row)
        })
    return packages


@authenticated
def get_mail(session, date=datetime.datetime.now().date()):
    """Get mail data."""
    _LOGGER.info("attempting to get informed delivery data")
    mail = []
    response = session.post(INFORMED_DELIVERY_URL, {
        'selectedDate': '{0:%m}/{0:%d}/{0:%Y}'.format(date)
    })
    container = _require_elem(response, INFORMED_DELIVERY_TAG, INFORMED_DELIVERY_ATTRS)
    for row in container.find_all(MAIL_IMAGE_TAG, MAIL_IMAGE_ATTRS):
        img = row.find('img').get('src')
        mail.append({
            'id': img.split('=')[1],
            'date': str(date),
            'image': '{}{}'.format(INFORMED_DELIVERY_IMAGE_URL, img)
        })
    """Download and compile images if we got mail, otherwise copy nomail image over GIF"""
    if len(mail) >= 1:
        download_images(session, mail)
    else:
        os.system("cp /opt/homeassistant/mail/nomail /opt/homeassistant/mail/mail.gif")
    return mail


def download_images(session, mail):
    os.system("rm /opt/homeassistant/mail/*.jpg")
    count = 1
    total = len(mail)
    for mailpiece in mail:
        img_data = session.get(mailpiece['image']).content
        """Download the image"""
        with open('/opt/homeassistant/mail/' + mailpiece['id'] + '.jpg', 'wb') as handler:
            handler.write(img_data)
        """Annotate image with it's number over the total so we can keep track in the final GIF"""
        os.system("convert /opt/homeassistant/mail/" + mailpiece['id'] + ".jpg -fill white -undercolor \
            '#00000080' -gravity SouthWest -pointsize 18 -annotate +0+0 '" + str(count) + "/" + \
            str(total) + "' /opt/homeassistant/mail/" + str(count) + ".jpg 2>/dev/null")
        """Remove un-annotated image"""
        os.system("rm /opt/homeassistant/mail/" + mailpiece['id'] + ".jpg")
        count += 1
    """Create GIF of all mail images"""
    os.system("convert -delay 300 -loop 0 -dispose previous /opt/homeassistant/mail/*.jpg /opt/homeassistant/mail/mail.gif")


def get_session(username, password, cookie_path=COOKIE_PATH):
    """Get session, existing or new."""
    class USPSAuth(AuthBase):  # pylint: disable=too-few-public-methods
        """USPS authorization storage."""

        def __init__(self, username, password, cookie_path):
            """Init."""
            self.username = username
            self.password = password
            self.cookie_path = cookie_path

        def __call__(self, r):
            """Call is no-op."""
            return r

    session = requests.session()
    session.auth = USPSAuth(username, password, cookie_path)
    session.headers.update({'User-Agent': USER_AGENT})
    if os.path.exists(cookie_path):
        _LOGGER.debug("cookie found at: %s", cookie_path)
        session.cookies = _load_cookies(cookie_path)
    else:
        _login(session)
    return session
