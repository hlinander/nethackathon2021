import curses
import re
from curses import wrapper
import session
import db
import jens
import os
import json
import datetime
import sys
import time
import readchar

INC_EXPIRY = 50
MIN_EXPIRY = 100
MAX_EXPIRY = 1000

my_id = '0'

state = 0
total_gems = 0
no_color = None
avanza_logo = None
white = None
focused_item = None
stat_color = None
red = None
yellow = None
green = None
list_name = None
selected_item = None
invest = False

expiry = MIN_EXPIRY
buy_long = True
cost = 0

selected_player_id = None

def get_full_name(p):
    return '%s - %s' % (p['player_ticker'], p['player_name'])

def item_color(s):
    if state < s:
        return white
    elif state == s:
        return focused_item
    return selected_item

def update(stdscr, cpstate, player_order):
    global selected_player_id
    global cost
    global total_gems
    total_gems = db.get_clan(my_id).power_gems

    player_index = 0
    full_name = get_full_name(cpstate[str(selected_player_id)])
    top = '╔═╣ ' + full_name + ' ╠' + ('═' * (38 + (16 - len(full_name)))) + '╦═╣ Stonks ╠═══════╗'
    stdscr.addstr(0, 0, top)
    row = '║                                                           ║                  ║'
    y = 1
    while y < 20:
        stdscr.addstr(y, 0, row)
        if player_index < len(player_order):
            if my_id == player_order[player_index]:
                player_index += 1
                continue
            player_id = player_order[player_index]
            player = cpstate[str(player_id)]
            full_name = get_full_name(player)
            cost = db.get_stonk(int(selected_player_id), "stonk").value
            if selected_player_id == player_id:
                stdscr.addstr(y, 61, ' ' + full_name + (' ' * (17 - len(full_name))), item_color(0))
                y += 1
                stdscr.addstr(y, 0, row)
                stdscr.addstr(y, 64, 'HP: ', stat_color)
                hp_color = green
                if player['hp'] < player['hpmax']/3:
                    hp_color = red
                elif player['hp'] < ((player['hpmax']/3)*2):
                    hp_color = yellow
                stdscr.addstr(str(player['hp']), hp_color)
                stdscr.addstr('/')
                stdscr.addstr(str(player['hpmax']))
                y += 1
                stdscr.addstr(y, 0, row)
                stdscr.addstr(y, 62, 'TURN: ', stat_color)
                stdscr.addstr(y, 68, str(player['last_turn']))
                y += 1
                stdscr.addstr(y, 0, row)
                stdscr.addstr(y, 62, 'DLVL: ', stat_color)
                stdscr.addstr(y, 68, str(player['dlevel']))
                y += 1
                stdscr.addstr(y, 0, row)
                stdscr.addstr(y, 61, '──────────────────', stat_color)
            else:
                stdscr.addstr(y, 61, ' ' + full_name + (' ' * (17 - len(full_name))), list_name)
            player_index += 1
        y += 1
    stdscr.addstr(y+0, 0, '╠═╣ ')
    stdscr.addstr('$$$', yellow)
    stdscr.addstr(' Make Investment ', white)
    stdscr.addstr('$$$', yellow)
    stdscr.addstr(' ╠═══════════════════════════════╩══════════════════╣')
    stdscr.addstr(y+1, 0, '║                                                                              ║')
    stdscr.addstr(y+2, 0, '║ ')
    stdscr.addstr('Expiry: ', stat_color)
    stdscr.addstr('%4d' % (expiry), item_color(1))
    stdscr.addstr('      [')
    stdscr.addstr('X' if buy_long else ' ', item_color(2) if buy_long else white)
    stdscr.addstr('] ')
    stdscr.addstr('Long', stat_color)
    stdscr.addstr('  [')
    stdscr.addstr('X' if not buy_long else ' ', item_color(2) if not buy_long else white)
    stdscr.addstr('] ')
    stdscr.addstr('Short', stat_color)
    stdscr.addstr('      Cost: ', stat_color)
    stdscr.addstr('% 5d/% 5d' % (cost, total_gems))
    stdscr.addstr('      ')
    stdscr.addstr('   BUY   ', stat_color | curses.A_REVERSE if state < 3 else item_color(3))
    stdscr.addstr('  ║')
    # '10000 T                                                              ║')
    stdscr.addstr(y+3, 0, '║                                                                              ║')
    stdscr.addstr(y+4, 0, '╚════════════════════════════════╣ ')
    stdscr.addstr("Press 'q' go back (and ultimately quit)", stat_color)
    stdscr.addstr(' ╠══╝')
    stdscr.insstr(y+4, 2, "═")

    stank = db.get_stonk_series(int(selected_player_id), "stonk", 100, datetime.datetime.utcnow() - datetime.timedelta(minutes=5), datetime.datetime.utcnow())
    jens.candlechart(stdscr, 1, 1, 57, 19, stank, (green, red))

    if state == 4:
        if cost <= (total_gems + 500):
            # ("═", "║", "╔", "╗", "╚", "╝", "╦", "╩", "╠", "╣", "╬")
            stdscr.addstr(8, 3, '╔═╣ Confirm Investment ╠══════════════════════════════════════════════════╗')
            stdscr.addstr(9, 3, '║                                                                         ║')
            stdscr.addstr(10, 3, '║                                                                         ║')
            stdscr.addstr(10, 3, '║ You selected ')
            stdscr.addstr('long' if buy_long else 'short', green if buy_long else red)
            stdscr.addstr(' in ')
            stdscr.addstr(get_full_name(cpstate[str(selected_player_id)]), green)
            stdscr.addstr(' with an expiry in ')
            stdscr.addstr('%d' % (expiry), stat_color)
            stdscr.addstr(' turns.')
            stdscr.addstr(11, 3, '║                                                                         ║')
            stdscr.addstr(12, 3, '║ Invest ')
            stdscr.addstr(str(cost), yellow)
            stdscr.addstr(' of total ')
            stdscr.addstr(str(total_gems), yellow)
            stdscr.addstr(' Power Gems?')
            stdscr.addstr(' ' * (35 - len(str(cost)) + len(str(total_gems))))
            stdscr.addstr('║')
            stdscr.addstr(13, 3, '║                                                                         ║')
            stdscr.addstr(14, 3, '║                                                                         ║')
            stdscr.addstr(15, 3, '║ Press ')
            stdscr.addstr('SPACE', green)
            stdscr.addstr(' to confirm, or ')
            stdscr.addstr('q', red | curses.A_REVERSE)
            stdscr.addstr(' to cancel.                                 ║')
            stdscr.addstr(16, 3, '║                                                                         ║')
            stdscr.addstr(17, 3, '╚═════════════════════════════════════════════════════════════════════════╝')
        else:
            stdscr.addstr(8, 3, '╔═╣ Confirm Investment ╠══════════════════════════════════════════════════╗')
            stdscr.addstr(9, 3, '║                                                                         ║')
            stdscr.addstr(10, 3, '║                                                                         ║')
            stdscr.addstr(10, 3, '║ You selected ')
            stdscr.addstr('long' if buy_long else 'short', green if buy_long else red)
            stdscr.addstr(' in ')
            stdscr.addstr(get_full_name(cpstate[str(selected_player_id)]), green)
            stdscr.addstr(' with an expiry in ')
            stdscr.addstr('%d' % (expiry), stat_color)
            stdscr.addstr(' turns.')
            stdscr.addstr(11, 3, '║                                                                         ║')
            stdscr.addstr(12, 3, '║ You tried to Invest ')
            stdscr.addstr(str(cost), yellow)
            stdscr.addstr(' , but you have ')
            stdscr.addstr(str(total_gems), yellow)
            stdscr.addstr(' Power Gems. Get lost, poor.')
            stdscr.addstr(' ' * (35 - len(str(cost)) + len(str(total_gems))))
            stdscr.addstr('║')
            stdscr.addstr(13, 3, '║                                                                         ║')
            stdscr.addstr(14, 3, '║                                                                         ║')
            stdscr.addstr(15, 3, '║ Press ')
            stdscr.addstr('q', red | curses.A_REVERSE)
            stdscr.addstr(' to go back.                                 ║')
            stdscr.addstr(16, 3, '║                                                                         ║')
            stdscr.addstr(17, 3, '╚═════════════════════════════════════════════════════════════════════════╝')
