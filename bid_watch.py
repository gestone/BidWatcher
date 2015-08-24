from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
from twilio.rest import TwilioRestClient

import time
import threading
import math
import sys
import urllib2
import urlparse
import os


SEARCH_ENTRY = sys.argv[1]
MAX_BID_PRICE = float(sys.argv[2]) # Without shipping
MAX_TOTAL_PRICE = float(sys.argv[3]) # With shipping cost
MILLISECONDS_UNTIL_NOTIF = long(sys.argv[4]) # How many milliseconds there will be left for a bid before a text message is sent off 
PHONE_NUMBERS = sys.argv[5:]
TITLE_PREFIX_OFFSET = 26 # Offset into the actual item title

seen_items = set()
browser = webdriver.Firefox()
client = TwilioRestClient()
	 
""" Gets all the listings that have not been seen yet """
def get_listings():
	browser.get('http://ebay.com/')
	search_box = browser.find_element_by_id('gh-ac')
	print "Searching for %s..." % SEARCH_ENTRY

	search_box.send_keys(SEARCH_ENTRY + Keys.RETURN)
	
	# Feed in the page source into BeautifulSoup to figure out which ones it should explore
	soup = BeautifulSoup(browser.page_source, "html.parser")
	
	all_listings = soup.find("ul", id="ListViewInner").find_all("li", r=True)
	
	# Build a list of URLS to explore after analyzing each listing
	explore_listings = []

	for listing in all_listings:
		
		# Find the price first to see if it is plausable to even bid
		price_info = float(listing.select_one("span.bold").string.replace("$", ""))

		if price_info < MAX_BID_PRICE:
			listing_title_url = listing.select_one("h3.lvtitle a")
			listing_name = listing_title_url.get("title")[TITLE_PREFIX_OFFSET:]
			listing_URL = listing_title_url.get("href")
			
			# Get item hash from parsed GET request in the URL to make sure that we're not sending
			# multiple notifications for the same item
			item_hash = urlparse.parse_qs(urlparse.urlparse(listing_URL).query)['hash'][0]

			# Check that the item hasn't been seen yet...
			if item_hash not in seen_items and "SATURDAY" in listing_name.upper():
				seen_items.add(item_hash)
				explore_listings.append((price_info, listing_name, listing_URL))
				
	# Give priority to the elements that have a lower price
	# Compose a list omitting the PRICE because current bid price is not the 
	# price that we're going to bid for.
	return ([(x[1], x[2]) for x in sorted(explore_listings)])


"""Iterates through each listing and spawns a new thread to possibly notify a user about when a bid is going to end.
The user will be notified MILLISECONDS_UNTIL_NOTIF milliseconds before the bid is going to close. 

Keyword arguments:
listings -- all the listings to be checked

"""
def analyze_listings(listings):
	# Hit each of the urls to check out the listing
	for listing in listings:
		listing_name = listing[0]
		url_listing = listing[1]

		browser.get(url_listing)
		soup = BeautifulSoup(browser.page_source, "html.parser")
		total_price = find_price(soup)

		if total_price < MAX_TOTAL_PRICE:
			epoch_time = soup.find("span", class_="timeMs").get("timems")
			time_until_notif = int(epoch_time) - int(round(time.time() * 1000))

			# No negative time for scheduling. If time until bid is close enough to be done,
			# send the notification immediately
			if time_until_notif < MILLISECONDS_UNTIL_NOTIF:
				send_text_message(url_listing, listing_name, total_price)
			else:
				time_until_notif -= MILLISECONDS_UNTIL_NOTIF
				time_until_notif = math.ceil(time_until_notif / 1000.0)
				print "Found a new listing! Will notify users in %s minutes " % math.ceil(time_until_notif / 60000.0)
				threading.Timer(time_until_notif, check_price, (url_listing, listing_name)).start()

"""Checks the price of the bid again before sending off a notification just in case the bid has changed

Keyword arguments:
url -- the url to link to be checked for the bid

"""
def check_price(url, listing_title):
	soup = BeautifulSoup(urllib2.urlopen(url), "html.parser")
	current_price = find_price(soup)
	if current_price < MAX_TOTAL_PRICE:
		send_text_message(url, listing_title, current_price)

"""Finds the price of the current item in question including the shipping cost.

Keyword arguments:
soup -- contains the HTML from viewing the current item to be extracted to find the price

"""
def find_price(soup):
	
	# Find the minimum price to bid
	price_text = soup.find("div", class_="notranslate u-flL bid-note")
	if price_text is not None: 
		min_bid_price = float(price_text.string[10:15])

		# The total price will never be used in bidding, but only in considering the
		# whether or not if it is worth it to bid.
		total_price = min_bid_price
		
		shipping = soup.find("span", id="fshippingCost")

		# Check to see if the shipping cost has already been calculated
		if shipping is not None:
			shipping_text = shipping.find("span").string
			# Now check to add on shipping, otherwise do nothing
			if shipping_text != "FREE":
				total_price += float(shipping_text.replace("$", ""))
			return total_price
		else:
			return total_price + 5.75 # Assume it's not too far away...
	else:
		return sys.maxint 


	
"""Sends a text message to a phone with the url to the bid, the title of the listing, and the current price (with shipping included) that the user would have to bid for.

Keyword arguments:
url -- the url to bid for the given item
listing_title -- the title of the listing
current_price -- the lowest price the user could get this item for including shipping
"""
def send_text_message(url, listing_title, current_price):
	minutes = str(MILLISECONDS_UNTIL_NOTIF / 60000) + " minutes"
	current_price = '%.2f' % current_price
	msg = "A bid for \"%s\" is available in %s for $%s. Go to the url: %s to bid" % (listing_title, minutes, current_price, url)
	for phone_number in PHONE_NUMBERS:
		print "Sent a notification to %s about listing: %s " % (phone_number, listing_title)
		client.messages.create(to = phone_number, from_ = os.environ['TWILIO_PHONE_NUMBER'], body = msg)


def main():
	valid_listings = get_listings()
	if not valid_listings:
		print "No new listings found! Trying again in 60 seconds..."
	else:
		analyze_listings(valid_listings)
		print "Finished analyzing new listings!"
	threading.Timer(60, main).start()

if __name__ == "__main__":
	main()
