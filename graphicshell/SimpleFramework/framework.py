#!/usr/bin/env python
# -*- coding: utf-8 -*-
# COPYRIGHT: Openmoko Inc. 2009
# LICENSE: GPL Version 2 or later
# DESCRIPTION: Simple frame and dialog box framework
# AUTHOR: Christopher Hall <hsw@openmoko.com>

import sys
import types
import pygame
from pygame.locals import *
import wrap
from colour import Colour

pygame.display.init()
pygame.font.init()


class Theme:

    class Event:
        background = Colour.bisque2

    class Screen:
        background = Colour.burlywood

    class Frame:
        background = Colour.grey70
        foreground = Colour.black

    class Text:
        background = Colour.white
        foreground = Colour.blue
        size = 24
        font = None

    class Button:
        background = Colour.blue
        foreground = Colour.green

        class Text:
            size = 36

    class Dialog:
        border = Colour.black
        background = Colour.LightSkyBlue

        class Text:
            background = Colour.grey97
            foreground = Colour.DarkBlue
            size = 36
            font = None

        class Yes:
            foreground = Colour.DarkOliveGreen1
            background = Colour.DarkGreen

        class No:
            foreground = Colour.pink
            background = Colour.DarkOrange2


class EventHandler:

    # return value for event handler
    # sum the requires values
    DONE = 0
    PASS_TO_OTHERS = 1
    FLUSH_QUEUE = 2
    EXIT_HANDLER = 4

    def __init__(self, frames, retain = False):
        self.retainBackground = retain
        if isinstance(frames, types.ListType):
            self.frameList = frames
        else:
            self.frameList = [frames]

    def prepend(self, frame):
        self.frameList.insert(0, frame)

    def remove(self, frame):
        self.frameList.remove(frame)

    def refresh(self):
        doneScreen = self.retainBackground
        for frame in self.frameList:
            if not doneScreen:
                frame.drawScreen()
                doneScreen = True
            frame.draw()
        pygame.display.flip()

    def onClick(self, event):
        run = True
        for frame in self.frameList:
            r = frame.onClick(event.pos)
            if r & EventHandler.EXIT_HANDLER != 0:
                run = False
            if r & EventHandler.FLUSH_QUEUE != 0:
                pygame.event.clear()
            if r & EventHandler.PASS_TO_OTHERS == 0:
                break
        return run

    def offClick(self, event):
        run = True
        for frame in self.frameList:
            r = frame.offClick(event.pos)
            if r & EventHandler.EXIT_HANDLER != 0:
                run = False
            if r & EventHandler.FLUSH_QUEUE != 0:
                pygame.event.clear()
            if r & EventHandler.PASS_TO_OTHERS == 0:
                break
        return run

    def onDrag(self, event):
        run = True
        for frame in self.frameList:
            if event.buttons[0] == 1:
                r = frame.onDrag(event.pos)
                if r & EventHandler.EXIT_HANDLER != 0:
                    run = False
                if r & EventHandler.FLUSH_QUEUE != 0:
                    pygame.event.clear()
                if r & EventHandler.PASS_TO_OTHERS == 0:
                    break
        return run

    def run(self):
        self.refresh()
        run = True
        pygame.event.clear()
        while run:
            self.refresh()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    sys.exit(0)
                elif event.type == pygame.MOUSEMOTION:
                    run = self.onDrag(event)
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    run = self.onClick(event)
                elif event.type == pygame.MOUSEBUTTONUP:
                    run = self.offClick(event)
        self.frameList[0].drawScreen()
        pygame.display.flip()


class Screen(object):

    def __init__(self, name, width, height):
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption(name)
        self.draw()

    def draw(self):
        self.fill(Theme.Screen.background)

    def fill(self, colour):
        self.screen.fill(colour)

    def blit(self, surface, rectangle):
        self.screen.blit(surface, rectangle)

    def flip(self):
        pygame.display.flip()


