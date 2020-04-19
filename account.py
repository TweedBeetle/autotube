import googleapiclient.discovery
from google.oauth2.credentials import Credentials


class YouTubeAccount:
    def __init__(self, credentials: Credentials):
        api_service_name = 'youtube'
        api_version = 'v3'

        self.client = googleapiclient.discovery.build(api_service_name, api_version, credentials=credentials)

    def make_playlist(self, title, description=None, tags=None, default_language=None, private=True):
        snippet = {
            'title': title,
        }

        if description is not None:
            snippet['description'] = description

        if tags is not None:
            snippet['tags'] = tags

        if default_language is not None:
            snippet['defaultLanguage'] = default_language

        request = self.client.playlists().insert(
            part='snippet,status',
            body={
                'snippet': snippet,
                'status': {
                    'privacyStatus': 'private' if private else 'public'
                }
            }
        )

        return request.execute()

    def get_playlist_ids_by_name(self, filter_func):
        response = self.client.playlists().list(part="snippet", mine=True).execute()

        title_id_map = {item['snippet']['title']: item['id'] for item in response['items']}

        ids = []

        for title, id in title_id_map.items():
            if filter_func(title):
                ids.append(id)

        return ids

    def get_playlist_id_by_name(self, filter_func):
        ids = self.get_playlist_ids_by_name(filter_func)
        assert len(ids) == 1
        return ids[0]