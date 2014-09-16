# -*- coding: utf-8 -*-
"""
OnionShare | https://onionshare.org/

Copyright (C) 2014 Micah Lee <micah@micahflee.com>
Copyright (C) 2014 Kali Kaneko <kali@leap.se>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
# TODO ------------------------------------------------------------
# Refactor in progress (flask to twisted.web)

# [ ] Do cleanup of the keys files (add a flag to allow to preserve tor keys)
# [ ] Re-add the file handling boilerplate (name, content-type...)
# [ ] Re-add the slug check
# [ ] Re-add the tails stuff (might want to wait until we ditch webkit)
# [ ] Add Listener to the hidden service for doing ascii progress bar
# [ ] Add hooks for GUI
# [ ] Integrate Qtreactor?
# ----------------------------------------------------------------

import argparse
import os
import shutil
import sys

from twisted.python import log
from twisted.internet import defer
from twisted.internet import reactor
from twisted.internet.endpoints import serverFromString
from twisted.web.template import flattenString
from twisted.web.server import NOT_DONE_YET
from twisted.web.server import Site, GzipEncoderFactory
from twisted.web.resource import Resource, EncodingResourceWrapper, ErrorPage
from twisted.web.static import File

import helpers
import strings
import web
from web import OnionSharePageHtml

hsdir = os.path.abspath("./hidden_service_data")
cleanup_filenames = []

with open(os.path.join(web.static, '404.html')) as f:
    four_oh_four = f.read()


class Forbidden(ErrorPage):

    def render(self, request):
        return four_oh_four


class OnionShare(Resource):

    slugs = None
    filepath = None

    def add_onionshare_node(self, resource):
        self.putChild(resource.slug, resource)

    def getChild(self, path, request):
        return Forbidden(404, "", "")


class OnionShareDownload(OnionShare):

    def add_download_node(self):
        # XXX add guess content type, file name handling etc...
        # (subclass from File)
        self.putChild("download", File(self.filepath))

    def _slug_is_allowed(self, slug_candidate):
        # XXX FIX this
        compare = helpers.constant_time_compare
        asciify = lambda c: c.encode('ascii')

        matches = map(
            lambda slug: compare(
                asciify(slug_candidate), asciify(slug)),
            self.slug)
        print "matches", matches
        return any(matches)

    @defer.inlineCallbacks
    def _render_download_page(self, request):
        # slug_candidate = request.uri[1:]
        # XXX check slug guard

        html = yield flattenString(None, OnionSharePageHtml(
            slug=self.slug))
        request.write(html)
        request.finish()

    def render_GET(self, request):
        self._render_download_page(request)
        return NOT_DONE_YET


def serve_local(site):
    endpoint = serverFromString(reactor,
                                "tcp:8080:interface=127.0.0.1")
    endpoint.listen(site)
    print "Serving at http://localhost:8080/%s" % web.slug


def serve_hidden(site):
    hs_endpoint = serverFromString(reactor,
                                   "onion:80:hiddenServiceDir=%s" % hsdir)
    d = hs_endpoint.listen(site)
    d.addCallback(on_ready_hidden_service)


def on_ready_hidden_service(endpoint):
    print strings._("give_this_url")
    onion_host = endpoint.address.onion_uri
    print 'http://{0}/{1}'.format(onion_host, web.slug)
    print ''
    print strings._("ctrlc_to_stop")


def validate_files(filenames):
    # validation
    valid = True
    for filename in filenames:
        if not os.path.exists(filename):
            print(strings._("not_a_file").format(filename))
            valid = False
    if not valid:
        sys.exit()


# XXX TODO move to reactor function (on shutdown)

def cleanup(self):
    global cleanup_filenames
    for filename in cleanup_filenames:
        if os.path.isfile(filename):
            os.remove(filename)
        elif os.path.isdir(filename):
            shutil.rmtree(filename)
    cleanup_filenames = []


def main():
    strings.load_strings()

    # parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--local-only', action='store_true', dest='local_only',
                        help=strings._("help_local_only"))
    parser.add_argument('--stay-open', action='store_true', dest='stay_open',
                        help=strings._("help_stay_open"))
    parser.add_argument('--debug', action='store_true', dest='debug',
                        help=strings._("help_debug"))
    parser.add_argument('filename', metavar='filename', nargs='+',
                        help=strings._('help_filename'))
    args = parser.parse_args()

    filenames = args.filename
    for i in range(len(filenames)):
        filenames[i] = os.path.abspath(filenames[i])

    local_only = bool(args.local_only)
    debug = bool(args.debug)

    # XXX honor it
    stay_open = bool(args.stay_open)

    if debug:
        # XXX add file handler
        log.startLogging(sys.stdout)

    validate_files(filenames)

    # prepare files to share
    print strings._("preparing_files")
    web.set_file_info(filenames)
    cleanup_filenames.append(web.zip_filename)

    # create the root resource
    root = OnionShare()
    onionshare_page = OnionShareDownload()
    onionshare_page.slug = web.slug
    onionshare_page.filepath = web.zip_filename
    onionshare_page.add_download_node()
    root.add_onionshare_node(onionshare_page)

    wrapped = EncodingResourceWrapper(root, [GzipEncoderFactory()])

    site = Site(wrapped)
    site.displayTracebacks = local_only

    if local_only:
        serve_local(site)
    else:
        serve_hidden(site)

    reactor.run()

if __name__ == "__main__":
    main()
