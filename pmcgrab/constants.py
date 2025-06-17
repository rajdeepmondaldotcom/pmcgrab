import logging
import warnings
import re
import signal

logger = logging.getLogger(__name__)
warnings.formatwarning = lambda msg, cat, *args, **kwargs: f"{cat.__name__}: {msg}\n\n"
warnings.filterwarnings("ignore")

SUPPORTED_DTD_URLS = [
    "https://dtd.nlm.nih.gov/ncbi/pmc/articleset/nlm-articleset-2.0.dtd"
]
DTD_URL_PATTERN = re.compile(r'"(https?://\S+)"')
END_OF_URL_PATTERN = re.compile(r"[^/]+$")

class NoDTDFoundError(Exception):
    pass

class TimeoutException(Exception):
    pass

def timeout_handler(signum, frame):
    """Raise a ``TimeoutException`` when a signal alarm is triggered."""
    raise TimeoutException("Operation timed out")
signal.signal(signal.SIGALRM, timeout_handler)

EMAILS = sorted(set([
    "bk68g1gx@test.com", "wkv1h06c@sample.com", "m42touro@sample.com", "vy8u7tsx@test.com",
    "8xsqaxke@sample.com", "cilml02q@sample.com", "1s1ywssv@demo.com", "pfd4bf0y@demo.com",
    "hvjhnv7o@test.com", "vtirmn0j@sample.com", "4bk68g1gx0y4@sample.com", "a8riw1tsm42t@sample.com",
    "uro2fp0bt1w@demo.com", "8xsqaxkenhc@test.com", "js2rq1s1yw@demo.com", "7t2pfd4bf0yf@test.com",
    "5h1cwqg2p0hx@sample.com", "n0jc5ob2lrb@demo.com", "hng0gryqf@test.com", "iftxphoxuk5@demo.com",
    "bwd4n34n0e@sample.com", "bpx4le9l@demo.com", "sjqexrltn@test.com", "r6xjuxkjahc@demo.com",
    "0ppd1x4w@test.com", "ur58ralllmn@sample.com", "ifm9ikmz5@test.com", "72z4j1pvi@demo.com",
    "zsgq0a1y1s@sample.com", "b25m7bv9lrdr@demo.com", "g28fn53pg@demo.com", "yimjg6il5@sample.com",
    "srsu7jehnqar@demo.com", "c4ktfvaho@demo.com", "do19vw6hbad@demo.com", "1fk0t7j1@test.com",
    "ym4w8xkimeu@test.com", "5icttn2von8@sample.com", "twy6ejv0@test.com", "nmjvr8pzr9@demo.com"
]))
email_counter = 0

class ReversedBiMapComparisonWarning(Warning): pass
class ValidationWarning(Warning): pass
class MultipleTitleWarning(Warning): pass
class UnhandledTextTagWarning(Warning): pass
class ReadHTMLFailure(Warning): pass
class UnexpectedMultipleMatchWarning(Warning): pass
class UnexpectedZeroMatchWarning(Warning): pass
class UnmatchedCitationWarning(Warning): pass
class UnmatchedTableWarning(Warning): pass
class UnexpectedTagWarning(Warning): pass
class EmptyTextWarning(Warning): pass
class PubmedHTTPError(Warning): pass