class Frame(object):

    def __init__(self, name, **kwargs):

        if 'rect' in kwargs:
            (left, top, width, height) = kwargs['rect']
        else:
            raise TypeError('rect must be a 4 element tuple: (left, top, width, height)')

        self.name = name

        self.surface = pygame.Surface((width, height));
        self.rectangle = self.surface.get_rect();
        self.parent = None
        self.screen = None

        if 'parent' in kwargs:
            p = kwargs['parent']
            if isinstance(p, Screen):
                self.screen = p
            elif isinstance(p, Frame):
                self.parent = p
                self.screen = self.parent.getScreen()
            else:
                raise TypeError('parent must be a frame or screen instance')
        else:
            raise TypeError('orphaned frame')

        if self.parent != None:
            self.rectangle.left = left + self.parent.rectangle.left
            self.rectangle.top = top + self.parent.rectangle.top
            self.parent.add(self)
        else:
            self.rectangle.left = left
            self.rectangle.top = top

        self.children = []

        if 'background' in kwargs:
            self.background = kwargs['background']
        else:
            self.background = Theme.Frame.background

        if 'foreground' in kwargs:
            self.foreground = kwargs['foreground']
        else:
            self.foreground = Theme.Frame.foreground

        self.surface.fill(self.background)

    def add(self, child):
        self.children.append(child)

    def __repr__(self):
        return "Frame " + self.name + "(" + str(self.rectangle.left) + \
            ", " + str(self.rectangle.top) + \
            ", " + str(self.rectangle.width) + \
            ", " + str(self.rectangle.top) + ")"

    def onDrag(self, pos):
        t = EventHandler.PASS_TO_OTHERS
        for c in self.children:
            t = c.onDrag(pos)
            if t & EventHandler.PASS_TO_OTHERS == 0:
                break
        return t

    def onClick(self, pos):
        t = EventHandler.PASS_TO_OTHERS
        for c in self.children:
            t = c.onClick(pos)
            if t & EventHandler.PASS_TO_OTHERS == 0:
                break
        return t

    def offClick(self, pos):
        t = EventHandler.PASS_TO_OTHERS
        for c in self.children:
            t = c.offClick(pos)
            if t & EventHandler.PASS_TO_OTHERS == 0:
                break
        return t

    def draw(self):
        self.screen.blit(self.surface, self.rectangle)
        for c in self.children:
            c.draw()

    def drawScreen(self):
        self.screen.draw()

    def flip(self):
        self.screen.flip()

    def getScreen(self):
        return self.screen


class Draw(Frame):

    def __init__(self, name, **kwargs):
        Frame.__init__(self, name, **kwargs)
        self.pos = None
        self.blank = True
        if 'callback' in kwargs:
            self.callback = kwargs['callback']
        else:
            self.callback = None
        if 'callbackarg' in kwargs:
            self.callbackarg = kwargs['callbackarg']
        else:
            self.callbackarg = None

    def isBlank(self):
        return self.blank

    def onDrag(self, pos):
        t = Frame.onDrag(self, pos)
        if self.rectangle.collidepoint(pos):
            new_pos = pos[0] - self.rectangle[0], pos[1] - self.rectangle[1]
            if self.pos == None:
                self.pos = new_pos
            pygame.draw.line(self.surface, self.foreground, self.pos, new_pos)
            self.blank = False
            self.pos = new_pos
        else:
            self.pos = None
        return t

    def onClick(self, pos):
        t = Frame.onClick(self, pos)
        self.pos = None
        if t & EventHandler.PASS_TO_OTHERS != 0 and self.rectangle.collidepoint(pos):
            if self.callback != None:
                return self.callback(self.callbackarg)
            else:
                return EventHandler.DONE
        return t

    def offClick(self, pos):
        t = Frame.offClick(self, pos)
        self.pos = None
        if t & EventHandler.PASS_TO_OTHERS != 0 and self.rectangle.collidepoint(pos):
            if self.callback != None:
                return self.callback(self.callbackarg)
            else:
                return EventHandler.DONE
        return t


