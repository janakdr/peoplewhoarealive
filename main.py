# Copyright 2015 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# [START app]
import logger
import pickledb
import pprint
import sys
import tweepy
import urllib2
import wikitools
from flask import Flask

app = Flask(__name__)

SELF_SCREEN_NAME = 'pplwhoarealive'

LOG = logger.logging.getLogger("alive-basic")


WIKI_SITE = wikitools.wiki.Wiki("https://en.wikipedia.org/w/api.php")
WIKI_PARAMS = {'action' : 'query', 'prop' : 'revisions', 'rvprop' : 'content'}

def check_living(person):
  req = wikitools.api.APIRequest(WIKI_SITE, dict({'titles' : person}, **WIKI_PARAMS))
  page_text = req.query(querycontinue=False)['query']['pages'].values()[0]['revisions'][0]['*']
  LOG.debug(page_text)
  return "[[Category:Living people]]" in page_text


def tweet_alive(person, reply_id, screen_name, api):
  LOG.info("%s is alive!" % person)
  api.update_status("No worries @%s, %s is alive!" % (screen_name, person), in_reply_to_status_id=reply_id)


def validate_tweet(tweet):
  return tweet.user.screen_name != SELF_SCREEN_NAME


def extract_name(tweet_text):
  tweet_text = tweet_text.replace('@pplwhoarealive','')
  tweet_text = tweet_text.lstrip('.')
  # TODO(janak): sanitize tweet_text
  # TODO(janak): handle "[Ii]s ___( still)? alive\?*" and "[Ii]s __ dead\?*".
  # TODO(janak): return None if can't find name, change caller to tolerate.
  return tweet_text

   
def initialize_api(db):
  consumer_key = db.get("consumer_key")
  consumer_secret = db.get("consumer_secret")
  access_token = db.get("access_token")
  access_token_secret = db.get("access_token_secret")

  auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
  auth.set_access_token(access_token, access_token_secret)
  return tweepy.API(auth)


@app.route('/')
def main():
  print("Start of method")
  sys.stdout.flush()
  db = pickledb.load('alive.db', False)
  api = initialize_api(db)
  last_id = db.get("last_id")
  mentions = api.mentions_timeline(since_id = last_id)
  for mention in mentions:
    last_id = max(last_id, mention.id)
    if not validate_tweet(mention): 
      continue
    person = extract_name(mention.text)
    LOG.info('%s -> %s' % (mention.text, person))
    if check_living(person):
      try:
        tweet_alive(person=person, reply_id=mention.id, screen_name=mention.user.screen_name, api=api)
      except tweepy.TweepError as err:
        LOG.info(err)
  db.set("last_id", last_id)
  db.dump()
  return "Done!!"

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080)
# [END app]
