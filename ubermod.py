import praw
import requests
import mimetypes
import time
import threading
import shutil
from PIL import Image
import torch
from transformers import pipeline
import yaml
import sys

## Load config details from YAML
def load_yaml(filename):
    with open(filename, 'r') as stream:
        try:
            return yaml.safe_load(stream)
        except yaml.YAMLError as error:
            print(error)
    return None

# pass the yaml-format config file as command-line argument
config = load_yaml(sys.argv[1])

reddit = praw.Reddit(
    client_id=config["client_id"],
    client_secret=config["client_secret"],
    password=config["password"],
    user_agent=config["user_agent"],
    username=config["username"],
)
SUB = reddit.subreddit(config["subreddit"])

toxicity_thresholds = config["toxicity_thresholds"]

topic_model = pipeline("zero-shot-classification", model="valhalla/distilbart-mnli-12-3")
topic_list = config["topic_list"]

def on_topic(text, topiclist, trigger=0.75):
    result = topic_model(text, topiclist, multi_label=True)
    for score in result['scores']:
        if score > trigger:
            return True
    return False

toxicity_checker = pipeline("text-classification", model="unitary/unbiased-toxic-roberta", top_k=None)
def check_toxicity(text):
    start_time = time.time()
    try:
        results = toxicity_checker(text)
        end_time = time.time()
        print(f"Time taken: {end_time - start_time}")
        #print(f"Result: {results}")
        scores = {}
        for category in results[0]:
            scores[category['label']] = category['score']
        return scores
    except Exception as e:
        print(f"Exception in toxicity checker ({e})...")
        return None

def is_toxic(text2check):
    scores = check_toxicity(text2check)
    if scores:
        if scores['sexual_explicit'] > 0.75:
            if on_topic(text2check,topic_list):
                return True
        for threshold in toxicity_thresholds:
            if scores[threshold] > toxicity_thresholds[threshold]:
                return True
    else:
        return None
    return False

nsfw_checker = pipeline("image-classification", model="Falconsai/nsfw_image_detection")

def check_image(image_file):
    start_time = time.time()
    results = nsfw_checker(image_file)
    end_time = time.time()
    print(f"Time taken: {end_time - start_time}")
    #print(f"Result: {results}")
    scores = {}
    for result in results:
        scores[result['label']] = result['score']
    return scores

from transformers import CLIPProcessor, CLIPModel

clip_model = CLIPModel.from_pretrained("openai/clip-vit-large-patch14")
clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-large-patch14")

def image_topic(image_file, topiclist, trigger=0.75):
    image = Image.open(image_file)
    inputs = clip_processor(topiclist, images=image, return_tensors="pt", padding=True)
    outputs = clip_model(**inputs)
    logits_per_image = outputs.logits_per_image # this is the image-text similarity score
    #print(logits_per_image)
    probs = logits_per_image.softmax(dim=1) # we can take the softmax to get the label probabilities
    #print(probs)
    for prob in probs[0]:
        if prob > trigger:
            return True
    return False


def read_submissions(sub):
    while True:
        try:
            for submission in sub.stream.submissions(skip_existing=True):
                print(f"Post {submission.id}: {submission.title}")
                for recent_post in sub.new(limit=5):
                    if recent_post.title == submission.title and recent_post.id != submission.id:
                        submission.mod.remove(mod_note="Duplicate")
                        print("Duplicate post removed")
                if submission.is_self:
                    text2check = submission.title + "\n\n" + submission.selftext
                else:
                    text2check = submission.title
                    url2check = submission.url.split("?")[0]
                    try:
                        mimetype = mimetypes.guess_type(url2check)
                    except Exception as e:
                        print(f"Error in MIME type checker ({e})")
                        continue
                    if not mimetype[0]:
                        print("Could not guess MIME type")
                        continue
                    if mimetype[0].startswith('image/'):
                        res = requests.get(submission.url, stream = True)
                        if res.status_code != 200:
                            print(f"Error downloading image ({res.status_code})...")
                            continue
                        shutil.copyfileobj(res.raw, open('test.jpg', 'wb'))
                        img_scores = check_image('test.jpg')
                        if img_scores:
                            if img_scores['nsfw'] > 0.75:
                                if on_topic(text2check,topic_list):
                                    submission.mod.remove(mod_note="Minor sexualization detected")
                                    print("Post removed for minor sexualization")
                                if submission.over_18 == False:
                                    submission.mod.nsfw()
                                    print("Post marked NSFW")
                scores = check_toxicity(text2check)
                if scores:
                    if scores['sexual_explicit'] > 0.75:
                        if on_topic(text2check,topic_list):
                            submission.mod.remove(mod_note="Minor sexualization detected")
                            print("Post removed for minor sexualization")
                        if submission.is_self == False:
                            if image_topic('test.jpg', topic_list):
                                submission.mod.remove(mod_note="Minor sexualization detected")
                                print("Post removed for minor sexualization (due to image)")
                        if submission.over_18 == False:
                            submission.mod.nsfw()
                            print("Post marked NSFW")
                    for threshold in toxicity_thresholds:
                        if scores[threshold] > toxicity_thresholds[threshold]:
                            submission.report(reason=f"Possibly toxic content detected ({threshold}: {scores[threshold]})")
                            print(f"Post {submission.id} reported for {threshold} ({scores[threshold]})")
        except Exception as e:
            print(f"Exception in submission reader ({e})...")
            continue

def read_comments(sub):
    while True:
        try:
            for comment in sub.stream.comments(skip_existing=True):
                print(f"Comment {comment.id}: {comment.body}")
                scores = check_toxicity(comment.body)
                if scores:
                    if scores['sexual_explicit'] > 0.75:
                        if on_topic(comment.body,topic_list):
                            comment.mod.remove(mod_note="Minor sexualization detected")
                            print("Comment removed for minor sexualization")
                            continue
                        if comment.submission.over_18 == False:
                            comment.submission.mod.nsfw()
                    for threshold in toxicity_thresholds:
                        if scores[threshold] > toxicity_thresholds[threshold]:
                            comment.report(reason=f"Possibly toxic content detected ({threshold}: {scores[threshold]})")
                            print(f"Comment {comment.id} reported for {threshold} ({scores[threshold]})")
                            continue

        except Exception as e:
            print(f"Exception in comment reader ({e})...")
            continue


def main():
    submission_reader = threading.Thread(target=read_submissions, args=([SUB]))
    comment_reader = threading.Thread(target=read_comments, args=([SUB]))
    submission_reader.start()
    comment_reader.start()
    print("Ubermod running on r/subsimgpt2interactive...")

if __name__=="__main__":
    main()

