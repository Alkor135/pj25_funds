from youtube_transcript_api import YouTubeTranscriptApi

# video_id = "ZVMTeDBmSrI"  # стратегии Markov Hedge Fund Method
# video_id = "kMq4ryVTkEg"  # Olden_Era_ратное_дело
# video_id = "IrmDk-ry_bk"  # Olden_Era_роща_без_лучников
video_id = "1DkYpwHaF7M"  # Olden_Era_хмельной_аватар

yta = YouTubeTranscriptApi()
transcript = yta.fetch(video_id, languages=["ru", "en"])

text = "\n".join(item.text for item in transcript)

# file_output = "youtube_transcript.txt"  # стратегии Markov Hedge Fund Method
# file_output = "youtube_Olden_Era_ратное_дело.txt"
# file_output = "youtube_Olden_Era_роща_без_лучников.txt"
file_output = "youtube_Olden_Era_хмельной_аватар.txt"

with open(file_output, "w", encoding="utf-8") as f:
    f.write(text)

print(f"Сохранено в {file_output}")