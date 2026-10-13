from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from textblob import TextBlob
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Sentences(BaseModel):
    sentences: List[str]

class ResultItem(BaseModel):
    sentence: str
    sentiment: str

class Result(BaseModel):
    results: List[ResultItem]

# Strong keywords that override TextBlob if found
HAPPY_WORDS = [
    "love", "loved", "loving", "great", "excellent", "amazing", "awesome",
    "fantastic", "wonderful", "happy", "joyful", "excited", "best", "beautiful",
    "perfect", "brilliant", "superb", "delightful", "glad", "enjoy", "enjoyed",
    "fun", "incredible", "grateful", "thankful", "pleased", "cheerful",
    "outstanding", "terrific", "yay", "hooray", "smile", "laughing", "thrilled",
    "ecstatic", "overjoyed", "blessed", "positive", "like", "liked"
]

SAD_WORDS = [
    "hate", "hated", "terrible", "awful", "horrible", "bad", "worst", "sad",
    "disappointed", "disappointing", "upset", "angry", "frustrated", "annoyed",
    "miserable", "depressed", "crying", "cry", "dreadful", "disgusting",
    "dislike", "unfortunately", "failed", "fail", "failure", "poor", "useless",
    "broken", "hurt", "pain", "suffering", "regret", "sorry", "waste",
    "pathetic", "disaster", "ugly", "boring", "dull", "tired", "exhausted",
    "unfortunate", "tragic", "devastated", "hopeless", "helpless", "furious"
]

def get_sentiment(text):
    lower = text.lower()

    # Count keyword hits
    happy_score = sum(1 for w in HAPPY_WORDS if w in lower.split())
    sad_score   = sum(1 for w in SAD_WORDS   if w in lower.split())

    # Get TextBlob polarity (-1 to +1)
    polarity = TextBlob(text).sentiment.polarity

    # Combine: keywords vote + textblob vote
    if happy_score > sad_score:
        keyword_vote = "happy"
    elif sad_score > happy_score:
        keyword_vote = "sad"
    else:
        keyword_vote = "neutral"

    if polarity > 0.1:
        textblob_vote = "happy"
    elif polarity < -0.1:
        textblob_vote = "sad"
    else:
        textblob_vote = "neutral"

    # If both agree, confident answer
    if keyword_vote == textblob_vote:
        return keyword_vote

    # If keywords found a strong signal, trust them
    if happy_score > 0 or sad_score > 0:
        return keyword_vote

    # Otherwise trust TextBlob
    return textblob_vote

@app.post("/sentiment", response_model=Result)
def sentiment_analysis(data: Sentences):
    results = []
    for sentence in data.sentences:
        sentiment = get_sentiment(sentence)
        results.append({"sentence": sentence, "sentiment": sentiment})
    return {"results": results}