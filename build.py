# -*- coding: utf-8 -*-

# pip install csscompressor
# pip install jsmin

'''
1. Read `config.json` file. It describe project: 
	- order of .css files
	- order of .js files
	- names of `images` folders

2. Join, minify and put to `dist` .min.js and .min.css files with name cointains EPOCH stamp. 
	These files have to be pointed in config with path relative to `css`/`js` directory

3. Copy all folders from `src` to `dist`. For `css` and `js` folders remove files, which pointed as dependencies.

4. Parse .html files, recoginize `tmpl`'es. Insert parameters into templates. Include these templates in .html files

5. Include minified .css and .js files in appropriate place in html files
	${{CSSSTYLE}}$
	${{JAVASCRIPT}}$

6. Add EPOCH timestamp to image files, replace links to these files in all .html files


Assumptions:
Root of project contains .html files and folders. No other files in root except .html files.
There is special kinds of folders: `css`, `js`, and list of `image` folders.
'''

import json
import time
import sys
import os
import os.path
import shutil
import codecs

from csscompressor import compress
from jsmin import jsmin
from os.path import join as pjoin


config_file = "some predefined place..."
if len(sys.argv) == 2:
    config_file = sys.argv[1]

'''
ap = absolute path
rp = relative path
fn = file name
fc = file content
ext = file extention
hd = file after some processing
'''

BASE_DIR = os.path.dirname(config_file)
SRC_DIR = pjoin(BASE_DIR, "src")
DIST_DIR = pjoin(BASE_DIR, "dist")

CSS_PH = "${{CSSSTYLE}}$"
JS_PH = "${{JAVASCRIPT}}$"
CSS_EXT = ".css"
JS_EXT = ".js"
LS = "\r\n"
TS = int(time.time())

OPEN_TAG = "<!--{*"
CLOSE_TAG = "*}-->"

CSS_FN = pjoin(DIST_DIR, "css", "style" + str(TS) + ".min.css")
JS_FN = pjoin(DIST_DIR, "js", "style" + str(TS) + ".min.js")

def f_read(filename):
	return codecs.open(filename, "r", encoding='utf-8').read()

def f_write(filename, content):
	with codecs.open(filename, "w+", encoding='utf-8') as file:
		file.write(content)

def minify(filename, func):
	if os.path.exists(filename):
		if "min" in os.path.basename(filename):
			return f_read(filename)
		else:
			return func(f_read(filename))
	else:
		return ""

def minify_css(x1, x2): 
	return x1 \
		+ LS \
		+ LS \
		+ minify(pjoin(SRC_DIR, "css", x2 + CSS_EXT), compress)

def minify_js(x1, x2): 
	return x1 \
		+ LS \
		+ LS \
		+ minify(pjoin(SRC_DIR, "js", x2 + JS_EXT), jsmin)

class Templater:
	def __init__(self, html_fns, templates):
		self.html_fns = html_fns
		self.templates = templates

	def find_tags(self, fc, open_tag, close_tag):
		index = 0
		result = []
		while index < len(fc):
			hit = fc.find(open_tag, index)
			if hit == -1:
				index = len(fc) + 1
			else:
				hit2 = fc.find(close_tag, hit + len(open_tag))
				hit3 = fc.find(open_tag, hit + len(open_tag))
				if hit2 == -1:
					raise "Closed tag not found"
				if (not hit3 == -1) and hit3 < hit2:
					raise "Incorrect syntax"

				tag_content = fc[hit + len(open_tag):hit2].strip()
				result.append(
					{"begin": hit, \
					"end": hit2 + len(close_tag), \
					"content": tag_content \
					})
				index = hit2 + len(close_tag)

		return result

	def replace_variables(self, fc, vals):
		fc_copy = fc
		for k in vals.keys():
			fc_copy = fc_copy.replace("${" + k + "}$", vals[k])

		index = 0
		index2 = 0
		fc_copy2 = ""
		open_tag = "${::isset::"
		close_tag = "::}$"
		delimeter = "::"
		while index < len(fc_copy):
			hit = fc_copy.find(open_tag, index)
			if hit == -1:
				index = len(fc_copy) + 1
			else:
				hit2 = fc_copy.find(close_tag, hit + len(open_tag))
				hit3 = fc_copy.find(open_tag, hit + len(open_tag))
				if hit2 == -1:
					raise "Closed tag not found"
				if (not hit3 == -1) and hit3 < hit2:
					raise "Incorrect syntax, open tag before closed tag"

				tag_content = fc_copy[hit + len(open_tag):hit2].strip()

				d_pos = tag_content.find(delimeter)
				if (d_pos == -1):
					raise "Incorrect syntax, couldn't find delimeter"

				tag_var = tag_content[:d_pos]
				tag_value = tag_content[d_pos + len(delimeter):]

				fc_copy2 = fc_copy2 \
					+ fc_copy[index:hit] \
					+ (tag_value if tag_var in vals.keys() else "")
				
				index = hit2 + len(close_tag)
				index2 = index

		return fc_copy2 + fc_copy[index2:]

	def sort_key(self, elem):
		return elem["begin"]

	def template_html(self, fn):
		html_fc = f_read(pjoin(SRC_DIR, fn))

		tags = self.find_tags(html_fc, OPEN_TAG, CLOSE_TAG)
		tags.sort(key=self.sort_key)

		result = ""
		prev = 0
		for tag in tags:
			jtag = json.loads(tag["content"])
			tmpl_name = jtag["name"]
			tmpl_params = jtag["params"]
			tmpl_value = self.replace_variables(self.templates[tmpl_name], tmpl_params)

			result = result + html_fc[prev:tag["begin"]] + tmpl_value
			prev = tag["end"]

		return result + html_fc[prev:]

	def template(self):
		result = {}
		for html_fn in self.html_fns:
			result[html_fn] = self.template_html(html_fn)
		return result

	pass # Templater

