import pyte
import struct
import time
import re
import datetime
import sys
import random
import os
import db
import session
import jens
from subprocess import Popen

NO_WAIT = True

SCREEN_W = 512
SCREEN_H = 512

DEATH_CAM_SEC = 3

def clear():
	draw('\x1b[2J')

def draw(text):
	sys.stdout.write(text)

def draw_at(x, y, text):
	goto(x, y)
	draw(text)

def show_cursor(show):
    draw("\x1b[?25l" if not show else "\x1b[?25h")

def get_ms():
	return int(time.time() * 1000)

def _load_tty(filename):
	screen = pyte.Screen(SCREEN_W, SCREEN_H)
	stream = pyte.Stream(screen)
	fp = open(filename, 'rb')
	return dict(fp=fp, screen=screen, stream=stream, start_at=None, next_at=None,
		hp=0, maxhp=0, money=0, dead=False)

def load_tty(user_id, filename):
	return { 'user_id': user_id, 'live': _load_tty(filename), 'death': _load_tty(filename),
		 'filename': filename, 'created': time.time(), 'mtime': 0 }

def read_time(tr):
	try:
		sec, usec = struct.unpack('<II', tr['fp'].read(8))
		return sec + (usec / 1000000)
	except:
		return None

def read_frame(tr):
	size = struct.unpack('<I', tr['fp'].read(4))[0]
	data = tr['fp'].read(size)
	try:
		tr['stream'].feed(data.decode('utf-8'))
	except:
		pass

def step(tr, elapsed):
	t =  read_time(tr) if tr['next_at'] is None else tr['next_at']
	if t is None:
		return False
	if tr['start_at'] is None:
		tr['start_at'] = t
		read_frame(tr)
		return True
	if NO_WAIT or elapsed >= (t - tr['start_at']):
		read_frame(tr)
		tr['next_at'] = None
	else:
		tr['next_at'] = t
	return True

def goto(x, y):
	draw('\x1b[%d;%dH' % (y+1, x+1))

def convert_line(line):
	out = list(' ' * MON_W)
	plain = list(' ' * MON_W)
	fg = ''
	bg = ''
	for x in range(0, MON_W):
		v = line[x]
		n = ''
		if v.fg == 'default':
			n += '\x1b[0;37m'
		elif v.fg == 'brown':
			n += '\x1b[0;33m'
		elif v.fg == 'white':
			n += '\x1b[1;37m'
		elif v.fg == 'black':
			n += '\x1b[0;30m'
		elif v.fg == 'red':
			n += '\x1b[0;31m'
		elif v.fg == 'green':
			n += '\x1b[1;32m'
		elif v.fg == 'blue':
			n += '\x1b[1;34m'
		elif v.fg == 'cyan':
			n += '\x1b[1;36m'
		elif v.fg == 'yellow':
			n += '\x1b[1;33m'
		elif v.fg == 'magenta':
			n += '\x1b[1;35m'

		if v.bg == 'default':
			n += '' # '\x1b[0;100m'
		elif v.bg == 'brown':
			n += '\x1b[0;43m'
		elif v.bg == 'white':
			n += '\x1b[1;47m'
		elif v.bg == 'black':
			n += '\x1b[0;40m'
		elif v.bg == 'red':
			n += '\x1b[0;41m'
		elif v.bg == 'green':
			n += '\x1b[1;42m'
		elif v.bg == 'blue':
			n += '\x1b[1;44m'
		elif v.bg == 'cyan':
			n += '\x1b[1;46m'
		elif v.bg == 'yellow':
			n += '\x1b[1;43m'
		elif v.bg == 'magenta':
			n += '\x1b[1;45m'
		out[x] = n + v.data
		plain[x] = v.data
	return ''.join(out), ''.join(plain)

def draw_screen(tr, x, y):
	b = tr['screen'].buffer
	for line in tr['screen'].dirty:
		if line > 25:
			continue
		c, raw = convert_line(tr['screen'].buffer[line])
		if line < MON_H:
			draw_at(x, y+line, c)
		parse(tr, raw)
	tr['screen'].dirty.clear()

def parse(tr, line):
	m = re.match(r'.*\$:(\d+) HP:(\d+)\((\d+)\).*', line)
	if m is not None:
		tr['money'] = int(m.group(1))
		tr['hp'] = int(m.group(2))
		tr['maxhp'] = int(m.group(3))
	if tr['maxhp'] != 0 and tr['hp'] == 0:
		tr['dead'] = True

font = []

def load_font(filename):
	global font
	font = []
	char = []
	for it in open(filename, 'r').readlines():
		it = it.strip('\n')
		it = it.strip('\r')
		if it[-2:] == '@@':
			font.append(char)
			char = []
		else:
			char.append(it[:-1])

def play_death():
	os.system('aplay nhmon/death%d.wav 2>/dev/null' % (random.randint(0, 1)))