class Text(Frame):

    def __init__(self, text, **kwargs):

        if 'background' not in kwargs:
            kwargs['background'] = Theme.Text.background
        if 'foreground' not in kwargs:
            kwargs['foreground'] = Theme.Text.foreground

        Frame.__init__(self, "text", **kwargs)

        if 'fontsize' in kwargs:
            self.fontHeight = kwargs['fontsize']
        else:
            self.fontHeight = Theme.Text.size
        self.xOffset = 5
        self.fontWidth = self.rectangle.width - 2 * self.xOffset
        self.font = pygame.font.Font(Theme.Text.font, self.fontHeight)
        self.lineSize = self.font.get_linesize()
        self.maxLines = self.rectangle.height / self.lineSize
        self.currentLines = 0
        self.text = text
        self.tags = []
        self.offsetY = 0
        self.active = False
        self.changed = True
        self.cache = []
        self.display()

    def display(self):
        if self.changed:
            self.cache = wrap.wrap(self.text, self.font, self.fontWidth)
            self.currentLines = len(self.cache)
            self.changed = False
        self.surface.fill(self.background)
        y = self.rectangle.height
        if self.offsetY == 0:
            slice = None
        else:
            slice = -self.offsetY
        for l in reversed(self.cache[:slice]):
            y -= self.lineSize
            rendered = False
            for length, substr, fg, bg in self.tags:
                if substr == l[0:length]:
                    renderedLine = self.font.render(l, 1, fg, bg)
                    rendered = True
                    break
            if not rendered:
                renderedLine = self.font.render(l, 1, self.foreground, self.background)
            oneline = pygame.Rect(self.xOffset, y, self.fontWidth, self.fontHeight)
            self.surface.blit(renderedLine, oneline)
            if y < self.lineSize:
                break

    def addTag(self, tag, foreground, background):
        self.tags += [(len(tag), tag, foreground, background)]

    def append(self, text):
        self.text = ''.join([self.text, text])
        self.offsetY = 0
        self.changed = True
        self.display()
        # special: the next lines update the display
        self.draw()
        self.flip()

    def clear(self):
        self.text = ""
        self.changed = True
        self.display()

    def onClick(self, pos):
        if self.rectangle.collidepoint(pos):
            self.active = True
            self.pos = pos
        return EventHandler.PASS_TO_OTHERS

    def offClick(self, pos):
        if self.active:
            self.active = False
            deltaY = (self.pos[1] - pos[1]) / self.lineSize
            self.offsetY += deltaY
            if self.offsetY < 0:
                self.offsetY = 0
            elif self.offsetY > self.currentLines - self.maxLines:
                self.offsetY = self.currentLines - self.maxLines
            self.display()
        return EventHandler.PASS_TO_OTHERS


class Button(Frame):
    def __init__(self, text, **kwargs):
        if 'background' not in kwargs:
            kwargs['background'] = Theme.Button.background
        if 'foreground' not in kwargs:
            kwargs['foreground'] = Theme.Button.foreground

        Frame.__init__(self, text, **kwargs)

        self.active = False
        self.font = pygame.font.Font(None, Theme.Button.Text.size)
        self.text = text
        if 'callback' in kwargs:
            self.callback = kwargs['callback']
        else:
            self.callback = None
        if 'callbackarg' in kwargs:
            self.callbackarg = kwargs['callbackarg']
        else:
            self.callbackarg = None
        self.display()

    def onClick(self, pos):
        if self.rectangle.collidepoint(pos):
            self.active = True
            self.display()
        return EventHandler.PASS_TO_OTHERS

    def offClick(self, pos):
        if self.active:
            self.active = False
            self.display()
            if self.callback != None:
                return self.callback(self.callbackarg)
            else:
                return EventHandler.EXIT_HANDLER
        return EventHandler.PASS_TO_OTHERS

    def display(self):
        if self.active:
            self.surface.fill(self.background)
            message = self.font.render(self.text, 1, self.foreground, self.background)
        else:
            self.surface.fill(self.foreground)
            message = self.font.render(self.text, 1, self.background, self.foreground)
        r = message.get_rect()
        r.center = (self.rectangle.centerx - self.rectangle.left, self.rectangle.centery - self.rectangle.top)
        self.surface.blit(message, r)