def view_stonks(stdscr):
    db.open_db()
    y = 1
    for it in db.get_stonk_holdings():
        player = db.get_player(it.player_id)
        clan = db.get_clan_by_id(it.clan_id)
        stdscr.addstr(y, 1, 'Clan %s is %s in %s. Expires in %d turns.' % (
            clan.name, 'long' if it.long else 'short', player.username, it.expires_turn))
        y += 1
        if y == 23:
            stdscr.addstr(24, 1, 'Press to view more...')
            while -1 == stdscr.getch():
                time.sleep(0.2)
            y = 0
    stdscr.addstr(25, 1, 'Press q to exit.')
    while -1 == stdscr.getch():
        time.sleep(0.2)

def main(stdscr):
    global no_color
    global avanza_logo
    global white
    global focused_item
    global stat_color
    global red
    global yellow
    global green
    global list_name
    global selected_item
    global selected_player_id
    global state

    global buy_long
    global expiry

    db.open_db()
    stdscr.clear()
    stdscr.nodelay(1)
    curses.noecho()
    curses.start_color()
    curses.use_default_colors()
    curses.curs_set(0)
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_GREEN)
    curses.init_pair(3, curses.COLOR_WHITE, -1)
    curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.init_pair(5, curses.COLOR_WHITE, -1)
    curses.init_pair(6, curses.COLOR_RED, -1)
    curses.init_pair(7, curses.COLOR_YELLOW, -1)
    curses.init_pair(8, curses.COLOR_GREEN, -1)
    no_color = curses.color_pair(1)
    avanza_logo = curses.color_pair(2)
    white = curses.color_pair(3)
    focused_item = curses.color_pair(4) | curses.A_REVERSE
    stat_color = curses.color_pair(5) | curses.A_DIM
    red = curses.color_pair(6)
    yellow = curses.color_pair(7)
    green = curses.color_pair(8)
    list_name = yellow
    selected_item = curses.color_pair(8) | curses.A_REVERSE

    if not invest:
        return view_stonks(stdscr)

    quit = False
    update_at = 0

    while not quit:
        cpstate = session.get_state()['players']
        if str(my_id) in cpstate:
            del cpstate[str(my_id)]
        foo = {}
        for k,v in cpstate.items():
            if 'hp' in v and 'hpmax' in v and v['hp'] >= 1:
                foo[k] = v
        cpstate = foo
        player_order = [ int(it[0]) for it in sorted(cpstate.items(), key=lambda x: x[1]['player_name']) ]
        #open('/tmp/sko', 'w').write(json.dumps(cpstate))
        #exit(0)
        if len(player_order) == 0:
            stdscr.addstr(5, 5, 'NO STONKS :( Press q, or some other key.')
            time.sleep(1)
            return
        if selected_player_id is None:
            selected_player_id = player_order[0]
        elif selected_player_id not in player_order:
            selected_player_id = player_order[-1]

        if time.time() >= update_at:
            update(stdscr, cpstate, player_order)
            update_at = time.time() + 1
        
        key = stdscr.getch()
        if ord('j') == key:
            if 0 == state:
                for i in range(0, len(player_order)):
                    if selected_player_id == player_order[i]:
                        if i + 1 >= len(player_order):
                            selected_player_id = player_order[0]
                        else:
                            selected_player_id = player_order[i + 1]
                        break
            elif 1 == state:
                expiry -= INC_EXPIRY
                if expiry < MIN_EXPIRY:
                    expiry = MAX_EXPIRY
            elif 2 == state:
                buy_long = not buy_long
        elif ord('k') == key:
            if state == 0:
                for i in range(0, len(player_order)):
                    if selected_player_id == player_order[i]:
                        if i - 1 < 0:
                            selected_player_id = player_order[-1]
                        else:
                            selected_player_id = player_order[i - 1]
                        break
            elif state == 1:
                expiry += INC_EXPIRY
                if expiry > MAX_EXPIRY:
                    expiry = MIN_EXPIRY
            elif state == 2:
                buy_long = not buy_long
        elif ord(' ') == key:
            if state == 4:
                if cost <= (total_gems + 500):
                    # print('preeee')
                    db.add_buy_stonk_event(my_id, my_session, my_turn, int(selected_player_id), 'stonk', cost, expiry, buy_long)
                    # print('pooost')
                state = 3
            else:
                state += 1
        elif ord('q') == key:
            if 0 == state:
                quit = True
            else:
                state -= 1
        elif -1 == key:
            time.sleep(0.1)
            continue
        update_at = 0

def movecursor(x, y):
    print("\x1b[%d;%df" % (y, x), end='')

my_id = int(sys.argv[1])
my_turn = int(sys.argv[2])
my_session = int(sys.argv[3])

if True:
    logo = open('avanza.txt').read()
    logo = list(logo)

    for i in range(0, len(logo)):
        if logo[i] in ['1','2','3']:
            logo[i] = '\x1b[1;33m' + logo[i]
        elif logo[i] not in ['\n', '\r', '\t', '$', ' ']:
            logo[i] = '\x1b[1;37m' + logo[i]

    logo = ''.join(logo)
    logo = logo.replace('$', '\x1b[1;32m$')
    y = 1
    for it in ('\x1b[?25l\x1b[2J%s' % (logo)).split('\n'):
        movecursor(1, y)
        print(it)
        y += 1

    while True:
        v = readchar.readchar()
        if v == '1':
            invest = True
            break
        elif v == '2':
            invest = False
            break
        elif v == '3':
            sys.exit(123)
    print('\x1b[?25h')


wrapper(main)
