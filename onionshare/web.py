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
# REFACTOR IN PROGRESS --------------------------------------------
# (see onionshare.py)
# -----------------------------------------------------------------

import os

from twisted.web.template import Element, renderer, XMLFile, tags
from twisted.python.filepath import FilePath

import helpers
from strings import _

filesize_human = lambda i: helpers.human_readable_filesize(float(i))

static = os.path.abspath("./static")

# information about the file
file_info = []
zip_filename = None
zip_filesize = None

get_filename = lambda name: os.path.basename(name).decode("utf-8")


def set_file_info(filenames):
    global file_info, zip_filename, zip_filesize

    # build file info list
    file_info = {'files': [], 'dirs': []}
    for filename in filenames:
        info = {
            'filename': filename,
            'basename': os.path.basename(filename)
        }
        if os.path.isfile(filename):
            info['size'] = os.path.getsize(filename)
            info['size_human'] = helpers.human_readable_filesize(info['size'])
            file_info['files'].append(info)
        if os.path.isdir(filename):
            info['size'] = helpers.dir_size(filename)
            info['size_human'] = helpers.human_readable_filesize(info['size'])
            file_info['dirs'].append(info)
    file_info['files'] = sorted(
        file_info['files'], key=lambda k: k['basename'])
    file_info['dirs'] = sorted(
        file_info['dirs'], key=lambda k: k['basename'])

    # zip up the files and folders
    z = helpers.ZipWriter()
    for info in file_info['files']:
        z.add_file(info['filename'])
    for info in file_info['dirs']:
        z.add_dir(info['filename'])
    z.close()
    zip_filename = z.zip_filename
    zip_filesize = os.path.getsize(zip_filename)


slug = helpers.random_string(16)
download_count = 0


class OnionSharePageHtml(Element):

    loader = XMLFile(FilePath(os.path.join(
        static, 'index.xhtml')))

    def __init__(self, *args, **kwargs):
        self.slug = kwargs.pop("slug", None)
        Element.__init__(self, *args, **kwargs)

    @renderer
    def css(self, request, tag):
        # XXX remove bogus <script> tag
        with open(os.path.join(static, "onionshare.css")) as f:
            css = f.read()
        return tag(css, tags.script(type_="text/css"))

    @renderer
    def file_meta(self, request, tag):
        filename = get_filename(zip_filename)
        tag.fillSlots(filename=filename,
                      filesize=filesize_human(zip_filesize))
        return tag

    @renderer
    def meta_filesize(self, request, tag):
        return tag(tags.meta(
            name="onionshare-filesize",
            content=filesize_human(zip_filesize)))

    @renderer
    def download_link(self, request, tag):
        button_text = u"{filename} ▼ :"
        filename = get_filename(zip_filename)
        return tag(tags.a(button_text.format(
            filename=filename), href="/{slug}/download".format(
                slug=self.slug),
            class_="button"))

    @renderer
    def filename(self, request, tag):
        return tag(tags.p(zip_filename), id='filename')

    @renderer
    def download_size(self, request, tag):
        tag.fillSlots(p_size_class="download-size",
                      size_str="%s :" % _("download_size"))
        return tag

    @renderer
    def filesize_human(self, request, tag):
        tag.fillSlots(filesize_human_title="filesyze bytes",
                      filesize_human=filesize_human(zip_filesize))
        return tag

    @renderer
    def file_table_header(self, request, tag):
        tag.fillSlots(filename_str=_("filename"),
                      filesize_str=_("size"))
        return tag

    @renderer
    def file_info_table_dir_entries(self, request, tag):
        for info in file_info['dirs']:
            yield tag.clone().fillSlots(
                basename=info["basename"],
                size=info["size_human"])

    @renderer
    def file_info_table_file_entries(self, request, tag):
        for info in file_info['files']:
            yield tag.clone().fillSlots(
                basename=info["basename"],
                size=info["size_human"])
