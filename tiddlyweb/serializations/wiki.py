"""
Serialize into a fullblown tiddlywiki wiki.
"""

import re

from tiddlyweb.serializer import NoSerializationError
from tiddlyweb.serializations import SerializationInterface
from tiddlyweb.tiddler import Tiddler
from tiddlyweb.web.util import server_base_url

# this should come from config or even
# from a url
empty_html = 'lib/empty.html'
splitter = '</div>\n<!--POST-STOREAREA-->\n'

class Serialization(SerializationInterface):

    def as_bag(self, bag, input_string):
        """
        Turn a wiki into a bunch of tiddlers
        stored in the bag.
        """
        try:
            from tiddlyweb.importer import import_wiki
            return import_wiki(self.environ['tiddlyweb.store'], input_string, bag.name)
        except ImportError:
            raise NoSerializationError

    def list_tiddlers(self, bag):
        return self._put_tiddlers_in_tiddlywiki(bag.list_tiddlers())

    def tiddler_as(self, tiddler):
        return self._put_tiddlers_in_tiddlywiki([tiddler], title=tiddler.title)

    def _put_tiddlers_in_tiddlywiki(self, tiddlers, title='TiddlyWeb Loading'):
# read in empty.html from somewhere (prefer url)
# replace <title> with the right stuff
# replace markup etc with the right stuff
# hork in the stuff

        # figure out the content to be pushed into the
        # wiki and calculate the title
        lines = ''
        candidate_title = None
        candidate_subtitle = None
        for tiddler in tiddlers:
            lines += self._tiddler_as_div(tiddler)
            if tiddler.title == 'SiteTitle':
                candidate_title = tiddler.text
            if tiddler.title == 'SiteSubtitle':
                candidate_subtitle = tiddler.text

        # Turn the title into HTML and then turn it into
        # plain text so it is of a form satisfactory to <title>
        title = self._determine_title(title, candidate_title, candidate_subtitle)
        title = self._plain_textify_string(title)

        # load the wiki
        wiki = self._get_wiki()
        # put the title in place
        wiki = self._inject_title(wiki, title)

        # split the wiki into the before store and after store
        # sections, put our content in the middle
        tiddlystart, tiddlyfinish = self._split_wiki(wiki)
        return tiddlystart + lines + splitter + tiddlyfinish

    def _plain_textify_string(self, title):
        try:
            tiddler = Tiddler('tmp', bag='tmp')
            tiddler.text = unicode(title)
            # If the HTML serialization doesn't have wikklytext
            # we will get back wikitext inside the div classed
            # 'tiddler' instead of HTML
            from tiddlyweb.wikklyhtml import tiddler_to_wikklyhtml
            output = tiddler_to_wikklyhtml('', '', tiddler)

            from BeautifulSoup import BeautifulSoup
            soup = BeautifulSoup(output)
            title = soup.findAll(text=True)
            return ''.join(title).rstrip().lstrip()
        except ImportError:
            # If we have been unable to load BeautifilSoup then
            # fall back to the original wikitext
            return title

    def _determine_title(self, title, candidate_title, candidate_subtitle):
        if candidate_title and candidate_subtitle:
            return '%s - %s' % (candidate_title, candidate_subtitle)
        if candidate_title:
            return candidate_title
        if candidate_subtitle:
            return candidate_subtitle
        return title

    def _inject_title(self, wiki, title):
        title = '\n<title>\n%s\n</title>\n' % title
        return re.sub('\n<title>\n[^\n]*\n</title>\n', title, wiki, count=0)

    def _get_wiki(self):
        f = open(empty_html)
        wiki = f.read()
        wiki = unicode(wiki, 'utf-8')
        return wiki

    def _split_wiki(self, wiki):
        return wiki.split(splitter)

    def _tiddler_as_div(self, tiddler):
        """
        Read in the tiddler from a div.
        """
        recipe_name = ''
        if tiddler.recipe:
            recipe_name = tiddler.recipe
        try: 
            host = server_base_url(self.environ)
        except KeyError:
            host = ''
        host = '%s/' % host

        return '<div title="%s" server.page.revision="%s" modifier="%s" server.workspace="%s" server.type="tiddlyweb" server.host="%s" server.bag="%s" modified="%s" created="%s" tags="%s">\n<pre>%s</pre>\n</div>\n' \
                % (tiddler.title, tiddler.revision, tiddler.modifier, recipe_name,
                        host, tiddler.bag, tiddler.modified, tiddler.created,
                        self.tags_as(tiddler.tags), self._html_encode(tiddler.text))

