import json
path = ""
try:
    import os
    path = os.path.abspath(".")
    with open(path + '/lwConfig.json', 'r') as myfile:
        data = myfile.read()
except:
    path = '/home/pi/Desktop/lwBot'
    with open(path + '/lwCconfig.json', 'r') as myfile:
        data = myfile.read()


config = json.loads(data)
ownerID = config["owner_id"]
upvotesForPin = config["upvotes_for_pin"]
deleteAfter = config["delete_after_days"]
token = config["discord_token"]
statusMessage = config["status_message"]
memeChannelID = config["meme_channel_id"]
upvoteEmoji = config["upvote_emoji"]
downoteEmoji = config["downote_emoji"]
prefix = config["prefix"]
deleteEmojiName = config["delete_emoji_name"]
latestGmoNewsNumber = config["latest_gmo_news_number"]
newsChannelID = config["news_channel_id"]
gmoRoleID = config["gmo_role_id"]
serverID = config["server_id"]