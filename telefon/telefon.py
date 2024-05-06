import requests
import time
from telefon.song import get_lyrics_from_desc
import json

__client = 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6ImNsaWVudF8yZzVGYkl3UXNVc3E4dWlCc3RlMW80Mmc5aW8iLCJyb3RhdGluZ190b2tlbiI6InlydTR0am5vNDhtNXM1bGFlNnY2d3M2dHYwcHptdGM5NG1leHNtbHQifQ.n0yUir-ytcjlvnw3q-YvdRRfqopQKDmdcSmMQIBS7LzRlgysM11Vsi7e--wlBxoDH5aD6rS7Pk7rV1xIe73RBz_u_dmEZc9lrh2QI5EqapVeZKhF5RdeRhOJtgHrzd4a1eXX5c8y3-M0MvifO4npDdINfTWJxoeCHEu09xOQo7L5O3JJGvPLvPiIBz1LZuyKJpy8QYUBXrcxobzeOFyvdU9-bh75TMXwHLHfgyFa086P7p3XfTg-ydBWuqMBBfTbGeD7lXYoXuDl0tskf2defL62AD_E3kL7UFcaEIVB3d0t5jCaioGlQ7iXZe89t83b8fvKwBVKc2wnl397Ea7hVw'
__client_uat = str(int(time.time()))

def suno_make_cookies():
	return {
		"__client": __client,
		"__client_uat": __client_uat
	}

def suno_init_session(s):
	j = s.get('https://clerk.suno.com/v1/client?_clerk_js_version=4.72.0-snapshot.vc141245', cookies=suno_make_cookies())
	print(j)
	j = j.json()
	print(json.dumps(j, indent=2))
	time.sleep(2)
	jwt = j['response']['sessions'][0]['last_active_token']['jwt']
	session = j['response']['last_active_session_id']
	return jwt, session

def suno_refresh(s, session):
	j = s.post('https://clerk.suno.com/v1/client/sessions/%s/tokens?_clerk_js_version=4.72.2' % (session),
		cookies=suno_make_cookies()).json()
	if j['object'] != 'token':
		raise Exception('Wtf happened now?')
	return j['jwt']

def suno_create_song(s, jwt, session, title, tags, prompt):
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
		print("[DATA]")
		print(data)
		print("[/DATA]")
		for it in data:
			print(it) 
			print(it["status"])
			if it["status"] == "complete":
				return it["id"]
		time.sleep(1)
		if n_poll % 5 == 0:
			print('Refresing (%s)' % (jwt))
			jwt = suno_refresh(s, session)
			print('After refreshing (%s)' % (jwt))
		n_poll += 1


from dataclasses import dataclass
@dataclass
class SongResult:
	song_url: object
	song_lyrics: object

def create_song(desc):
	s = requests.Session()
	jwt, session = suno_init_session(s)
	lyrics = get_lyrics_from_desc(desc)
	clip_id = suno_create_song(s, jwt, session, "a song", "sutra", lyrics)
	clip_url = f"https://cdn1.suno.ai/{clip_id}.mp3"
	return SongResult(song_url=clip_url, song_lyrics=lyrics)
	# return clip_url
	# print(clip_url)

# create_song('Detta e sång om en ballong. Jag e katt, du e hest.')
