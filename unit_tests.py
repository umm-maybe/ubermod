import ubermod
from time import time

test_string = "When I was a kid, I was a total asshole."

print(f"Test string: \"{test_string}\"")

print("Checking topic...")
start = time()
check_topic = ubermod.on_topic(test_string, ["child","adult","pizza"])
end = time()
duration = end-start
print(f"Duration = {duration}, Results: {check_topic}")

print("Checking toxicity (simple)...")
start = time()
check_toxic1 = ubermod.check_toxicity(test_string)
end = time()
duration = end-start
print(f"Duration = {duration}, Results: {check_toxic1}")

print("Checking toxicity (combined)...")
start = time()
check_toxic2 = ubermod.is_toxic(test_string)
end = time()
duration = end-start
print(f"Duration = {duration}, Results: {check_toxic2}")

print("Checking if image is NSFW...")
start = time()
image_check1 = ubermod.check_image("test.jpg")
end = time()
duration = end-start
print(f"Duration = {duration}, Results: {image_check1}")

print("Checking image topic...")
start = time()
image_check2 = ubermod.image_topic("test.jpg",["child","adult","pizza"])
end = time()
duration = end-start
print(f"Duration = {duration}, Results: {image_check2}")
