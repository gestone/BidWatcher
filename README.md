# BidWatcher
A simple listing watcher used to scour listings on Ebay and sends text messages via Twilio when bids are almost up. Specify a search entry to search on Ebay, a maximum bid price along with a max with shipping, and the number of milliseconds before the auction is over to be notified as well as your phone number.

To get this to run, note that you must have your `TWILIO_ACCOUNT_SID` and `TWILIO_AUTH_TOKEN` to have Twilio to work as noted in their [documentation](https://github.com/twilio/twilio-python). `TWILIO_PHONE_NUMBER`, the Twilio phone number the text message is sent from must also be set.

USAGE:

`python bid_watcher.py SEARCH_ENTRY MAX_BID_PRICE MAX_WITH_SHIPPING MILLISECONDS_BEFORE_NOTIF PHONE_NUMBER_1 PHONE_NUMBER_2 ...`
