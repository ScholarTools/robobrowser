import unittest
from nose.tools import *

import re
import functools
import responses

from pyrobot.browser import RoboBrowser
from pyrobot.browser import RoboError


def mock_responses(resps):
    """Decorator factory to make tests more DRY. Bundles responses.activate
    with a collection of response rules.

    :param list resps: List of response-formatted ArgCatcher arguments.

    """
    def wrapper(func):
        @responses.activate
        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            for resp in resps:
                responses.add(*resp.args, **resp.kwargs)
            return func(*args, **kwargs)
        return wrapped
    return wrapper

class ArgCatcher(object):
    """Simple class for memorizing positional and keyword arguments. Used to
    capture responses for mock_responses.

    """
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

mock_links = mock_responses(
    [
        ArgCatcher(
            responses.GET, 'http://pyrobot.com/links/',
            body='''
                <a href="/link1/">sheer heart attack</a>
                <a href="/link2/" class="song">night at the opera</a>
            '''
        ),
        ArgCatcher(responses.GET, 'http://pyrobot.com/link1/'),
        ArgCatcher(responses.GET, 'http://pyrobot.com/link2/'),
    ]
)

mock_forms = mock_responses(
    [
        ArgCatcher(
            responses.GET, 'http://pyrobot.com/get/',
            body='''
                <form id="bass" method="post" action="/post/">'
                    <input name="deacon" value="john" />
                </form>
                <form id="drums" method="post" action="/post/">'
                    <input name="deacon" value="john" />
                </form>
            '''
        ),
        ArgCatcher(
            responses.POST, 'http://pyrobot.com/post/',
        ),
    ]
)

mock_urls = mock_responses(
    [
        ArgCatcher(responses.GET, 'http://pyrobot.com/page1/'),
        ArgCatcher(responses.GET, 'http://pyrobot.com/page2/'),
        ArgCatcher(responses.GET, 'http://pyrobot.com/page3/'),
        ArgCatcher(responses.GET, 'http://pyrobot.com/page4/'),
    ]
)

class TestLinks(unittest.TestCase):

    @mock_links
    def setUp(self):
        self.browser = RoboBrowser()
        self.browser.open('http://pyrobot.com/links/')

    @mock_links
    def test_get_link(self):
        link = self.browser.get_link()
        assert_equal(link.get('href'), '/link1/')

    @mock_links
    def test_get_links(self):
        links = self.browser.get_links()
        assert_equal(len(links), 2)

    @mock_links
    def test_get_link_by_text(self):
        link = self.browser.get_link('opera')
        assert_equal(link.get('href'), '/link2/')

    @mock_links
    def test_follow_link_tag(self):
        link = self.browser.get_link(text=re.compile('sheer'))
        self.browser.follow_link(link)
        assert_equal(self.browser.url, 'http://pyrobot.com/link1/')

    @mock_links
    def test_follow_link_text(self):
        self.browser.follow_link('heart attack')
        assert_equal(self.browser.url, 'http://pyrobot.com/link1/')

    @mock_links
    def test_follow_link_regex(self):
        self.browser.follow_link(re.compile(r'opera'))
        assert_equal(self.browser.url, 'http://pyrobot.com/link2/')

    @mock_links
    def test_follow_link_bs_args(self):
        self.browser.follow_link(class_=re.compile(r'song'))
        assert_equal(self.browser.url, 'http://pyrobot.com/link2/')

class TestForms(unittest.TestCase):

    @mock_forms
    def setUp(self):
        self.browser = RoboBrowser()
        self.browser.open('http://pyrobot.com/get/')

    @mock_forms
    def test_get_forms(self):
        forms = self.browser.get_forms()
        assert_equal(len(forms), 2)

    @mock_forms
    def test_get_form_by_id(self):
        form = self.browser.get_form('bass')
        assert_equal(form._parsed.get('id'), 'bass')

    @mock_forms
    def test_submit_form(self):
        form = self.browser.get_form()
        self.browser.submit_form(form)
        assert_equal(self.browser.url, 'http://pyrobot.com/post/')

class TestHistoryInternals(unittest.TestCase):

    def setUp(self):
        self.browser = RoboBrowser(history=True)

    @mock_urls
    def test_open_appends_to_history(self):
        assert_equal(len(self.browser._states), 0)
        assert_equal(self.browser._cursor, -1)
        self.browser.open('http://pyrobot.com/page1/')
        assert_equal(len(self.browser._states), 1)
        assert_equal(self.browser._cursor, 0)

    @mock_forms
    def test_submit_appends_to_history(self):
        self.browser.open('http://pyrobot.com/get/')
        form = self.browser.get_form()
        self.browser.submit_form(form)

        assert_equal(len(self.browser._states), 2)
        assert_equal(self.browser._cursor, 1)

    @mock_urls
    def test_open_clears_history_after_back(self):
        self.browser.open('http://pyrobot.com/page1/')
        self.browser.open('http://pyrobot.com/page2/')
        self.browser.back()
        self.browser.open('http://pyrobot.com/page3/')
        assert_equal(len(self.browser._states), 2)
        assert_equal(self.browser._cursor, 1)

    @mock_urls
    def test_state_deque_max_length(self):
        browser = RoboBrowser(history=5)
        for _ in range(5):
            browser.open('http://pyrobot.com/page1/')
        assert_equal(len(browser._states), 5)
        browser.open('http://pyrobot.com/page2/')
        assert_equal(len(browser._states), 5)

    @mock_urls
    def test_state_deque_no_history(self):
        browser = RoboBrowser(history=False)
        for _ in range(5):
            browser.open('http://pyrobot.com/page1/')
            assert_equal(len(browser._states), 1)
            assert_equal(browser._cursor, 0)

class TestHistory(unittest.TestCase):

    @mock_urls
    def setUp(self):
        self.browser = RoboBrowser(history=True)
        self.browser.open('http://pyrobot.com/page1/')
        self.browser.open('http://pyrobot.com/page2/')
        self.browser.open('http://pyrobot.com/page3/')

    def test_back(self):
        self.browser.back()
        assert_equal(
            self.browser.url,
            'http://pyrobot.com/page2/'
        )

    def test_back_n(self):
        self.browser.back(n=2)
        assert_equal(
            self.browser.url,
            'http://pyrobot.com/page1/'
        )

    def test_forward(self):
        self.browser.back()
        self.browser.forward()
        assert_equal(
            self.browser.url,
            'http://pyrobot.com/page3/'
        )

    def test_forward_n(self):
        self.browser.back(n=2)
        self.browser.forward(n=2)
        assert_equal(
            self.browser.url,
            'http://pyrobot.com/page3/'
        )

    @mock_urls
    def test_open_clears_forward(self):
        self.browser.back(n=2)
        self.browser.open('http://pyrobot.com/page4/')
        assert_equal(
            self.browser._cursor,
            len(self.browser._states) - 1
        )
        with assert_raises(RoboError):
            self.browser.forward()

    def test_back_error(self):
        with assert_raises(RoboError):
            self.browser.back(5)
