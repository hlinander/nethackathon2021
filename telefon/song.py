from openai import OpenAI

def get_lyrics_from_desc(desc):
  client = OpenAI()

  completion = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
      {"role": "system", "content": "You are a master bard, creating witty, thoughtful, sometimes sad, sometimes encouraging, sometimes heartfelt small songs about events in nethack. You will create a song that is exactly TWO PARAGRAPHS."},
      {"role": "user", "content": desc  } # "We are playing the roguelike nethack game, the player Niels has just been killed by a soldier ant while burdened. Write a song."}
    ]
  )

  return completion.choices[0].message.content