def play_type():
	os.system('aplay nhmon/type%d.wav 2>/dev/null' % (random.randint(0, 1)))

def type_char(x, y, c, sound):
	width = 0
	#Popen(['cvlc', '--play-and-exit', 'type%d.wav' % (random.randint(0, 1))], shell=False, stdin=None, stdout=None, stderr=None, close_fds=True)
	if sound:
		play_type()
	index = ord(c) - ord('!')
	for line in font[index]:
		draw_at(x, y, line)
		y += 1
		width = max(width, len(line))
	sys.stdout.flush()
	return width


def type_out(x, y, s, sound = True):
	for c in s:
		if ' ' == c:
			x += 6
		else:
			x += type_char(x, y, c, sound) + 1
	play_type()	

def run_tty(tr, start, x, y, do_draw):
	did_step = step(tr, time.time() - start)
	if do_draw:
		draw_screen(tr, x, y)
		goto(x, MON_H)
		# draw_at(x, MON_H, 'HP: %d/%d   Gold: %d' % (tr['hp'], tr['maxhp'], tr['money']))
	return did_step

def red():
	draw('\x1b[1;31m')
def reset():
	draw('\x1b[0m')

def death_cam(name, tr, start):
	set_fullscreen_size()
	clear()
	type_out(1, 1, name)
	time.sleep(0.5)
	red()
	type_out(15, 9, 'DEAD.', False)
	play_death()
	reset()
	time.sleep(1)
	clear()
	w, h = os.get_terminal_size()
	jens.paint_frames([(1, 1, w, h, name, 3)])
	while run_tty(tr, start, 1, 1, True):
		sys.stdout.flush()
		time.sleep(1/30)
	set_4x4_size()

def update_rec_list(ttydir, recs):
	files_by_user_id = {}
	for (dirpath, dirnames, filenames) in os.walk(ttydir):
		for file in filenames:
			file = os.path.join(dirpath, file)
			if file.endswith(".ttyrec"):
				m = re.match(r'.*\d+_(\d+)\.ttyrec', file)
				if m is not None:
					user_id = int(m.group(1))
					latest = files_by_user_id.get(user_id)
					mtime = os.path.getmtime(file)
					if latest is None or latest["mtime"] < mtime:
						files_by_user_id[user_id] = {
							"user_id": user_id,
							"mtime": mtime,
							"path": file
						}
	
	for k, v in files_by_user_id.items():
		found = False
		for i in range(0, len(recs)):
			it = recs[i]
			if k == it['user_id']:
				if it['filename'] != v['path']: # new file
					recs[i] = load_tty(k, v['path'])
				it['mtime'] = v['mtime']
				found = True
				break
		if not found:
			ttyfile = load_tty(k, v['path'])
			ttyfile['mtime'] = v['mtime']
			recs.append(ttyfile)


def get_long_amount(player_state):
	long_amount_gems = 0
	if 'long_amount_gems' in player_state:
		long_amount_gems = player_state['long_amount_gems']
	return long_amount_gems

def get_short_amount(player_state):
	short_amount_gems = 0
	if 'short_amount_gems' in player_state:
		short_amount_gems = player_state['short_amount_gems']
	return short_amount_gems



def interest_level(rec, all_player_states):
	if 'player_state' in rec:
		player_state = rec['player_state']
		if 'dlevel' in player_state:
			rec['dlevel'] = player_state['dlevel']
		if 'hp' in player_state and 'hpmax' in player_state and player_state['hpmax'] != 0:
			hp = player_state['hp']
			hpmax = player_state['hpmax']
			rec['hp'] = hp
			rec['hpmax'] = hpmax
			if hp <= 0:
				return -1.0
			hp_percentage = hp / hpmax
		else:
			hp_percentage = 1.0

		total_investment = 0
		for player in all_player_states:
			total_investment += get_long_amount(player) + get_short_amount(player)

		player_investment = get_long_amount(player) + get_short_amount(player)

		investment_interest = player_investment / total_investment if total_investment != 0 else 0

		time_since_active = 0
		if 'last_event_time' in player_state:
			time_since_active = datetime.datetime.now().timestamp() - rec['mtime'] #player_state['last_event_time']

		rec['time_since_active'] = time_since_active
		active_modifier = 1.0 - max(0, min(1, time_since_active / 180.0)) * 0.5
		# print(str(rec['user_id']) + " " + str(active_modifier))
		return (1.0 - hp_percentage + investment_interest + 0.1) * active_modifier
	return 0.0

def rec_interest_sort_key(rec, all_player_states):
	return interest_level(rec, all_player_states)


