from youtube_transcript_api import YouTubeTranscriptApi

# video_id = "ZVMTeDBmSrI"  # стратегии Markov Hedge Fund Method
video_id = "Z-hU97WO30I"  # стратегии Markov Hedge Fund Method 2

yta = YouTubeTranscriptApi()
transcript = yta.fetch(video_id, languages=["ru", "en"])

text = "\n".join(item.text for item in transcript)

# file_output = "quant_funds.txt"  # стратегии Markov Hedge Fund Method
file_output = "quant_funds_2.txt"

with open(file_output, "w", encoding="utf-8") as f:
    f.write(text)

print(f"Сохранено в {file_output}")