# -*- coding: utf-8 -*-
# Module: default
# Author: jurialmunkey
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html
import os
import re
import sys
import xbmc
import xbmcaddon
import xbmcvfs
from PIL import Image, ImageChops

ADDON = xbmcaddon.Addon('script.texturemaker')
ADDONPATH = ADDON.getAddonInfo('path')
ADDONDATA = 'special://profile/addon_data/script.texturemaker/'

GRADIENT = xbmcvfs.translatePath('{}/resources/images/gradient.png'.format(ADDONPATH))
SETTINGS = ['fg', 'bg', 'alpha', 'folder', 'reload', 'no_reload']


""" Usage
RunScript(script.texturemaker, fg=ffffffff, bg=ffffffff, alpha=1.0, folder=folder, mask_name=mask_file)

Output:
special://profile/addon_data/script.texturemaker/{folder}/{file}

gradient_h.png      = Horizontal gradient from fg to bg with alpha applied to fg
gradient_v.png      = gradient_h rotated 90 degrees
{mask_name}_h.png   = gradient_h with {mask_file} applied as mask
{mask_name}_v.png   = gradient_v with {mask_file} applied as mask

mask_name+multiply  = apply {mask_file} using multiply
mask_name+overlay   = layer "overlay_{mask_file}" on top of file
mask_name+padding{x|x|x|x} = apply transparent padding from edge (left, top, right, bottom)
mask_name+slicing{edge|x} = slice image x pixels from edge

"""


def get_params():
    params = {}
    for arg in sys.argv:
        if arg == 'script.py':
            pass
        elif '=' in arg:
            arg_split = arg.split('=', 1)
            if arg_split[0] and arg_split[1]:
                key, value = arg_split
                params.setdefault(key, value)
        else:
            params.setdefault(arg, True)
    return params


def make_gradient(fg_color='#ffff00', bg_color='red', alpha=0.8, gradient=GRADIENT):
    # Open base image
    og_img = Image.open(gradient)

    # Apply alpha adjustment
    og_img.putalpha(og_img.getchannel('A').point(lambda x: int(x * alpha)))

    # Apply colordiffuse
    fg_img = Image.new('RGBA', og_img.size, color=fg_color)
    fg_img.putalpha(og_img.getchannel('A'))

    # Layer over base color
    bg_img = Image.new('RGBA', og_img.size, color=bg_color)
    bg_img.paste(fg_img, (0, 0), fg_img)
    return bg_img


def make_padded(base, left, top, right, bottom):
    width, height = base.size
    new_width = width + right + left
    new_height = height + top + bottom
    result = Image.new(base.mode, (new_width, new_height))
    result.paste(base, (left, top))
    return result


def make_slices(base, edge, pixels):
    width, height = base.size
    if edge == 'left':
        bb_x = (0, 0, pixels, height)
        bb_y = (pixels, 0, width, height)
    elif edge == 'right':
        bb_x = (0, 0, width - pixels, height)
        bb_y = (width - pixels, 0, width, height)
    return (base.crop(bb_x), base.crop(bb_y))


def make_masked(base, mask, multiply=False, overlay=False, padding=None):
    # Open mask image
    mk_img = Image.open(mask)

    # Resize base gradient image to the size of the mask for quick processing
    og_img = base.resize(mk_img.size)

    # Copy mask alpha channel to base to apply transparency mask
    og_img.putalpha(mk_img.getchannel('A'))

    # Multiply base by mask to apply brightness mask (white=unaffected;grey=darken)
    if multiply:
        og_img = ImageChops.multiply(og_img, mk_img)

    # Overlay on top of image
    if overlay:
        fg_img = Image.open('{}_overlay{}'.format(mask[:-4], mask[-4:]))
        og_img = Image.alpha_composite(og_img, fg_img)

    # Padding added to canvas
    if padding:
        og_img = make_padded(og_img, *padding)

    return og_img


class Script(object):
    def __init__(self):
        self.params = get_params()
        self.save_dir = '{}/{}'.format(ADDONDATA, self.params.get('folder', 'default'))
        self.fg_color = '#{}'.format(self.params.get('fg', 'ffffffff')[2:])
        self.bg_color = '#{}'.format(self.params.get('bg', 'ffffffff')[2:])
        self.alpha = float(self.params.get('alpha', 1.0))

    def make_gradients(self, fg_color, bg_color, alpha):
        self.gradient_h = make_gradient(fg_color, bg_color, alpha)
        self.gradient_h_file = xbmcvfs.translatePath('{}/gradient_h.png'.format(self.save_dir))
        self.gradient_h.save(self.gradient_h_file)

        self.gradient_v = self.gradient_h.rotate(90, expand=True)
        self.gradient_v_file = xbmcvfs.translatePath('{}/gradient_v.png'.format(self.save_dir))
        self.gradient_v.save(self.gradient_v_file)

    def run(self):
        if not os.path.exists(xbmcvfs.translatePath(self.save_dir)):
            os.makedirs(xbmcvfs.translatePath(self.save_dir))

        self.make_gradients(self.fg_color, self.bg_color, self.alpha)

        for k, v in self.params.items():
            if k in SETTINGS:
                continue

            # Get multiply keyword
            multiply = True if '+multiply' in k else False
            k = k.replace('+multiply', '')

            # Get overlay keyword
            overlay = True if '+overlay' in k else False
            k = k.replace('+overlay', '')

            # Get padded keyword
            r = re.search(r'\+padding\{(.*?)\}', k)
            k, padding = (k.replace(r.group(0), ''), [int(i) for i in r.group(1).split('|')]) if r else (k, None)

            # Get slicing keyword
            r = re.search(r'\+slicing\{(.*?)\}', k)
            k, slicing = (k.replace(r.group(0), ''), r.group(1).split('|')) if r else (k, None)

            # Create masked images
            mask = xbmcvfs.translatePath(v)
            for i, j in [('h', self.gradient_h), ('v', self.gradient_v)]:
                mask_file = xbmcvfs.translatePath(f'{self.save_dir}/{k}_{i}')
                mask_img = make_masked(j, mask, multiply=multiply, overlay=overlay, padding=padding)
                mask_img.save(f'{mask_file}.png')
                if not slicing:
                    continue
                sliced_img_x, sliced_img_y = make_slices(mask_img, slicing[0], int(slicing[1]))
                sliced_img_x.save(f'{mask_file}_x.png')
                sliced_img_y.save(f'{mask_file}_y.png')

        if 'no_reload' not in self.params:
            xbmc.executebuiltin('ReloadSkin()')
        if 'reload' in self.params:
            xbmc.executebuiltin('ActivateWindow({})'.format(self.params['reload']))
