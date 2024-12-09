from googleapiclient.discovery import build
# Replace with your YouTube Data API key
API_KEY = 'AIzaSyAk61e0vXHzb_d8kIegfJpsUUY6YXD8oV4'
# Function to extract channel ID, category ID, and default audio language from video ID
def get_video_details(video_id):
    youtube = build('youtube', 'v3', developerKey=API_KEY)
    # Make a request to the YouTube API
    request = youtube.videos().list(
        part='snippet',
        id=video_id
    )
    response = request.execute()
    # Extract channel ID, category ID, and default audio language from the response
    if 'items' in response and len(response['items']) > 0:
        video_details = response['items'][0]['snippet']
        channel_id = video_details['channelId']
        category_id = video_details['categoryId']
        default_audio_language = video_details.get('defaultAudioLanguage', 'Unknown')
        return channel_id, category_id, default_audio_language
    else:
        return None, None, None
# Function to extract country from channel ID
def get_channel_country(channel_id):
    youtube = build('youtube', 'v3', developerKey=API_KEY)
    # Make a request to the YouTube API
    request = youtube.channels().list(
        part='snippet',
        id=channel_id
    )
    response = request.execute()
    # Extract country from the response
    if 'items' in response and len(response['items']) > 0:
        channel_details = response['items'][0]['snippet']
        country = channel_details.get('country', 'Unknown')
        return country
    else:
        return None
if __name__ == "__main__":
    video_id = input("Enter the YouTube video ID: ")
    channel_id, category_id, default_audio_language = get_video_details(video_id)
    if channel_id and category_id:
        print(f"Channel ID: {channel_id}")
        print(f"Category ID: {category_id}")
        print(f"Default Audio Language: {default_audio_language}")
        # Get country from channel ID
        country = get_channel_country(channel_id)
        if country:
            print(f"Country: {country}")
    else:
        print("Invalid video ID or video not found.")