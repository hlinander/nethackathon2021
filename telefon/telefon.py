import requests
import time
from telefon.song import get_lyrics_from_desc

# def suno_refresh():
# 	s = requests.Session()
# 	__client = 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6ImNsaWVudF8yZTNQZG1yY1V0Tk9Qdk1mSzJLNXZPWk83RlIiLCJyb3RhdGluZ190b2tlbiI6IjU5MjRrNmI1d2dja2Rkb2c4MjNuaWIwY3JvcWNuanNkMmxxbmtoc3YifQ.f4uJY92LRwijV95bMg4C2mQtbcbFQ6Km-PiOX5r-f2PgSV8emECIdxy1ecmHSafzVIQkMpohaW--1F8pm8Ej11qEPgKVXgwsIi9hEN5-L2Odhz2-BuQokY2jtuhGhpY0ApBZkh45Xbe1PmQ3MDwjmuOVJw5sZGCYBwIicjov8_BRJxBFwJCfxE-pKz9dEpDltkOPveAoh_Q4n_DuzF-XR4I3nqO1kwYFjeGAWj5ftRb9RrgRv79iJqE0UBF1XtgDjPnUWdikeyMW2F5lcWjxaotJNYv9FpqgrAhH-RXW9DinIpqHozs4f9mu5-J37Fyl5Sk8LBvx3wet4hbQJFs3HQ'
# 	__client_uat = '1711130398'
# 	j = s.get('https://clerk.suno.ai/v1/client?_clerk_js_version=4.70.5', cookies={
# 			"__client": __client,
# 			"__client_uat": __client_uat
# 		}).json()
# https://clerk.suno.ai/v1/client/sessions/sess_2e3PgMx3gxJDQL3NcSz3bOnkUaG/tokens?_clerk_js_version=4.70.5
__client = 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6ImNsaWVudF8yZkt0bUJHZmlXOG1jdXlYWHlLcHc5N3IzRzAiLCJyb3RhdGluZ190b2tlbiI6InQzYWU2M3JmcDdnb2lkZWlzMWg0ejcyMjIwM2xoOGN5bjA4eTM0azAifQ.ha8Ss5q7zePpEvctHEmLOjPMZx-RRc_pAriOokwmkzBGkd2MwyxainMBhsevJJCZfUKzUxc9OflpGMX-ieigM8S4wH53v6q288EGgQACDMU4izFj46Crg4kVG4PAFTdgtz8YfvE4g7qXcbBCLWzp3nXzsenQzWVpe6M1KVMfBcHDnhdvkD0U5oXrwHUx8AfMeCYHcqGk24FlJz8yqKmIEZ0y25zhZP3xgt_RUKgUKnKxQSXXfh1pJx9idlM2zAlzZkoreRDsFbVaOtwECD3b1Z8k5XZmP-l1u-q6bs-PTtAIqa8jZB_QnBoXp0Dk16NFlKAVXC0UysWGHKhGdGc9uQ'
__client_uat = '1713561815'

def suno_init_session():
	s = requests.Session()
	# __client = 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6ImNsaWVudF8yZTNQZG1yY1V0Tk9Qdk1mSzJLNXZPWk83RlIiLCJyb3RhdGluZ190b2tlbiI6IjU5MjRrNmI1d2dja2Rkb2c4MjNuaWIwY3JvcWNuanNkMmxxbmtoc3YifQ.f4uJY92LRwijV95bMg4C2mQtbcbFQ6Km-PiOX5r-f2PgSV8emECIdxy1ecmHSafzVIQkMpohaW--1F8pm8Ej11qEPgKVXgwsIi9hEN5-L2Odhz2-BuQokY2jtuhGhpY0ApBZkh45Xbe1PmQ3MDwjmuOVJw5sZGCYBwIicjov8_BRJxBFwJCfxE-pKz9dEpDltkOPveAoh_Q4n_DuzF-XR4I3nqO1kwYFjeGAWj5ftRb9RrgRv79iJqE0UBF1XtgDjPnUWdikeyMW2F5lcWjxaotJNYv9FpqgrAhH-RXW9DinIpqHozs4f9mu5-J37Fyl5Sk8LBvx3wet4hbQJFs3HQ'
	# __client_uat = '1713561333'
	j = s.get('https://clerk.suno.com/v1/client?_clerk_js_version=4.72.0-snapshot.vc141245', cookies={
			"__client": __client,
			"__client_uat": __client_uat
		})
	print(j)
	j = j.json()
	# import json
	# print(json.dumps(j, indent=2))
	# print(j)
	# last_sess = j['response']['last_active_session_id']
	# j = s.post('https://clerk.suno.ai/v1/client/sessions/%s/tokens/api?_clerk_js_version=4.72.0-snapshot.vc141245' % (last_sess),
		# cookies={
			# "__client": __client
		# }).json()
	time.sleep(2)
	return s, j['response']['sessions'][0]['last_active_token']['jwt']

def suno_create_song(s, jwt, title, tags, prompt):
	header = {
		"authorization": 'Bearer ' + jwt
	}
	r = s.post('https://studio-api.suno.ai/api/generate/v2/', headers=header,
	json={
		"continue_at": None,
		"continue_clip_id": None,
		"mv": "chirp-v3-0",
		"title": title,
		"tags": tags,
		"prompt": prompt,
	})

	if 200 != r.status_code:
		print('Died', r)
	js = r.json()
	# print(js)

	ids = [clip["id"] for clip in js["clips"]]

	n_poll = 0
	while True:
		feed_url = f"https://studio-api.suno.ai/api/feed/?ids={','.join(ids)}"
		data = s.get(feed_url, headers=header).json()
		for it in data:
			print(it["status"])
			if it["status"] == "complete":
				return it["id"]
			
		time.sleep(1)
		# if n_poll % 5 == 0:
			# s, jwt = suno_init_session()
			# header = {
				# "authorization": 'Bearer ' + jwt
			# }



def create_song(desc):
	s, jwt = suno_init_session()
	lyrics = get_lyrics_from_desc(desc)
	clip_id = suno_create_song(s, jwt, "a song", "sutra", lyrics)
	clip_url = f"https://cdn1.suno.ai/{clip_id}.mp3"
	return clip_url
	# print(clip_url)
# suno_create_song(s, jwt, 'Detta e datormusik', 'space trance', 'Detta e sång om en ballong. Jag e katt, du e hest.')
