#!/usr/bin/env python3

import sys, random

def movecursor(x, y):
    print( "\x1b[%d;%df" % (y, x) , flush=False, end='' )

def paint_frames(frames):

    max_x = 0
    max_y = 0
    for fr in frames:
        xp = fr[0] + fr[2]
        yp = fr[1] + fr[3]
        if xp > max_x:
            max_x = xp
        if yp > max_y:
            max_y = yp

    printed = [[0 for x in range(max_x)] for y in range(max_y)]

    # Lines
    for fr in frames:
        chars = ("═", "║")

        # Horiz
        movecursor( fr[0]+1, fr[1] )

        print( chars[0] * (fr[2]-2), flush=False, end='' )
        #for i in range(fr[2]-2):

        movecursor( fr[0]+1, fr[1] + fr[3]-1 )
        print( chars[0] * (fr[2]-2), flush=False, end='' )

        # Vert
        for i in range(0, fr[3]-2):
            movecursor(fr[0], fr[1]+i+1)
            print(chars[1], flush=False, end='')
        for i in range(0, fr[3]-2):
            movecursor(fr[0]+fr[2]-1, fr[1]+i+1)
            print(chars[1], flush=False, end='')

        # Set printed
        for i in range(0, fr[3]):
            printed[fr[1]+i][fr[0]] = 1
            printed[fr[1]+i][fr[0]+fr[2]-1] = 1

        for i in range(0, fr[2]):
            printed[fr[1]][fr[0]+i] = 1
            printed[fr[1]+fr[3]-1][fr[0]+i] = 1

    # Corners
    for fr in frames:
        chars = ("╔", "╗", "╚", "╝", "╦", "╩", "╠", "╣", "╬")

        coords = [
            [fr[0], fr[1]],
            [fr[0]+fr[2]-1, fr[1]],
            [fr[0], fr[1]+fr[3]-1],
            [fr[0]+fr[2]-1, fr[1]+fr[3]-1],
        ]

        for c in coords:
            movecursor( c[0], c[1] )
            xp = printed[c[1]][c[0]+1] == 1 if c[0] != max_x-1 else False
            xn = printed[c[1]][c[0]-1] == 1 if c[0] != 0 else False
            yp = printed[c[1]+1][c[0]] == 1 if c[1] != max_y-1 else False
            yn = printed[c[1]-1][c[0]] == 1 if c[1] != 0 else False

            if xn and xp and yn and yp:
                print(chars[8], flush=False, end='')
            elif xn and xp and yn:
                print(chars[5], flush=False, end='')
            elif xn and xp and yp:
                print(chars[4], flush=False, end='')
            elif xn and yn and yp:
                print(chars[7], flush=False, end='')
            elif xp and yn and yp:
                print(chars[6], flush=False, end='')
            elif xp and yp:
                print(chars[0], flush=False, end='')
            elif xp and yn:
                print(chars[2], flush=False, end='')
            elif xn and yp:
                print(chars[1], flush=False, end='')
            elif xn and yn:
                print(chars[3], flush=False, end='')

    # Titles
    for fr in frames:
        movecursor( fr[0]+2, fr[1] )

        if fr[5] == 3:
            print("\x1b[31;1m", flush=False, end='')
        if fr[5] == 2:
            print("\x1b[33;1m", flush=False, end='')
        if fr[5] == 1:
            print("\x1b[32;1m", flush=False, end='')

        print(fr[4], flush=False, end='')
        print("\x1b[0m", flush=False, end='')


def candlechart(x, y, w, h, values):
    # Get max/min range of input values
    vmax_in = max(values)
    vmin_in = min(values)
    deltav_in = (vmax_in - vmin_in) / h

    # Add in some margins
    vmax = vmax_in + deltav_in * 2
    vmin = vmin_in - deltav_in * 2
    deltav = (vmax - vmin) / h


    def v_to_y(v):
        return (v - vmin) / deltav

    def y_to_v(y):
        return vmin + deltav * y

    for yp in range(h):
        vp = y_to_v(yp)
        movecursor( x, y+h-1-int(yp) )
        print( f"{vp:.1f}", flush=False, end='' )

    nw = len(values) if len(values) < w else w
    values = values[-nw:]
    dx = 2
    for vi, val in enumerate(values):
        if vi == 0:
            continue

        yp = int(v_to_y(val))
        ypp = int(v_to_y(values[vi-1]))

        if yp == ypp:
            print("\x1b[37;1m", flush=False, end='')
            movecursor( x+vi+dx, y+h-1-yp )
            print( "—", flush=False, end='' )
        elif yp > ypp:
            print("\x1b[32;1m", flush=False, end='')
            for i in range(ypp, yp):
                movecursor( x+vi+dx, y+h-1-i )
                print( "█", flush=False, end='' )
        elif ypp > yp:
            print("\x1b[31;1m", flush=False, end='')
            for i in range(yp, ypp):
                movecursor( x+vi+dx, y+h-1-i )
                print( "█", flush=False, end='' )

        print("\x1b[0m", flush=False, end='')
        # if ypp != yp:
        #     rnd = random.randint(0, 2)
        #     for i in range(rnd):
        #         yc = y+h-1-max(yp,ypp)-i
        #         if yc > y-1:
        #             movecursor( x+vi+dx, yc )
        #             print( "│", flush=False, end='' )

        #     yc = y+h-1-max(yp,ypp)-rnd
        #     if yc > y-1:
        #         movecursor( x+vi+dx, yc )
        #         print( "┬", flush=False, end='' )

        #     rnd = random.randint(0, 5)
        #     for i in range(rnd):
        #         yc = y+h-min(yp,ypp)+i
        #         if yc < y+h:
        #             movecursor( x+vi+dx, yc )
        #             print( "│", flush=False, end='' )

        #     yc = y+h-min(yp,ypp)+rnd
        #     if yc < y+h:
        #         movecursor( x+vi+dx, yc )
        #         print( "┴", flush=False, end='' )
        #
def chart_in_box(x, y, w, h, stonk, stonk_name, frame_color=0):
    candlechart(x, y, w, h, stonk)
    paint_frames([[x-1,y-1,w+3,h+2, stonk_name, frame_color]])

# candledata = (5, 6, 8, 3, 6, 1, 2, 1, 5, 6, 9, 8, 9, 3, 4, 8, 3, 1, 7, 6, 5, 3, 2, 1, 4, 3, 5, 4, 7, 8, 7, 7, 6, 3, 4, 3, 5, 3, 2, 7, 6, 4, 3, 6, 7, 9, 6, 4, 6, 3, 4, 8, 7)
# candledata = (1, 5, 6, 7, 3, 2)


#framedata = (
#    (2, 2, 50, 30, "Stonks 0", 1),
#    (51, 2, 50, 50, "Stonks 1", 1),
#)
#paint_frames(framedata)

#candlechart(3, 3, 48, 28, 10, candledata)
#candlechart(52, 3, 48, 48, 10, candledata)

# movecursor( 0, 33 )
# sys.stdout.flush()
