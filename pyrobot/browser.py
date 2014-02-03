"""
Robotic browser
"""

import re
import requests
import urlparse
from bs4 import BeautifulSoup
from bs4.element import Tag

from . import helpers
from .forms.form import Form

class RoboError(Exception): pass

_link_ptn = re.compile('^(a|button)$', re.I)
_form_ptn = re.compile('^form$', re.I)

class RoboState(object):
    """Representation of a browser state. Wraps the browser and response, and
    lazily parses the response content.

    """

    def __init__(self, browser, response):
        self.browser = browser
        self.response = response
        self.url = response.url
        self._parsed = None

    @property
    def parsed(self):
        """Lazily parse response content, using HTML parser specified by the
        browser.

        """
        if self._parsed is None:
            self._parsed = BeautifulSoup(
                self.response.content,
                features=self.browser.parser,
            )
        return self._parsed

class RoboBrowser(object):
    """Robotic web browser."""

    def __init__(self, auth=None, parser=None, headers=None, user_agent=None,
                 history=True):
        """RoboBrowser constructor.

        :param tuple auth: Tuple of (username, password)
        :param str parser: HTML parser; used by BeautifulSoup
        :param dict headers: Default headers
        :param str user_agent: Default user-agent
        :param history: History length; infinite if True, 1 if falsy, else
            takes integer value

        """
        self.session = requests.Session()

        # Add default basic auth
        if auth:
            self.session.auth = auth

        # Add default headers
        headers = headers or {}
        if user_agent is not None:
            headers['User-Agent'] = user_agent

        self.parser = parser

        # Configure history
        self.history = history
        if history is True:
            self._maxlen = None
        elif not history:
            self._maxlen = 1
        else:
            self._maxlen = history
        self._states = []
        self._cursor = -1

    def __repr__(self):
        try:
            return '<RoboBrowser url={0}>'.format(self.url)
        except RoboError:
            return '<RoboBrowser>'

    @property
    def state(self):
        if self._cursor == -1:
            raise RoboError('No state')
        try:
            return self._states[self._cursor]
        except IndexError:
            raise RoboError('Index out of range')

    @property
    def response(self):
        return self.state.response

    @property
    def url(self):
        return self.state.url

    @property
    def parsed(self):
        return self.state.parsed

    @property
    def find(self):
        try:
            return self.parsed.find
        except AttributeError:
            raise RoboError

    @property
    def find_all(self):
        try:
            return self.parsed.find_all
        except AttributeError:
            raise RoboError

    @property
    def select(self):
        try:
            return self.parsed.select
        except AttributeError:
            raise RoboError

    def _build_url(self, url):
        """Build absolute URL.

        :param url: Full or partial URL
        :return: Full URL

        """
        return urlparse.urljoin(
            self.url,
            url
        )

    def open(self, url):
        """Open a URL.

        :param str url: URL

        """
        response = self.session.get(url)
        self._update_state(response)

    def _update_state(self, response):
        """Update the state of the browser. Create a new state object, and
        append to or overwrite the browser's state history.

        :param requests.Response: New response object

        """
        # Clear trailing states
        self._states = self._states[:self._cursor + 1]

        # Append new state
        state = RoboState(self, response)
        self._states.append(state)
        self._cursor += 1

        # Clear leading states
        if self._maxlen:
            decrement = len(self._states) - self._maxlen
            if decrement > 0:
                self._states = self._states[decrement:]
                self._cursor -= decrement

    def _traverse(self, n=1):
        """Traverse state history. Used by `back` and `forward` methods.

        :param int n: Cursor increment. Positive values move forward in the
            browser history; negative values move backward.

        """
        if not self.history:
            raise RoboError('Not tracking history')
        cursor = self._cursor + n
        if cursor >= len(self._states) or cursor < 0:
            raise RoboError('Index out of range')
        self._cursor = cursor

    def back(self, n=1):
        """Go back in browser history.

        :param int n: Number of pages to go back

        """
        self._traverse(-1 * n)

    def forward(self, n=1):
        """Go forward in browser history.

        :param int n: Number of pages to go forward

        """
        self._traverse(n)

    def get_link(self, text=None, *args, **kwargs):
        """Find an anchor or button by containing text, as well as standard
        BeautifulSoup arguments.

        :param text: String or regex to be matched in link text
        :return: BeautifulSoup tag if found, else None

        """
        return helpers.find(
            self.parsed, _link_ptn, text=text, *args, **kwargs
        )

    def get_links(self, text=None, *args, **kwargs):
        """Find anchors or buttons by containing text, as well as standard
        BeautifulSoup arguments.

        :param text: String or regex to be matched in link text
        :return: List of BeautifulSoup tags

        """
        return helpers.find_all(
            self.parsed, _link_ptn, text=text, *args, **kwargs
        )

    def get_form(self, id=None, *args, **kwargs):
        """Find form by ID, as well as standard BeautifulSoup arguments.

        :param str id: Form ID
        :return: BeautifulSoup tag if found, else None

        """
        if id:
            kwargs['id'] = id
        form = self.find(_form_ptn, *args, **kwargs)
        if form is not None:
            return Form(form)

    def get_forms(self, *args, **kwargs):
        """Find forms by standard BeautifulSoup arguments.

        :return: List of BeautifulSoup tags

        """
        forms = self.find_all(_form_ptn, *args, **kwargs)
        return [
            Form(form)
            for form in forms
        ]

    def follow_link(self, value=None, *args, **kwargs):
        """Find a click a link by tag, pattern, and/or BeautifulSoup
        arguments.

        :param value: BeautifulSoup tag, string, or regex. If tag, follow its
            href; if string or regex, search parsed document for match

        """
        if isinstance(value, Tag):
            link = value
        elif isinstance(value, (str, unicode)):
            text = re.compile(re.escape(value), re.I)
            link = self.get_link(text=text, *args, **kwargs)
        elif isinstance(value, re._pattern_type):
            link = self.get_link(text=value, *args, **kwargs)
        else:
            link = self.get_link(*args, **kwargs)
        if link is None:
            raise RoboError('No results found')
        href = link.get('href')
        if href is None:
            raise RoboError('Link element must have href attribute')
        self.open(self._build_url(href))

    def submit_form(self, form):
        """Submit a form.

        :param Form form: Filled-out form object

        """
        # Get HTTP verb
        func = getattr(self.session, form.method.lower())

        # Send request
        url = self._build_url(form.action) or self.url
        data = form.serialize()
        response = func(url, **data)

        # Update history
        self._update_state(response)
