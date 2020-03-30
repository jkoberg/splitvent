
import time, math
from collections import deque

import pygame
from pygame.locals import *


def main():
    size = (1024, 600)
    width, height = size
    graphfrac = 0.80
    pygame.init()
    pygame.font.init()
    pygame.display.set_caption("splitvent")
    screen = pygame.display.set_mode(size)
    bg = pygame.Surface(size)
    bg.fill(pygame.Color('#000000'))
    font = pygame.font.SysFont("menlottc", 30)
    print(font)
    n = 0
    running = True
    times = deque(maxlen=10)
    times.append(0.0)
    datapoints = deque(maxlen=width)
    while running:
        times.append(time.time())
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
              running = false
        screen.blit(bg, (0,0))
        x = (n % 120) / 120.0
        datavalue = math.sin(2 * math.pi * x)
        datapoints.append(0.5 * graphfrac * height * datavalue)
        y0 = height / 2
        pointlist = list((n,y+y0) for n,y in enumerate(datapoints))
        if len(datapoints) > 2:
            pygame.draw.lines(screen, (127,255,255), False, pointlist, 3)
        fps = (len(times) - 1) / (times[-1] - times[0])
        textsurf = font.render(
            "{:4.0f} fps n={:10d}  {:10.2f}"
                .format(fps, n, datavalue),
            True,
            (255,255,255),
            (0,0,0)
        )
        screen.blit(textsurf, (0,0))

        
        pygame.display.update()
        n = n + 1
    pygame.quit()


if __name__=="__main__":
    main()
