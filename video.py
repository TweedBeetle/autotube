import json
import os
import shutil
import uuid

from googleapiclient.http import MediaFileUpload

FRAME_RATE = 24  # todo: tidy


def close_clip(vidya_clip):
    # noinspection PyBroadException
    try:
        vidya_clip.reader.close()
        del vidya_clip.reader
        if vidya_clip.audio is not None:
            vidya_clip.audio.reader.close_proc()
            del vidya_clip.audio
        del vidya_clip
    except Exception:
        # sys.exc_clear()
        pass


class YoutubeVideo:
    def __init__(self, title, description, tags, category_id, video_location, thumbnail_location=None, language_code='en'):
        self.title = title
        self.description = description
        self.tags = tags
        self.category_id = category_id
        self.video_location = video_location
        self.thumbnail_location = thumbnail_location
        self.language_code = language_code
        self.uploaded = False

    def __eq__(self, other):
        return all([
            self.title == other.title,
            self.description == other.description,
            self.tags == other.tags,
            self.category_id == other.category_id,
            self.video_location == other.video_location,
            self.thumbnail_location == other.thumbnail_location,
            self.language_code == other.language_code,
        ])

    def get_id(self):
        return f'{self.title} - {self.language_code}'

    def backup(self, database):
        database.backup(self)

    def get_upload_snippet(self):
        return {
            'description': self.description,
            # 'title': self.title.replace('"', '-').replace("'", '-'),
            'title': self.title[:100],
            'defaultLanguage': self.language_code,
            'defaultAudioLanguage': self.language_code,
        }

    def upload_to_yt_account(self, yt_account, private=True, playlist_ids=None):

        # Disable OAuthlib's HTTPS verification when running locally.
        # *DO NOT* leave this option enabled in production.
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

        snippet = self.get_upload_snippet()

        if len(snippet['title']) > 100:
            # todo: log
            snippet['title'] = snippet['title'][:100]

        if self.category_id is not None:
            snippet['categoryId'] = str(self.category_id)

        if self.tags is not None:
            # snippet['tags'] = [tag.encode('utf-8') for tag in self.tags]
            snippet['tags'] = self.tags

        responses = dict(video=None, thumbnail=None, playlists=list())

        video_request = yt_account.client.videos().insert(
            part='snippet,status',
            body={
                'snippet': snippet,
                'status': {
                    'privacyStatus': 'private' if private else 'public'
                }
            },

            media_body=MediaFileUpload(self.video_location)
        )

        responses['video'] = video_request.execute()

        if self.thumbnail_location is not None:
            thumbnail_request = yt_account.client.thumbnails().set(
                videoId=responses['video']['id'],

                media_body=MediaFileUpload(self.thumbnail_location, resumable=True)
            )
            responses['thumbnail'] = thumbnail_request.execute()

        for playlist_id in playlist_ids:
            playlist_request = yt_account.client.playlistItems().insert(
                part="snippet",
                body={
                    "snippet": {
                        "playlistId": playlist_id,
                        "position": 0,
                        "resourceId": {
                            "kind": "youtube#video",
                            "videoId": responses['video']['id']
                        }
                    }
                }
            )
            responses['playlists'].append(playlist_request.execute())

        return responses

    def get_folder_name(self):
        return str(uuid.uuid4())

    def get_metadata(self):

        return dict(
            title=self.title,
            description=self.description,
            tags=self.tags,
            category_id=self.category_id,
            language_code=self.language_code,
        )

    def save(self, directory, move=False, folder_name=None):

        folder_name = self.get_folder_name() if folder_name is None else folder_name

        folder = os.path.join(directory, folder_name)
        os.mkdir(folder)

        with open(os.path.join(folder, 'metadata.json'), 'w', encoding='utf-8') as f:
            json.dump(self.get_metadata(), f)

        delete_or_copy = shutil.move if move else shutil.copy

        if self.thumbnail_location is not None:
            thumbnail_file_name = os.path.split(self.thumbnail_location)[-1]
            delete_or_copy(self.thumbnail_location, os.path.join(folder, thumbnail_file_name))

        if self.video_location is not None:
            video_file_name = os.path.split(self.video_location)[-1]
            delete_or_copy(self.video_location, os.path.join(folder, video_file_name))


class PreexistingVideo(YoutubeVideo):
    def __init__(self, source_folder_location):

        self.source_folder_location = source_folder_location

        video_location, thumbnail_location = self.get_media_locations()

        metadata = self.load_metadata()

        super().__init__(
            title=metadata['title'],
            description=metadata['description'],
            tags=metadata['tags'],
            category_id=metadata['category_id'],
            video_location=video_location,
            thumbnail_location=thumbnail_location,
            language_code=metadata['language_code']
        )

    def get_media_locations(self):

        file_names = os.listdir(self.source_folder_location)

        video_file_names = list(filter(lambda x: x.endswith('.mp4'), file_names))
        image_file_names = list(filter(lambda x: x.endswith('.jpg'), file_names))

        if len(video_file_names) == 0:
            raise RuntimeError(f'No video files were found in the given folder "{self.source_folder_location}"')
        elif len(video_file_names) > 1:
            raise RuntimeError(f'There were to many videos in the given folder "{self.source_folder_location}"')

        if len(image_file_names) == 0:
            raise RuntimeError(f'No image files were found in the given folder "{self.source_folder_location}"')
        elif len(image_file_names) > 1:
            raise RuntimeError(f'There were to many images in the given folder "{self.source_folder_location}"')

        video_location = os.path.join(self.source_folder_location, video_file_names[0])
        thumbnail_location = os.path.join(self.source_folder_location, image_file_names[0])

        return video_location, thumbnail_location

    def load_metadata(self):
        assert 'metadata.json' in os.listdir(self.source_folder_location)
        title_location = os.path.join(self.source_folder_location, 'metadata.json')
        with open(title_location, 'r', encoding="utf-8") as f:
            metadata = json.load(f)

        return metadata


class InvalidQuestionError(RuntimeError):
    pass

if __name__ == '__main__':
    pass