class Dialog(Frame):

    def __init__(self, message, x, y, parent):
        self.x = x
        self.y = y
        self.width = 400
        self.height = 300
        self.state = False

        bHeight = 80
        bWidth = 120

        tWidth = self.width - 20
        tHeight = 4 * Theme.Dialog.Text.size

        self.border = 3

        xt = (self.width - tWidth) / 2
        yt = (self.height - bHeight - tHeight) / 3
        xb = (self.width - 2 * bWidth) / 3
        yb = self.height - yt - bHeight

        Frame.__init__(self, "dialog", rect = (self.x, self.y, self.width, self.height), \
                           parent = parent, \
                           background = Theme.Dialog.border)
        self.internal = Frame("bk", \
                                  rect = (self.border, self.border, \
                                              self.width - 2  * self.border, self.height - 2  * self.border), \
                                  parent = self, background = Theme.Dialog.background)
        self.text = Text(message, rect = (xt, yt, tWidth, tHeight), parent = self.internal, \
                              foreground = Theme.Dialog.Text.foreground, background = Theme.Dialog.Text.background)

        self.yes = Button("YES", rect = (xb, yb, bWidth, bHeight), \
                              parent = self.internal, \
                              callback = self.setState, callbackarg = True, \
                              foreground = Theme.Dialog.Yes.foreground, background = Theme.Dialog.Yes.background)
        self.no = Button("NO", rect = (self.width - xb - bWidth, yb, bWidth, bHeight), \
                             parent = self.internal, \
                             callback = self.setState, callbackarg = False, \
                             foreground = Theme.Dialog.No.foreground, background = Theme.Dialog.No.background)

    def setState(self, state):
        self.state = state
        return EventHandler.EXIT_HANDLER

    def set(self, text):
        self.text.clear()
        self.text.append(text)


    def run(self):
        save = self.screen.screen.copy()
        self.draw()
        self.screen.flip()
        pygame.event.clear()
        EventHandler(self, True).run()
        self.screen.blit(save, save.get_rect())
        self.screen.flip()


# main program

if __name__ == '__main__':

    def cb1(arg):
        t.append(" and a bit less text")
        return False

    def cb2(arg):
        t.append(" more text and more text")
        return False

    def cbz(arg):
        t.clear()
        return False

    def cbx(arg):
        print "callback - NOP"
        return False

    def cbd(arg):
        d.run()
        return False

    width, height = 480, 640
    s = Screen("Test for Framework", width, height)

    d = Dialog("Please answer", 50, 100, parent = s)

    d.run()

    x = Frame("x", rect = (0, 0, 320, 240), parent = s, background = Colour.grey40)
    y = Frame("y", rect = (20, 20, 200, 150), parent = x, background = Colour.yellow)

    z0 = Button("z0", rect = (10, 10, 60, 50), parent = y, callback = cbz)
    z1 = Button("z1", rect = (90, 10, 60, 50), parent = y, callback = cb1)
    z2 = Button("z2", rect = (10, 90, 60, 50), parent = y, callback = cb2, foreground = Colour.green)
    z3 = Text("text", rect = (100, 100, 75, 25), parent = y)

    aa1 = Button("EXIT", rect = (300, 50, 140, 100), parent = x, foreground = Colour.white, background = Colour.red)

    aq1 = Button("ABCDEF", rect = (40, 200, 110, 100), parent = x, callback = cbx, foreground = Colour.white, background = Colour.red)
    aq2 = Button("ABCDEF", rect = (170, 200, 110, 100), parent = x, callback = cbx, foreground = Colour.white, background = Colour.green)
    aq3 = Button("ABCDEF", rect = (300, 200, 110, 100), parent = x, callback = cbx, foreground = Colour.white, background = Colour.blue)

    bt99 = Button("dialog", rect = (100, 320, 110, 100), parent = x, callback = cbd, foreground = Colour.white, background = Colour.blue)

    tOffset = 10
    tWidth = width - 2 * tOffset
    tHeight = 8 * Theme.Text.size
    tVertical = height - tHeight - 10
    t = Text("text 1\ntext 2\ntext 3\ntext 4\n", \
                 fontsize = 20, \
                 parent = s, \
                 rect = (tOffset, tVertical, tWidth, tHeight))

    EventHandler([x, t]).run()