class ImageHandler:
	def __init__(self, base_ap, image_fns, timestamp):
		self.base_ap = base_ap
		self.image_fns = image_fns
		self.timestamp = timestamp
		self.images = {}

		for image_fn in self.image_fns:
			self.process_images(pjoin(self.base_ap, image_fn))

	def process_images(self, root):
		files = os.listdir(root)
		for name in files:
			file = pjoin(root, name)
			if os.path.isdir(file):
				self.process_images(file)
			else:
				rel_fp = os.path.relpath(file, self.base_ap)
				self.images[rel_fp] = self.ts_file(rel_fp)
				os.rename(file, self.ts_file(file))

	def ts_file(self, file):
		filename, file_extension = os.path.splitext(file)
		return filename + "_" + str(self.timestamp) + file_extension

	def process(self, content):
		result = content
		for ip in self.images.keys():
			result = result.replace(ip, self.images[ip])
		return result

	pass # ImageHandler


# read config
config_fc = json.loads(f_read(config_file))

# clean the target directory
shutil.rmtree(DIST_DIR)
os.mkdir(DIST_DIR)

# copy directories & accumulate .html files names
html_fns = []
for fn in os.listdir(SRC_DIR):
	ap = pjoin(SRC_DIR, fn)
	if os.path.isdir(ap):
		shutil.copytree(ap, pjoin(DIST_DIR, fn))	
	else:
		assert ".html" in fn
		html_fns.append(fn)

# handle images
ih = ImageHandler(DIST_DIR, config_fc["images"], TS)

# minify and write css & js files
css_hd = reduce(minify_css, config_fc["dependencies"]["css"], "")
js_hd = reduce(minify_js, config_fc["dependencies"]["js"], "")

for fp in config_fc["dependencies"]["css"]:
	os.remove(pjoin(DIST_DIR, "css", fp + CSS_EXT))

for fp in config_fc["dependencies"]["js"]:
	os.remove(pjoin(DIST_DIR, "js", fp + JS_EXT))

f_write(CSS_FN, ih.process(css_hd))
f_write(JS_FN, ih.process(js_hd))

# read templates
templates = {}
for tname in os.listdir(pjoin(BASE_DIR, "tmpl")):
	ap_tmpl = pjoin(BASE_DIR, "tmpl", tname)
	templates[tname] = f_read(ap_tmpl)

# include templates into .html files
html_hds = Templater(html_fns, templates).template()

# store .html files to `dist` directory
for html_fn in html_hds.keys():
	html_ap = pjoin(DIST_DIR, html_fn)
	html_fc = ih.process(html_hds[html_fn])
	html_fc = html_fc.replace(CSS_PH, os.path.basename(CSS_FN))
	html_fc = html_fc.replace(JS_PH, os.path.basename(JS_FN))
	f_write(html_ap, html_fc)
