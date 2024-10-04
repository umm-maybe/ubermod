# UBERMOD
This is a Reddit moderation bot that uses machine learning models to identify toxic and NSFW material (text and images) in posts and comments on a given subreddit.  It attempts to filter out content that might be considered minor sexualization, mainly by checking whether the content appears to reference children, after determining that the content is NSFW. I originally created this bot as a tool to support moderation of r/SubSimGPT2Interactive, but in its current form it could be used on any subreddit.

## Requirements
Previous versions of this bot used the HuggingFace inference API to run classification models; however since they have clamped down on free access to that service the bot now loads the models locally.  You will therefore need an always-on machine with sufficient CPU and RAM to run inference.  A GPU is not necessary.  You will also need Python 3 installed.

## Installation
Clone the repo, enter the directory, create a virtual environment and activate (e.g. `source python3 -m venv env && env/bin/activate`) and install the requirements (`pip3 install -Ur requirements.txt`).

## Preparation
Create a user account for the bot on reddit and go to https://reddit.com/prefs/apps to create a bot (you may have to jump through some hoops to do this thanks to Reddit's API policy changes).  Create a copy of *config_example.yaml*, rename it to *config.yaml*, and enter the user account, password, and client id/secret values you obtained previously from Reddit.  You can also customize the toxicity thresholds and topic labels used to check content, if desired.

To run the bot, with the virtual environment activated, execute:
`python3 ubermod.py config.yaml`

Note that the bot will run indefinitely until it crashes or you Ctrl-C to kill it, so it is probably a good idea to use *tmux* or something similar so that you still have access to your shell.
