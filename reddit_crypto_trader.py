from auth.reddit_auth import *
from trade_client import *
from store_order import *

from datetime import datetime, time
import time

import json
import os.path

import nltk
from nltk.sentiment import SentimentIntensityAnalyzer

reddit = load_creds('auth/auth.yml')
config = load_config('config.yml')
keywords = load_keywords('keywords.yml')

print(f'logged in as {reddit.user.me()}')

def get_post():
    """
    Returns relevant posts based the user configuration
    """
    posts = {}
    for sub in config['SUBREDDITS']:
        subreddit = reddit.subreddit(sub)
        relevant_posts = getattr(subreddit, config['SORT_BY'])(limit=config['NUMBER_OF_POSTS'])
        for post in relevant_posts:
            if not post.stickied:
                posts[post.id] = {"title": post.title,
                                  "subreddit": sub,
                                  "body": post.selftext,

                                  }
    return posts


def store_posts(data):
    """
     Stores relevant posts and associated data in a local json file
    """
    with open('reddit_posts.json', 'w') as file:
        json.dump(data, file)


def load_posts(file):
    """
    Loads saved reddit posts
    """
    with open(file, 'r') as f:
        return json.load(f)


def compare_posts(fetched, stored):
    """
    Checks if there are new posts
    """
    i=0
    for post in fetched:
        if not fetched[post] in [stored[item] for item in stored]:
            i+=0

    return i


def find_keywords(posts, keywords):
    """
    Checks if there are any keywords int he posts we pulled
    Bit of a mess but it works
    """
    key_posts = {}

    for post in posts:
        for key in keywords:
            for item in keywords[key]:
                if item in posts[post]['title'] or item in posts[post]['body']:
                    key_posts[post] = posts[post]
                    key_posts[post]['coin'] = key

    return key_posts


def analyse_posts(posts):
    """
    analyses the sentiment of each post with a keyword
    """
    sia = SentimentIntensityAnalyzer()
    sentiment = {}
    for post in posts:
        if posts[post]['coin'] not in sentiment:
            sentiment[posts[post]['coin']] = []

        sentiment[posts[post]['coin']].append(sia.polarity_scores(posts[post]['title']))
        sentiment[posts[post]['coin']].append(sia.polarity_scores(posts[post]['body']))

    return sentiment


def get_avg_sentiment(sentiment):
    """
    Compiles and returnes the average sentiment
    of all titles and bodies of our query
    """
    average = {}

    for coin in sentiment:
        # sum up all compound readings from each title & body associated with the
        # coin we detected in keywords
        average[coin] = sum([item['compound'] for item in sentiment[coin]])

        # get the mean compound sentiment if it's not 0
        if average[coin] != 0:
            average[coin] = average[coin] / len(sentiment[coin])

    return average


def get_price(coin, pairing):
    return client.get_ticker(symbol=coin+pairing)['lastPrice']


if __name__ == '__main__':
    while True:
        # get the posts from reddit
        posts = get_post()

        # check if the order file exists and load the current orders
        if os.path.isfile('order.json'):
            order = load_order('order.json')
        else:
            order = {}

        # check if the reddit posts files exist and load them
        if os.path.isfile('reddit_posts.json'):
            saved_posts = load_posts('reddit_posts.json')

            # this will return the number of new posts we found on reddit
            # compared to the ones stored
            new_posts = compare_posts(posts, saved_posts)

            if new_posts > -1:
                print("New posts detected, fetching new posts...")

                # store the posts if they are new
                store_posts(posts)
                # find posts with matching keywords
                key_posts = find_keywords(posts, keywords)
                # determine the sentiment for each post
                sentiment = analyse_posts(key_posts)
                # return the compoundavg sentiment, grouped by symbol
                analyzed_coins = get_avg_sentiment(sentiment)

                print(f'Found matching  keywords with the following sentiments: {analyzed_coins}')

                for coin in analyzed_coins:

                    # prepare to buy if the sentiment of each coin is greater than 0
                    # and the coin hasn't been bought already
                    if analyzed_coins[coin] > 0 and coin not in order:
                        print(f'{coin} sentiment is positive: {analyzed_coins[coin]}, preparing to buy...')

                        price = get_price(coin, config['TRADE_OPTIONS']['PAIRING'])
                        volume = convert_volume(coin+config['TRADE_OPTIONS']['PAIRING'], config['TRADE_OPTIONS']['QUANTITY'],price)

                        try:
                            # Run a test trade if true
                            if config['TRADE_OPTIONS']['TEST']:
                                order[coin] = {
                                            'symbol':coin+config['TRADE_OPTIONS']['PAIRING'],
                                            'price':price,
                                            'volume':volume,
                                            'time':datetime.timestamp(datetime.now())
                                            }

                                print('PLACING TEST ORDER')
                            else:
                                order[coin] = create_order(coin+config['TRADE_OPTIONS']['PAIRING'], volume)

                        except Exception as e:
                            print(e)

                        else:
                            print(f'Order created with {volume} on {coin}')

                            store_order('order.json', order)
                    else:
                        print(f'Sentiment for {coin} is negative or {coin} is currently in portfolio')

            time.sleep(config['TRADE_OPTIONS']['RUN_EVERY']*60)
        else:
            print("Running first iteration, fetching posts...")
            store_posts(posts)