def choose_on_display(on_display, recs):
	player_states = session.get_state()['players']

	# update player_state in recs
	for it in recs:
		if str(it['user_id']) in player_states:
			player_state = player_states[str(it['user_id'])]
			it['player_state'] = player_state
			it['interest'] = interest_level(it, player_states)
		for i, display in enumerate(on_display):
			if display['rec']['user_id'] == it['user_id'] and display['rec'] != it:
				on_display[i]['rec'] = it





	sorted_recs = sorted(recs, reverse=True, key=lambda x: rec_interest_sort_key(x, player_states))
	
	sorted_not_displayed = list(filter(lambda x: not any(o['rec'] == x for o in on_display), sorted_recs))

	for i in range(4):
		if len(on_display) <= i:
			if len(sorted_not_displayed) > 0:
				on_display.append( {
					'rec': sorted_not_displayed[0],
					'live_at': time.time(),
				})
				del sorted_not_displayed[0]
		else:
			current = on_display[i]
			time_live = time.time() - current['live_at']
			if time_live > 15 or current['rec']['live']['dead']:
				current_interest_level = interest_level(current['rec'], player_states)
				current_interest_level *= 1.0 - min(time_live / 360, 1.0) * 0.35
				if len(sorted_not_displayed) > 0:
					other = sorted_not_displayed[0]
					other_interest_level = interest_level(other, player_states)
					if other_interest_level > current_interest_level:
						# check if something is more interesting
						on_display[i] = {
							'rec': other,
							'live_at': time.time(),
						}
						del sorted_not_displayed[0]

	for i in range(4):
		if len(on_display) > i:
			on_display[i]['x'] = 1 + (i & 1) * MON_W + (i&1)
			on_display[i]['y'] = 1 + (i >> 1) * MON_H + (i>>1)


def run(ttydir):
	recs = []
	on_display = []
	start = time.time()
	frame = 0
	deathcams_played = []
	while True:
		update_rec_list(ttydir, recs)
		recs = [it for it in recs if not it['filename'] in deathcams_played]

		choose_on_display(on_display, recs)
		framedata = []
		# time.sleep(1/30)
		i = 0
		for it in recs:
			screen_x = 0
			screen_y = 0
			exists = False
			for d in on_display:
				if d['rec'] == it:
					exists = True
					screen_x = d['x']
					screen_y = d['y']
					break
			run_tty(it['live'], start, screen_x, screen_y, exists)
			time_since_active = int(0)
			interest = 0.0
			hp = 0
			hpmax = 0
			dlevel = 0
			if 'player_state' in it:
				player_state = it['player_state']
				if player_state and 'player_name' in player_state:
					if 'interest' in it:
						interest = it['interest']
					if 'time_since_active' in it:
						time_since_active =it['time_since_active'] 
					if 'hp' in it:
						hp =it['hp'] 
					if 'hpmax' in it:
						hpmax = it['hpmax'] 
					if 'dlevel' in it:
						dlevel = it['dlevel'] 
				interest_float = str.format("{:.1f}", interest)
				player_name = player_state['player_name'] + "  " + str(hp) + "/" + str(hpmax) + " hp  dlevel " + \
						str(dlevel) + "                                           i:" + interest_float
				# player_name = player_state['player_name'] + "  " + str(hp) + "/" + str(hpmax) + " hp  dlevel " + \
						# str(dlevel) + "                                           i:" + interest_float
			else:
				player_name = "Loading.."
			if it['live']['dead'] and it['filename'] not in deathcams_played: 
				if "player_name" in player_state:
					name = player_state["player_name"]
				else:
					name = "Vem?"
				death_cam(name, it['death'], start + DEATH_CAM_SEC)
				deathcams_played.append(it['filename'])
			elif time.time() > (it['created'] + DEATH_CAM_SEC):
				run_tty(it['death'], start + DEATH_CAM_SEC, screen_x, screen_y, False)
			if it['live']['maxhp']:
				color = int(4 - (3 * (it['live']['hp'] / it['live']['maxhp'])))
			else:
				color = 0
			if exists:
				framedata.append((screen_x, screen_y, MON_W+2, MON_H+2, player_name, color))
		reset()
		jens.paint_frames(framedata)
		recs = [it for it in recs if not it['live']['dead']]
		frame += 1
		sys.stdout.flush()
		time.sleep(0.001)

MON_W = 0
MON_H = 0

def set_4x4_size():
	global MON_W
	global MON_H
	MON_W, MON_H = os.get_terminal_size()
	MON_W = (MON_W // 2) - 3
	MON_H = (MON_H // 2) - 3

def set_fullscreen_size():
	global MON_W
	global MON_H
	MON_W, MON_H = os.get_terminal_size()
	MON_W = MON_W - 2
	MON_H = MON_H - 2 # borders

def main():
	db.open_db()
	show_cursor(False)
	set_4x4_size()
	load_font('nhmon/font.txt')
	run(sys.argv[1])
	show_cursor(True)

if __name__ == "__main__":
	main()
