
import time
from collections import deque

import pygame
from pygame.locals import *


def main():
    size = (1024, 600)
    pygame.init()
    pygame.font.init()
    pygame.display.set_caption("splitvent")
    screen = pygame.display.set_mode(size)
    bg = pygame.Surface(size)
    bg.fill(pygame.Color('#000000'))
    font = pygame.font.SysFont("menlottc", 144)
    print(font)
    n = 0
    running = True
    times = deque(maxlen=10)
    times.append(0.0)
    while running:
        times.append(time.time())
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
              running = false
        screen.blit(bg, (0,0))
        fps = (len(times) - 1) / (times[-1] - times[0])
        textsurf = font.render("{:10.1f}".format(fps), True, (255,255,255), (0,0,0))
        screen.blit(textsurf, (0,0))
        pygame.display.update()
        n = n + 1
    pygame.quit()


if __name__=="__main__":
    main()
