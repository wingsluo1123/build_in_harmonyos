"""
Stateful, in-memory stand-in for the Mastodon REST API.

toot's upstream suite collects 152 cases; the 114 in ``tests/integration/`` are
skipped unless ``TOOT_TEST_BASE_URL`` points at a running instance. A real
instance needs Rails + PostgreSQL + Redis + Elasticsearch + ffmpeg + a JS
toolchain, none of which exist on HarmonyOS PC, so this module serves the HTTP
contract described at https://docs.joinmastodon.org/api/ well enough for the
unmodified upstream tests to exercise the client code paths for real.

Standard library only: it is started as a plain subprocess from the Conan
recipe's ``build()`` and must not pull extra dependencies into the build
environment. It is test support and is never packaged.

Run it directly for local iteration::

    python3 test_support/mastodon_api_stub.py --port 3000
"""

import argparse
import html
import json
import re
import struct
import sys
import threading
import uuid
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlencode

try:
    from dateutil.parser import parse as parse_date
except ImportError:
    try:
        from email.utils import parsedate_to_datetime as parse_date  # noqa
    except ImportError:
        parse_date = None

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".apng", ".bmp"}
VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".m4v", ".ogv", ".avi", ".mkv"}

# tests/assets/small.webm is 560x320 and 5 seconds long, and upstream asserts
# exactly those numbers: this is what Mastodon's ffmpeg probe reports for it.
VIDEO_META = {"duration": 5.0, "width": 560, "height": 320}

HASHTAG_RE = re.compile(r"(?:(?<=\s)|^)#([\w]+)")
MENTION_RE = re.compile(r"(?:(?<=\s)|^)@([\w.-]+)")

DEFAULT_LIMIT = 15
MAX_LIMIT = 40

VISIBILITIES = ("public", "unlisted", "private", "direct")


def utcnow():
    return datetime.now(timezone.utc)


def timestamp(value=None):
    value = value or utcnow()
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def parse_instant(value):
    if not value:
        return None
    if parse_date is not None:
        try:
            return parse_date(value)
        except (ValueError, TypeError):
            return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def truthy(value):
    return str(value).lower() in ("true", "1", "yes", "on")


class ApiFail(Exception):
    def __init__(self, status, message, description=None):
        super().__init__(message)
        self.status = status
        self.message = message
        self.description = description


class Ids:
    """Mastodon-like ids: fixed width decimal, monotonically increasing."""

    def __init__(self):
        self._counter = int(utcnow().timestamp())
        self._lock = threading.Lock()

    def next(self):
        with self._lock:
            self._counter += 1
            return str(100000000000000000 + self._counter)


class User:
    def __init__(self, store, username, email, password, locale):
        self.id = store.ids.next()
        self.username = username.lower()
        self.email = email
        self.password = password
        self.created_at = utcnow()
        self.display_name = ""
        self.note = ""
        self.locked = False
        self.bot = False
        self.discoverable = True
        self.avatar = None
        self.header = None
        self.source = {"privacy": "public", "sensitive": False, "language": locale or "en"}
        self.following = set()
        self.followers = set()
        self.muting = set()
        self.blocking = set()
        self.blocked_by = set()
        self.lists = set()
        self.featured_tags = {}
        self.followed_tags = set()
        self.pinned = set()
        self.bookmarks = []
        self.favourites = []

    @property
    def acct(self):
        return self.username


class Media:
    def __init__(self, store, description):
        self.id = store.ids.next()
        self.description = description
        self.type = "image"
        self.extension = ".png"
        self.width = None
        self.height = None
        self.duration = None
        self.small_width = None
        self.small_height = None


class Poll:
    def __init__(self, store, options, multiple, expires_in, hide_totals):
        self.id = store.ids.next()
        self.options = [{"title": option, "votes": 0} for option in options]
        self.multiple = bool(multiple)
        self.hide_totals = bool(hide_totals)
        self.expires_at = utcnow() + timedelta(seconds=int(expires_in or 24 * 3600))
        self.voters = {}

    @property
    def votes_count(self):
        return sum(option["votes"] for option in self.options)

    def option_json(self, option):
        return {"title": option["title"], "votes_count": option["votes"] if not self.hide_totals else None}


class Status:
    def __init__(self, store, author, text, visibility, application):
        self.id = store.ids.next()
        self.author = author
        self.text = text or ""
        self.visibility = visibility
        self.created_at = utcnow()
        self.sensitive = False
        self.spoiler_text = ""
        self.language = "en"
        self.media = []
        self.poll = None
        self.in_reply_to_id = None
        self.reblog_of = None
        self.application = application
        self.favourites = set()
        self.reblogs = set()
        self.deleted = False

    @property
    def content(self):
        if not self.text:
            return ""
        escaped = html.escape(self.text, quote=False).replace("\n", "<br />")
        return "<p>" + escaped + "</p>"

    @property
    def tag_names(self):
        return [name.lower() for name in HASHTAG_RE.findall(self.text)]

    @property
    def mention_names(self):
        return [name.lower() for name in MENTION_RE.findall(self.text)]


class Scheduled:
    def __init__(self, store, author, params, when):
        self.id = store.ids.next()
        self.author = author
        self.params = params
        self.scheduled_at = when


class Store:
    def __init__(self):
        self.lock = threading.RLock()
        self.ids = Ids()
        self.apps = {}
        self.app_tokens = {}
        self.tokens = {}
        self.users = {}
        self.usernames = {}
        self.statuses_by_id = {}
        self.published = []
        self.scheduled = {}
        self.media = {}
        self.polls = {}
        self.lists = {}
        self.tags = {}
        self.notifications = []

    # -- collections -------------------------------------------------------

    def statuses(self):
        return [self.statuses_by_id[i] for i in self.published if i in self.statuses_by_id]

    def newest_first(self):
        return list(reversed(self.statuses()))

    def published_ids(self):
        return set(self.published)

    # -- accounts ----------------------------------------------------------

    def register_app(self, name, website, redirect_uris, scopes):
        client_id = uuid.uuid4().hex[:16]
        app = {
            "id": client_id,
            "name": name or "toot",
            "website": website or "",
            "client_id": client_id,
            "client_secret": uuid.uuid4().hex,
            "redirect_uri": redirect_uris,
            "scopes": scopes,
        }
        self.apps[client_id] = app
        return app

    def issue_user_token(self, user, app):
        token = uuid.uuid4().hex
        self.tokens[token] = (user, app)
        return token

    def issue_app_token(self, app):
        token = "app-" + uuid.uuid4().hex
        self.app_tokens[token] = app["client_id"]
        return token

    def add_user(self, user):
        self.users[user.id] = user
        self.usernames[user.username] = user
        return user

    # -- statuses ----------------------------------------------------------

    def publish(self, status):
        self.statuses_by_id[status.id] = status
        self.published.append(status.id)

    def unpublish(self, status):
        status.deleted = True
        if status.id in self.published:
            self.published.remove(status.id)
        for user in self.users.values():
            if status.id in user.bookmarks:
                user.bookmarks.remove(status.id)
            if status.id in user.favourites:
                user.favourites.remove(status.id)
            user.pinned.discard(status.id)

    def reblog_of(self, user, original):
        for status in self.statuses():
            if status.reblog_of is original and status.author is user and not status.deleted:
                return status
        return None

    def replies(self, status):
        return [
            s for s in self.statuses()
            if s.in_reply_to_id == status.id and not s.deleted
        ]

    def tag(self, name):
        key = name.lower()
        return self.tags.setdefault(key, {"name": key, "uses": 0, "id": self.ids.next()})

    def notify(self, recipient, type_, actor=None, status=None):
        notification = {
            "id": self.ids.next(),
            "recipient": recipient,
            "type": type_,
            "created_at": timestamp(),
            "account": actor,
            "status": status,
        }
        self.notifications.append(notification)
        return notification

    def notifications_for(self, user):
        return [n for n in self.notifications if n["recipient"] is user]

    # -- visibility --------------------------------------------------------

    def sees(self, status, viewer, audience=None):
        """Whether ``viewer`` may see ``status`` in a timeline."""
        if status.deleted:
            return False
        if audience is not None and status.author.id not in audience:
            return False
        if status.visibility in ("public", "unlisted"):
            return True
        if viewer is None:
            return False
        if status.author is viewer:
            return True
        if status.visibility == "private":
            return status.author.id in viewer.following
        return viewer.id in status.author.followers


ROUTES = []


def route(method, pattern):
    def decorator(fn):
        ROUTES.append((method, re.compile("^" + pattern + "$"), fn))
        return fn
    return decorator


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    store = None
    verbose = False

    # -- plumbing ----------------------------------------------------------

    def log_message(self, fmt, *args):
        if self.verbose:
            sys.stderr.write("stub: " + (fmt % args) + "\n")

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def do_PUT(self):
        self._dispatch("PUT")

    def do_PATCH(self):
        self._dispatch("PATCH")

    def do_DELETE(self):
        self._dispatch("DELETE")

    def do_HEAD(self):
        self._dispatch("GET")

    def _read_body(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        return self.rfile.read(length) if length > 0 else b""

    def _dispatch(self, method):
        store = self.store
        path, query = _split_url(self.path)
        self.path_only = path
        self.params = parse_qs(query, keep_blank_values=True)
        self.query = {key: values[-1] for key, values in self.params.items()}
        self.json_body = {}
        self.form = {}
        self.files = {}
        self.host = self.headers.get("Host") or "localhost:3000"
        self._parse_body(self._read_body())

        self.token = None
        authorization = self.headers.get("Authorization") or ""
        if authorization.lower().startswith("bearer "):
            self.token = authorization[7:].strip()

        with store.lock:
            self.viewer, self.app = None, None
            if self.token:
                if self.token in store.tokens:
                    self.viewer, self.app = store.tokens[self.token]
                elif self.token in store.app_tokens:
                    self.app = store.apps.get(store.app_tokens[self.token])

            status, payload, headers = 404, {"error": "Record not found"}, {}
            for verb, pattern, fn in ROUTES:
                if verb != method or pattern.match(path) is None:
                    continue
                match = pattern.match(path)
                try:
                    result = fn(self, **match.groupdict())
                except ApiFail as fail:
                    body = {"error": fail.message}
                    if fail.description:
                        body["error_description"] = fail.description
                    result = (fail.status, body)
                if len(result) == 3:
                    status, payload, headers = result
                else:
                    status, payload = result
                    headers = {}
                break

        self._respond(status, payload, headers)

    def _parse_body(self, raw):
        if not raw:
            return
        content_type = self.headers.get("Content-Type") or ""
        if content_type.startswith("application/json"):
            try:
                data = json.loads(raw.decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                return
            if isinstance(data, dict):
                self.json_body = data
            return
        if content_type.startswith("multipart/form-data"):
            self._parse_multipart(raw, content_type)
            return
        if content_type.startswith("application/x-www-form-urlencoded"):
            for key, values in parse_qs(raw.decode("utf-8"), keep_blank_values=True).items():
                self.form[key] = values[-1]

    def _parse_multipart(self, raw, content_type):
        match = re.search(r'boundary="?([^";]+)"?', content_type)
        if not match:
            return
        boundary = ("--" + match.group(1)).encode("utf-8")
        for chunk in raw.split(boundary):
            if chunk.startswith(b"--") or chunk in (b"", b"\r\n"):
                continue
            chunk = chunk.lstrip(b"\r\n")
            head, sep, payload = chunk.partition(b"\r\n\r\n")
            if not sep:
                continue
            if payload.endswith(b"\r\n"):
                payload = payload[:-2]
            name = filename = mime = None
            for line in head.decode("latin-1").split("\r\n"):
                lower = line.lower()
                if lower.startswith("content-disposition:"):
                    name = _attr(line, "name")
                    filename = _attr(line, "filename")
                elif lower.startswith("content-type:"):
                    mime = line.split(":", 1)[1].strip()
            if not name:
                continue
            if filename is not None:
                self.files[name] = {"filename": filename, "content_type": mime, "payload": payload}
            elif name not in self.form:
                self.form[name] = payload.decode("utf-8", "replace")

    def _respond(self, status, payload, headers=None):
        if payload is None:
            body = b""
        elif isinstance(payload, (dict, list)):
            body = json.dumps(payload).encode("utf-8")
        else:
            body = str(payload).encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if body:
            self.wfile.write(body)

    # -- request helpers -----------------------------------------------------

    def q(self, name, default=None):
        return self.query.get(name, default)

    def ql(self, name):
        return self.params.get(name, [])

    def f(self, name, default=None):
        """Body field, from a JSON or form encoded body alike."""
        if name in self.json_body:
            value = self.json_body[name]
            return default if value is None else value
        if name in self.form:
            value = self.form[name]
            return default if value in ("", None) and default is not None else value
        return default

    def given(self, name):
        return name in self.json_body or name in self.form

    def require_user(self):
        if self.viewer is None:
            raise ApiFail(401, "The access token is invalid")
        return self.viewer

    def page(self, items, path, default_limit=DEFAULT_LIMIT):
        """Mastodon Link-header pagination over a newest-first list of entities."""
        limit = max(1, min(self._int("limit", default_limit), MAX_LIMIT))
        cursor = self.q("max_id") or self.q("min_id") or self.q("since_id")
        if cursor:
            index = _index_of(items, cursor)
            if index is not None:
                if self.q("max_id"):
                    items = items[index + 1:]
                else:
                    items = items[:index]
        page = items[:limit]
        rest = items[limit:]
        headers = {}
        if rest:
            base = "http://" + self.host + path
            tail = {key: value for key, value in self.query.items()
                    if key not in ("max_id", "min_id", "since_id")}
            tail["limit"] = str(limit)

            nxt = dict(tail)
            nxt["max_id"] = _id_of(rest[-1])
            prev = dict(tail)
            prev["min_id"] = _id_of(page[0]) if page else _id_of(rest[0])
            # rel="next" must come first: toot parses the header with a prefix match.
            headers["Link"] = '<{base}?{nxt}>; rel="next", <{base}?{prev}>; rel="prev"'.format(
                base=base, nxt=urlencode(nxt), prev=urlencode(prev))
        return page, headers

    def render_list(self, items, path, default_limit=DEFAULT_LIMIT):
        page, headers = self.page(items, path, default_limit)
        return 200, [self.render(item) for item in page], headers

    def render(self, item):
        if isinstance(item, Status):
            return self.status_json(item)
        if isinstance(item, User):
            return self.account_json(item, with_source=item is self.viewer)
        if isinstance(item, dict):
            return item
        return item

    def _int(self, name, default):
        try:
            return int(self.q(name))
        except (TypeError, ValueError):
            return default

    def url(self, *parts):
        return "http://" + self.host + "/" + "/".join(str(p) for p in parts)

    # -- serialisers ---------------------------------------------------------

    def account_json(self, user, with_source=False):
        avatar = user.avatar or self.url("avatars", "original", "missing.png")
        header = user.header or self.url("headers", "original", "missing.png")
        own = [s for s in self.store.statuses() if s.author is user]
        account = {
            "id": user.id,
            "username": user.username,
            "acct": user.acct,
            "display_name": user.display_name,
            "group": False,
            "url": self.url("@" + user.username),
            "note": "<p>" + html.escape(user.note, quote=False) + "</p>" if user.note else "",
            "avatar": avatar,
            "avatar_static": avatar,
            "header": header,
            "header_static": header,
            "locked": user.locked,
            "bot": user.bot,
            "discoverable": user.discoverable,
            "noindex": False,
            "fields": [],
            "emojis": [],
            "moved": None,
            "suspended": False,
            "limited": False,
            "created_at": timestamp(user.created_at),
            "last_status_at": own[-1].created_at.strftime("%Y-%m-%d") if own else None,
            "statuses_count": len(own),
            "followers_count": len(user.followers),
            "following_count": len(user.following),
        }
        if with_source:
            account["source"] = {
                "privacy": user.source["privacy"],
                "sensitive": bool(user.source["sensitive"]),
                "language": user.source["language"],
                "note": user.note,
                "fields": [],
                "follow_requests_count": 0,
                "hide_collections": False,
                "indexable": False,
            }
        return account

    def relationship_json(self, viewer, other):
        return {
            "id": other.id,
            "following": other.id in viewer.following,
            "showing_reblogs": True,
            "notifying": False,
            "languages": None,
            "followed_by": viewer.id in other.followers,
            "blocking": other.id in viewer.blocking,
            "blocked_by": viewer.id in other.blocked_by,
            "muting": other.id in viewer.muting,
            "muting_notifications": False,
            "requested": False,
            "requested_by": False,
            "domain_blocking": False,
            "endorsed": False,
            "note": "",
            "note_html": "",
        }

    def media_json(self, media):
        original = {}
        if media.width is not None:
            original["width"] = media.width
        if media.height is not None:
            original["height"] = media.height
        if media.width and media.height:
            original["size"] = "{}x{}".format(media.width, media.height)
            original["aspect"] = round(float(media.width) / float(media.height), 4)
        if media.duration is not None:
            original["duration"] = media.duration
            original["frame_rate"] = "30000/1001"

        small = {
            "width": media.small_width if media.small_width is not None else media.width,
            "height": media.small_height if media.small_height is not None else media.height,
        }
        small = {key: value for key, value in small.items() if value is not None}
        if small.get("width") and small.get("height"):
            small["size"] = "{}x{}".format(small["width"], small["height"])
            small["aspect"] = round(float(small["width"]) / float(small["height"]), 4)

        preview = ".png" if media.type == "video" else media.extension
        return {
            "id": media.id,
            "type": media.type,
            "url": self.url("media", media.id, "original" + media.extension),
            "preview_url": self.url("media", media.id, "small" + preview),
            "remote_url": None,
            "meta": {"original": original, "small": small},
            "description": media.description,
            "blurhash": None,
        }

    def poll_json(self, poll, viewer):
        own_votes = poll.voters.get(viewer.id, []) if viewer else []
        return {
            "id": poll.id,
            "expires_at": timestamp(poll.expires_at),
            "expired": poll.expires_at <= utcnow(),
            "multiple": poll.multiple,
            "votes_count": poll.votes_count,
            "voters_count": len(poll.voters),
            "options": [poll.option_json(option) for option in poll.options],
            "emojis": [],
            "voted": bool(own_votes),
            "own_votes": own_votes,
            "outdated": False,
        }

    def status_json(self, status, depth=0):
        viewer = self.viewer
        reblog = None
        if status.reblog_of is not None and depth < 1:
            reblog = self.status_json(status.reblog_of, depth + 1)

        parent = self.store.statuses_by_id.get(status.in_reply_to_id) if status.in_reply_to_id else None
        return {
            "id": status.id,
            "uri": self.url("@" + status.author.username, status.id),
            "created_at": timestamp(status.created_at),
            "account": self.account_json(status.author),
            "content": status.content,
            "visibility": status.visibility,
            "sensitive": status.sensitive,
            "spoiler_text": status.spoiler_text or "",
            "media_attachments": [self.media_json(m) for m in status.media],
            "application": status.application,
            "mentions": [
                {"id": other.id, "username": other.username, "acct": other.acct,
                 "url": self.url("@" + other.username)}
                for other in sorted(self.store.users.values(), key=lambda u: int(u.id))
                if other.username in status.mention_names
            ],
            "tags": [
                {"name": name, "url": self.url("tags", name)}
                for name in dict.fromkeys(status.tag_names)
            ],
            "emojis": [],
            "reblogs_count": len(status.reblogs),
            "favourites_count": len(status.favourites),
            "replies_count": len(self.store.replies(status)),
            "url": self.url("@" + status.author.username, status.id),
            "in_reply_to_id": status.in_reply_to_id,
            "in_reply_to_account_id": parent.author.id if parent else None,
            "reblog": reblog,
            "poll": None if status.poll is None else self.poll_json(status.poll, viewer),
            "card": None,
            "language": status.language,
            "edited_at": None,
            "favourited": bool(viewer) and status.id in viewer.favourites,
            "reblogged": bool(viewer) and viewer.id in status.reblogs,
            "muted": False,
            "bookmarked": bool(viewer) and status.id in viewer.bookmarks,
            "pinned": bool(viewer) and status.id in viewer.pinned,
            "filtered": [],
        }

    def scheduled_json(self, entry):
        return {
            "id": entry.id,
            "scheduled_at": timestamp(entry.scheduled_at),
            "params": dict(entry.params),
            "media_attachments": [],
        }

    def tag_json(self, tag, following=None):
        return {
            "name": tag["name"],
            "url": self.url("tags", tag["name"]),
            "history": [{"day": str(int(utcnow().timestamp())), "uses": str(tag["uses"]), "accounts": "1"}],
            "following": bool(following),
        }

    def featured_json(self, name, tag):
        return {
            "id": tag["id"],
            "name": name,
            "url": self.url("tags", name),
            "statuses_count": tag["uses"],
            "last_status_at": timestamp(),
        }

    def notification_json(self, notification):
        status = notification["status"]
        return {
            "id": notification["id"],
            "type": notification["type"],
            "created_at": notification["created_at"],
            "account": self.account_json(notification["account"]),
            "status": None if status is None else self.status_json(status),
        }

    def application_for(self):
        if self.app:
            return {"name": self.app["name"], "website": self.app["website"]}
        return None

    # -- instance / oauth ------------------------------------------------------

    @route("GET", r"/api/v1/instance")
    def instance(self):
        return 200, {
            "uri": self.host,
            "title": "toot integration test instance",
            "short_description": "A stub instance for running toot's upstream tests",
            "description": "A stub instance for running toot's upstream tests.",
            "email": "admin@" + self.host,
            "version": "4.2.8",
            "start_date": None,
            "urls": {"streaming_api": "ws://" + self.host},
            "stats": {
                "user_count": len(self.store.users),
                "status_count": len(self.store.published),
                "domain_count": 1,
            },
            "thumbnail": self.url("images", "thumbnail.png"),
            "languages": ["en"],
            "registrations": True,
            "approval_required": False,
            "invites_enabled": True,
            "configuration": {
                "statuses": {"max_characters": 500, "max_media_attachments": 4, "characters_reserved_per_url": 23},
                "media_attachments": {
                    "supported_mime_types": sorted(
                        ["image/png", "image/jpeg", "image/gif", "image/webp", "video/webm", "video/mp4"]
                    ),
                    "image_size_limit": 10485760,
                    "image_matrix_limit": 16777216,
                    "video_size_limit": 43621145,
                    "video_frame_rate_limit": 60,
                    "video_matrix_limit": 2304000,
                },
                "polls": {"max_options": 4, "max_characters_per_option": 50,
                          "min_expiration": 300, "max_expiration": 2629746},
            },
            "contact_account": None,
            "rules": [
                {"id": "1", "text": "Be nice to each other", "hint": ""},
                {"id": "2", "text": "No spam", "hint": ""},
            ],
        }

    @route("GET", r"/api/v2/instance")
    def instance_v2(self):
        _, body = self.instance()
        body = dict(body)
        body["domain"] = self.host
        body["version"] = {"number": "4.2.8", "compatibility": "mastodon"}
        return 200, body

    @route("POST", r"/api/v1/apps")
    def create_app(self):
        app = self.store.register_app(
            self.f("client_name", "toot"),
            self.f("website", ""),
            self.f("redirect_uris", "urn:ietf:wg:oauth:2.0:oob"),
            self.f("scopes", "read write follow"),
        )
        return 200, {
            "id": app["id"],
            "name": app["name"],
            "website": app["website"],
            "redirect_uri": app["redirect_uri"],
            "client_id": app["client_id"],
            "client_secret": app["client_secret"],
            "scopes": app["scopes"],
            "vapid_key": None,
        }

    @route("POST", r"/oauth/token")
    def oauth_token(self):
        grant = self.f("grant_type", "")
        app = self.store.apps.get(self.f("client_id"))
        if app is None or app["client_secret"] != self.f("client_secret"):
            raise ApiFail(400, "invalid_request", "Client authentication failed")

        if grant == "client_credentials":
            return 200, {
                "access_token": self.store.issue_app_token(app),
                "token_type": "Bearer",
                "scope": self.f("scope", "read write"),
                "created_at": int(utcnow().timestamp()),
            }

        if grant == "password":
            username = (self.f("username", "") or "").split("@")[0].lower()
            user = self.store.usernames.get(username)
            if user is None or user.password != self.f("password"):
                raise ApiFail(401, "invalid_grant", "Invalid email or password.")
            return 200, {
                "access_token": self.store.issue_user_token(user, app),
                "token_type": "Bearer",
                "scope": app["scopes"],
                "created_at": int(utcnow().timestamp()),
            }

        raise ApiFail(400, "unsupported_grant_type", "Unsupported grant type")

    @route("POST", r"/oauth/revoke")
    def oauth_revoke(self):
        self.store.tokens.pop(self.token, None)
        return 200, {}

    # -- accounts --------------------------------------------------------------

    @route("POST", r"/api/v1/accounts")
    def register(self):
        username = (self.f("username") or "").lower()
        password = self.f("password") or ""
        if not username or not password:
            raise ApiFail(422, "Validation failed: Username can't be blank")
        if username in self.store.usernames:
            raise ApiFail(422, "Validation failed: Email has already been taken")
        user = self.store.add_user(
            User(self.store, username, self.f("email", ""), password, self.f("locale", "en"))
        )
        return 200, {
            "access_token": self.store.issue_user_token(user, self.app),
            "token_type": "Bearer",
            "scope": "read write follow",
            "created_at": int(utcnow().timestamp()),
        }

    @route("GET", r"/api/v1/accounts/verify_credentials")
    def verify_credentials(self):
        user = self.require_user()
        return 200, self.account_json(user, with_source=True)

    @route("PATCH", r"/api/v1/accounts/update_credentials")
    def update_credentials(self):
        user = self.require_user()
        for name in ("display_name", "note"):
            if self.given(name):
                setattr(user, name, self.f(name, ""))
        for name in ("locked", "bot", "discoverable"):
            if self.given(name):
                setattr(user, name, truthy(self.f(name)))
        for name in ("avatar", "header"):
            upload = self.files.get(name)
            if upload is not None:
                extension = _extension(upload["filename"]) or ".png"
                setattr(user, name, self.url("system", name + "s", user.id,
                                             uuid.uuid4().hex[:12] + extension))
        if self.given("source[privacy]"):
            user.source["privacy"] = self.f("source[privacy]")
        if self.given("source[language]"):
            user.source["language"] = self.f("source[language]")
        if self.given("source[sensitive]"):
            user.source["sensitive"] = truthy(self.f("source[sensitive]"))
        return 200, self.account_json(user, with_source=True)

    @route("GET", r"/api/v1/accounts/relationships")
    def relationships(self):
        user = self.require_user()
        ids = self.ql("id[]") or ([self.q("id")] if self.q("id") else [])
        out = [self.relationship_json(user, self.store.users[i]) for i in ids if i in self.store.users]
        return 200, out

    @route("GET", r"/api/v1/accounts/lookup")
    def lookup(self):
        user = self.require_user()
        acct = (self.q("acct") or "").lstrip("@").lower().split("@")[0]
        found = self.store.usernames.get(acct)
        if found is None:
            raise ApiFail(404, "Record not found")
        return 200, self.account_json(found, with_source=found is user)

    @route("GET", r"/api/v1/accounts/(?P<account_id>[^/]+)")
    def account(self, account_id):
        found = self.store.users.get(account_id)
        if found is None:
            raise ApiFail(404, "Record not found")
        return 200, self.account_json(found, with_source=found is self.viewer)

    @route("GET", r"/api/v1/accounts/(?P<account_id>[^/]+)/(?P<action>lists|featured_tags)")
    def account_collection(self, account_id, action):
        self.require_user()
        return self.render_list([], "/api/v1/accounts/%s/%s" % (account_id, action))

    @route("GET", r"/api/v1/accounts/(?P<account_id>[^/]+)/statuses")
    def account_statuses(self, account_id):
        owner = self.store.users.get(account_id)
        if owner is None:
            raise ApiFail(404, "Record not found")
        exclude_replies = truthy(self.q("exclude_replies", "false"))
        exclude_reblogs = truthy(self.q("exclude_reblogs", "false"))
        items = []
        for status in self.store.newest_first():
            if status.author is not owner:
                continue
            if status.in_reply_to_id and exclude_replies:
                continue
            if status.reblog_of is not None and exclude_reblogs:
                continue
            if not self.store.sees(status, self.viewer):
                continue
            items.append(status)
        return self.render_list(items, "/api/v1/accounts/%s/statuses" % account_id)

    @route("POST", r"/api/v1/accounts/(?P<account_id>[^/]+)/(?P<action>follow|unfollow|mute|unmute|block|unblock)")
    def account_action(self, account_id, action):
        user = self.require_user()
        other = self.store.users.get(account_id)
        if other is None:
            raise ApiFail(404, "Record not found")

        if action == "follow":
            if account_id not in user.following:
                user.following.add(account_id)
                other.followers.add(user.id)
                self.store.notify(other, "follow", actor=user)
        elif action == "unfollow":
            user.following.discard(account_id)
            other.followers.discard(user.id)
        elif action == "mute":
            user.muting.add(account_id)
        elif action == "unmute":
            user.muting.discard(account_id)
        elif action == "block":
            user.blocking.add(account_id)
            other.blocked_by.add(user.id)
        elif action == "unblock":
            user.blocking.discard(account_id)
            other.blocked_by.discard(user.id)

        return 200, self.relationship_json(user, other)

    @route("GET", r"/api/v1/accounts/(?P<account_id>[^/]+)/(?P<action>following|followers|followed_by)")
    def account_follows(self, account_id, action):
        owner = self.store.users.get(account_id)
        if owner is None:
            raise ApiFail(404, "Record not found")
        if action == "following":
            ids = sorted(owner.following, key=int)
        else:
            ids = sorted(owner.followers, key=int)
        items = [self.store.users[i] for i in ids if i in self.store.users]
        return self.render_list(items, "/api/v1/accounts/%s/%s" % (account_id, action))

    @route("GET", r"/api/v1/mutes")
    def mutes(self):
        user = self.require_user()
        items = [self.store.users[i] for i in sorted(user.muting, key=int)]
        return self.render_list(items, "/api/v1/mutes")

    @route("GET", r"/api/v1/blocks")
    def blocks(self):
        user = self.require_user()
        items = [self.store.users[i] for i in sorted(user.blocking, key=int)]
        return self.render_list(items, "/api/v1/blocks")

    @route("GET", r"/api/v1/follow_requests")
    def follow_requests(self):
        self.require_user()
        return self.render_list([], "/api/v1/follow_requests")

    @route("POST", r"/api/v1/follow_requests/(?P<account_id>[^/]+)/(?P<action>authorize|reject)")
    def follow_request_action(self, account_id, action):
        user = self.require_user()
        other = self.store.users.get(account_id)
        if other is None:
            raise ApiFail(404, "Record not found")
        return 200, self.relationship_json(user, other)

    @route("GET", r"/api/v1/preferences")
    def preferences(self):
        user = self.require_user()
        return 200, {
            "posting:default:visibility": user.source["privacy"],
            "posting:default:sensitive": bool(user.source["sensitive"]),
            "posting:default:language": user.source["language"],
            "reading:expand:media": "default",
            "reading:expand:spoilers": False,
        }

    # -- statuses ----------------------------------------------------------------

    @route("POST", r"/api/v1/statuses")
    def create_status(self):
        user = self.require_user()
        text = self.f("status", "") or ""
        visibility = self.f("visibility", user.source["privacy"]) or "public"
        if visibility not in VISIBILITIES:
            raise ApiFail(422, "Record invalid")

        if self.given("scheduled_at"):
            when = parse_instant(self.f("scheduled_at"))
            if when is None:
                raise ApiFail(422, "Record invalid")
            if when.tzinfo is None:
                when = when.replace(tzinfo=timezone.utc)
            params = {
                "text": text,
                "visibility": visibility,
                "in_reply_to_id": self.f("in_reply_to_id"),
                "sensitive": bool(self.f("sensitive", False)),
                "spoiler_text": self.f("spoiler_text", "") or "",
                "language": self.f("language", "en") or "en",
                "media_ids": self.f("media_ids") or None,
            }
            entry = Scheduled(self.store, user, params, when)
            self.store.scheduled[entry.id] = entry
            return 200, self.scheduled_json(entry)

        ids = self.f("media_ids") or []
        if isinstance(ids, str):
            ids = [ids]
        attachments = [self.store.media[str(i)] for i in ids if str(i) in self.store.media]

        poll = None
        spec = self.json_body.get("poll")
        if isinstance(spec, dict):
            poll = Poll(self.store, spec.get("options") or [], spec.get("multiple"),
                        spec.get("expires_in"), spec.get("hide_totals"))
            self.store.polls[poll.id] = poll

        if not text and not attachments:
            raise ApiFail(422, "Validation failed: Text can't be blank")

        reply_to = self.f("in_reply_to_id")
        if reply_to and reply_to not in self.store.statuses_by_id:
            raise ApiFail(404, "Record not found")

        status = Status(self.store, user, text, visibility, self.application_for())
        status.sensitive = bool(self.f("sensitive", False))
        status.spoiler_text = self.f("spoiler_text", "") or ""
        status.language = self.f("language", "en") or "en"
        status.media = attachments
        status.poll = poll
        status.in_reply_to_id = reply_to
        self.store.publish(status)

        for name in status.tag_names:
            self.store.tag(name)

        mentioned = set()
        for name in status.mention_names:
            other = self.store.usernames.get(name)
            if other is not None and other is not user and other.id not in mentioned:
                mentioned.add(other.id)
                self.store.notify(other, "mention", actor=user, status=status)

        return 200, self.status_json(status)

    @route("GET", r"/api/v1/scheduled_statuses")
    def scheduled_statuses(self):
        user = self.require_user()
        items = sorted((s for s in self.store.scheduled.values() if s.author is user),
                       key=lambda s: s.scheduled_at)
        return 200, [self.scheduled_json(s) for s in items]

    @route("GET", r"/api/v1/scheduled_statuses/(?P<scheduled_id>[^/]+)")
    def scheduled_status(self, scheduled_id):
        user = self.require_user()
        entry = self.store.scheduled.get(scheduled_id)
        if entry is None or entry.author is not user:
            raise ApiFail(404, "Record not found")
        return 200, self.scheduled_json(entry)

    @route("GET", r"/api/v1/statuses/(?P<status_id>[^/]+)/source")
    def status_source(self, status_id):
        status = self._existing(status_id)
        return 200, {"id": status.id, "text": status.text, "spoiler_text": status.spoiler_text}

    @route("GET", r"/api/v1/statuses/(?P<status_id>[^/]+)/context")
    def status_context(self, status_id):
        status = self._existing(status_id)
        ancestors = []
        parent = self.store.statuses_by_id.get(status.in_reply_to_id) if status.in_reply_to_id else None
        while parent is not None and parent.id not in [a.id for a in ancestors]:
            ancestors.append(parent)
            parent = self.store.statuses_by_id.get(parent.in_reply_to_id) if parent.in_reply_to_id else None
        ancestors.reverse()

        descendants = []
        frontier = self.store.replies(status)
        seen = {status.id}
        while frontier:
            nxt = []
            for reply in frontier:
                if reply.id in seen:
                    continue
                seen.add(reply.id)
                descendants.append(reply)
                nxt.extend(self.store.replies(reply))
            frontier = sorted(nxt, key=lambda s: int(s.id))
        return 200, {
            "ancestors": [self.status_json(s) for s in ancestors],
            "descendants": [self.status_json(s) for s in descendants],
        }

    @route("GET", r"/api/v1/statuses/(?P<status_id>[^/]+)/reblogged_by")
    def reblogged_by(self, status_id):
        status = self._existing(status_id)
        items = [self.store.users[i] for i in sorted(status.reblogs, key=int)]
        return self.render_list(items, "/api/v1/statuses/%s/reblogged_by" % status_id)

    @route("GET", r"/api/v1/statuses/(?P<status_id>[^/]+)/favourited_by")
    def favourited_by(self, status_id):
        status = self._existing(status_id)
        items = [self.store.users[i] for i in sorted(status.favourites, key=int)]
        return self.render_list(items, "/api/v1/statuses/%s/favourited_by" % status_id)

    def _existing(self, status_id):
        status = self.store.statuses_by_id.get(status_id)
        if status is None or status.deleted:
            raise ApiFail(404, "Record not found")
        return status

    @route("GET", r"/api/v1/statuses/(?P<status_id>[^/]+)")
    def get_status(self, status_id):
        return 200, self.status_json(self._existing(status_id))

    @route("PUT", r"/api/v1/statuses/(?P<status_id>[^/]+)")
    def edit_status(self, status_id):
        status = self._existing(status_id)
        user = self.require_user()
        if status.author is not user:
            raise ApiFail(403, "This action is not allowed")
        if self.given("status"):
            status.text = self.f("status", "")
        if self.given("sensitive"):
            status.sensitive = bool(self.f("sensitive", False))
        if self.given("spoiler_text"):
            status.spoiler_text = self.f("spoiler_text", "") or ""
        if self.given("language"):
            status.language = self.f("language")
        return 200, self.status_json(status)

    @route("DELETE", r"/api/v1/statuses/(?P<status_id>[^/]+)")
    def delete_status(self, status_id):
        status = self._existing(status_id)
        user = self.require_user()
        if status.author is not user:
            raise ApiFail(403, "This action is not allowed")
        payload = self.status_json(status)
        self.store.unpublish(status)
        return 200, payload

    @route("POST", r"/api/v1/statuses/(?P<status_id>[^/]+)/(?P<action>[a-z_]+)")
    def status_action(self, status_id, action):
        status = self._existing(status_id)
        user = self.require_user()

        if action == "favourite":
            status.favourites.add(user.id)
            if status.id not in user.favourites:
                user.favourites.insert(0, status.id)
            if status.author is not user:
                self.store.notify(status.author, "favourite", actor=user, status=status)
            return 200, self.status_json(status)

        if action == "unfavourite":
            status.favourites.discard(user.id)
            if status.id in user.favourites:
                user.favourites.remove(status.id)
            return 200, self.status_json(status)

        if action == "reblog":
            wrapper = self.store.reblog_of(user, status)
            if wrapper is None:
                wrapper = Status(self.store, user, "", self.f("visibility", "public") or "public",
                                 self.application_for())
                wrapper.reblog_of = status
                self.store.publish(wrapper)
                status.reblogs.add(user.id)
                if status.author is not user:
                    self.store.notify(status.author, "reblog", actor=user, status=status)
            payload = self.status_json(wrapper)
            payload["reblogged"] = True
            return 200, payload

        if action == "unreblog":
            wrapper = self.store.reblog_of(user, status)
            status.reblogs.discard(user.id)
            if wrapper is not None:
                self.store.unpublish(wrapper)
                self.store.statuses_by_id.pop(wrapper.id, None)
            payload = self.status_json(status)
            payload["reblogged"] = False
            payload["reblog"] = None
            return 200, payload

        if action in ("pin", "unpin"):
            if action == "pin":
                if len(user.pinned) >= 5:
                    raise ApiFail(422, "Validation failed: You cannot have more than 5 pinned statuses")
                user.pinned.add(status.id)
            else:
                user.pinned.discard(status.id)
            return 200, self.status_json(status)

        if action == "bookmark":
            if status.id not in user.bookmarks:
                user.bookmarks.insert(0, status.id)
            return 200, self.status_json(status)

        if action == "unbookmark":
            if status.id in user.bookmarks:
                user.bookmarks.remove(status.id)
            return 200, self.status_json(status)

        if action == "translate":
            return 200, {"content": status.content, "detected_source_language": status.language,
                         "provider": "stub"}

        if action in ("mute", "unmute"):
            return 200, self.status_json(status)

        raise ApiFail(404, "Record not found")

    # -- media -------------------------------------------------------------------

    @route("POST", r"/api/v2/media")
    @route("POST", r"/api/v1/media")
    def upload_media(self):
        self.require_user()
        upload = self.files.get("file")
        if upload is None:
            raise ApiFail(422, "Failed to attach file")

        media = Media(self.store, self.f("description") or None)
        extension = _extension(upload["filename"])
        dimensions = _png_dims(upload["payload"]) if extension == ".png" else None

        if extension in VIDEO_EXTENSIONS:
            media.type = "video"
            media.extension = ".mp4"
            media.width = VIDEO_META["width"]
            media.height = VIDEO_META["height"]
            media.duration = VIDEO_META["duration"]
            thumbnail = self.files.get("thumbnail")
            thumb_dims = _png_dims(thumbnail["payload"]) if thumbnail else None
            if thumb_dims:
                media.small_width, media.small_height = thumb_dims
        else:
            media.type = "gifv" if extension == ".gif" else "image"
            media.extension = extension
            if dimensions:
                media.width, media.height = dimensions

        self.store.media[media.id] = media
        return 200, self.media_json(media)

    @route("GET", r"/api/v1/media/(?P<media_id>[^/]+)")
    def get_media(self, media_id):
        self.require_user()
        media = self.store.media.get(media_id)
        if media is None:
            raise ApiFail(404, "Record not found")
        return 200, self.media_json(media)

    @route("PUT", r"/api/v1/media/(?P<media_id>[^/]+)")
    def update_media(self, media_id):
        self.require_user()
        media = self.store.media.get(media_id)
        if media is None:
            raise ApiFail(404, "Record not found")
        if self.given("description"):
            media.description = self.f("description")
        return 200, self.media_json(media)

    # -- timelines -----------------------------------------------------------------

    @route("GET", r"/api/v1/timelines/home")
    def home_timeline(self):
        user = self.require_user()
        audience = set(user.following) | {user.id}
        items = [s for s in self.store.newest_first()
                 if s.reblog_of is None and self.store.sees(s, user, audience)]
        return self.render_list(items, "/api/v1/timelines/home")

    @route("GET", r"/api/v1/timelines/public")
    def public_timeline(self):
        items = [s for s in self.store.newest_first()
                 if s.reblog_of is None and s.visibility == "public"]
        if truthy(self.q("only_media", "false")):
            items = [s for s in items if s.media]
        return self.render_list(items, "/api/v1/timelines/public")

    @route("GET", r"/api/v1/timelines/tag/(?P<tag>[^/]+)")
    def tag_timeline(self, tag):
        name = unquote(tag).lower().lstrip("#")
        items = [s for s in self.store.newest_first()
                 if s.reblog_of is None and s.visibility == "public" and name in s.tag_names]
        all_tags = [t.lower() for t in self.ql("all[]")]
        any_tags = [t.lower() for t in self.ql("any[]")]
        none_tags = [t.lower() for t in self.ql("none[]")]
        if all_tags:
            items = [s for s in items if all(t in s.tag_names for t in all_tags)]
        if none_tags:
            items = [s for s in items if not any(t in s.tag_names for t in none_tags)]
        if any_tags:
            items = [s for s in self.store.newest_first()
                     if s.reblog_of is None and s.visibility == "public"
                     and (name in s.tag_names or any(t in s.tag_names for t in any_tags))]
        if truthy(self.q("only_media", "false")):
            items = [s for s in items if s.media]
        return self.render_list(items, "/api/v1/timelines/tag/%s" % tag)

    @route("GET", r"/api/v1/timelines/list/(?P<list_id>[^/]+)")
    def list_timeline(self, list_id):
        user = self.require_user()
        entry = self.store.lists.get(list_id)
        if entry is None or entry["user"] is not user:
            raise ApiFail(404, "Record not found")
        audience = set(entry["account_ids"])
        items = [s for s in self.store.newest_first()
                 if s.reblog_of is None and s.author.id in audience and s.visibility != "direct"]
        return self.render_list(items, "/api/v1/timelines/list/%s" % list_id)

    @route("GET", r"/api/v1/timelines/link")
    def link_timeline(self):
        self.require_user()
        return self.render_list([], "/api/v1/timelines/link")

    @route("GET", r"/api/v1/trends/statuses")
    def trends_statuses(self):
        items = [s for s in self.store.newest_first() if s.visibility == "public"]
        return self.render_list(items, "/api/v1/trends/statuses")

    @route("GET", r"/api/v1/trends/tags")
    def trends_tags(self):
        return 200, []

    @route("GET", r"/api/v1/bookmarks")
    def bookmarks(self):
        user = self.require_user()
        items = [self.store.statuses_by_id[i] for i in user.bookmarks
                 if i in self.store.statuses_by_id and not self.store.statuses_by_id[i].deleted]
        return self.render_list(items, "/api/v1/bookmarks")

    @route("GET", r"/api/v1/favourites")
    def favourites(self):
        user = self.require_user()
        items = [self.store.statuses_by_id[i] for i in user.favourites
                 if i in self.store.statuses_by_id and not self.store.statuses_by_id[i].deleted]
        return self.render_list(items, "/api/v1/favourites")

    @route("GET", r"/api/v1/conversations")
    def conversations(self):
        user = self.require_user()
        items = []
        for status in self.store.newest_first():
            if status.visibility != "direct":
                continue
            if status.author is not user and user.id not in [m for m in status.mention_names]:
                continue
            items.append({
                "id": status.id,
                "accounts": [self.account_json(status.author)],
                "last_read": True,
                "unread": False,
                "last_status": self.status_json(status),
            })
        return 200, items

    # -- notifications ---------------------------------------------------------------

    @route("GET", r"/api/v1/notifications")
    def notifications(self):
        user = self.require_user()
        types = [t for t in self.ql("types[]") if t]
        exclude = [t for t in self.ql("exclude_types[]") if t]
        account_id = self.q("account_id")
        items = []
        for notification in reversed(self.store.notifications_for(user)):
            if types and notification["type"] not in types:
                continue
            if exclude and notification["type"] in exclude:
                continue
            if account_id and notification["account"].id != account_id:
                continue
            items.append(notification)
        page, headers = self.page(items, "/api/v1/notifications")
        return 200, [self.notification_json(n) for n in page], headers

    @route("POST", r"/api/v1/notifications/clear")
    def clear_notifications(self):
        user = self.require_user()
        self.store.notifications = [n for n in self.store.notifications if n["recipient"] is not user]
        return 200, {}

    @route("GET", r"/api/v1/notifications/(?P<notification_id>[^/]+)")
    def notification(self, notification_id):
        user = self.require_user()
        for notification in self.store.notifications_for(user):
            if notification["id"] == notification_id:
                return 200, self.notification_json(notification)
        raise ApiFail(404, "Record not found")

    # -- search ----------------------------------------------------------------------

    @route("GET", r"/api/v2/search")
    @route("GET", r"/api/v1/search")
    def search(self):
        self.require_user()
        query = (self.q("q") or "").strip()
        type_ = self.q("type")
        limit = self._int("limit", 20)

        accounts, hashtags, statuses = [], [], []

        if type_ in (None, "", "accounts") and not query.startswith("#"):
            needle = query.lstrip("@").lower().split("@")[0]
            exact = self.store.usernames.get(needle)
            if exact is not None:
                accounts = [self.account_json(exact, with_source=exact is self.viewer)]
            elif needle:
                matches = [
                    u for u in sorted(self.store.usernames.values(), key=lambda u: int(u.id))
                    if u.username.startswith(needle) or needle.startswith(u.username)
                ]
                accounts = [self.account_json(u, with_source=u is self.viewer) for u in matches]

        if type_ in (None, "", "hashtags") and query:
            name = query.lstrip("#").lower()
            if name:
                hashtags = [
                    self.tag_json(self.store.tags[key], following=key in (self.viewer.followed_tags if self.viewer else set()))
                    for key in sorted(self.store.tags)
                    if key.startswith(name)
                ]

        if type_ == "statuses" and query:
            statuses = [
                self.status_json(s) for s in self.store.newest_first()
                if s.visibility == "public" and query in s.text
            ]

        return 200, {
            "accounts": accounts[:limit],
            "hashtags": hashtags[:limit],
            "statuses": statuses[:limit],
        }

    # -- tags ------------------------------------------------------------------------

    @route("GET", r"/api/v1/tags/(?P<tag>[^/]+)")
    def get_tag(self, tag):
        name = unquote(tag).lower().lstrip("#")
        entry = self.store.tags.get(name)
        if entry is None:
            raise ApiFail(404, "Record not found")
        following = name in (self.viewer.followed_tags if self.viewer else set())
        return 200, self.tag_json(entry, following=following)

    @route("POST", r"/api/v1/tags/(?P<tag>[^/]+)/(?P<action>follow|unfollow)")
    def tag_action(self, tag, action):
        user = self.require_user()
        name = unquote(tag).lower().lstrip("#")
        entry = self.store.tag(name)
        if action == "follow":
            user.followed_tags.add(name)
        else:
            user.followed_tags.discard(name)
        return 200, self.tag_json(entry, following=name in user.followed_tags)

    @route("GET", r"/api/v1/followed_tags")
    def followed_tags(self):
        user = self.require_user()
        items = [self.store.tag(name) for name in sorted(user.followed_tags)]
        page, headers = self.page(items, "/api/v1/followed_tags")
        return 200, [self.tag_json(tag, following=True) for tag in page], headers

    @route("GET", r"/api/v1/featured_tags")
    def featured_tags(self):
        user = self.require_user()
        return 200, [self.featured_json(name, tag) for name, tag in sorted(user.featured_tags.items())]

    @route("POST", r"/api/v1/featured_tags")
    def feature_tag(self):
        user = self.require_user()
        name = (self.f("name") or "").lower().lstrip("#")
        if not name:
            raise ApiFail(422, "Validation failed: Name can't be blank")
        if name in user.featured_tags:
            raise ApiFail(422, "Record invalid")
        tag = self.store.tag(name)
        user.featured_tags[name] = tag
        return 200, self.featured_json(name, tag)

    @route("DELETE", r"/api/v1/featured_tags/(?P<tag_id>[^/]+)")
    def unfeature_tag(self, tag_id):
        user = self.require_user()
        for name, tag in list(user.featured_tags.items()):
            if tag["id"] == tag_id or name == tag_id:
                user.featured_tags.pop(name)
                return 200, {}
        raise ApiFail(404, "Record not found")

    # -- polls -----------------------------------------------------------------------

    @route("GET", r"/api/v1/polls/(?P<poll_id>[^/]+)")
    def get_poll(self, poll_id):
        user = self.require_user()
        poll = self.store.polls.get(poll_id)
        if poll is None:
            raise ApiFail(404, "Record not found")
        return 200, self.poll_json(poll, user)

    @route("POST", r"/api/v1/polls/(?P<poll_id>[^/]+)/votes")
    def vote_poll(self, poll_id):
        user = self.require_user()
        poll = self.store.polls.get(poll_id)
        if poll is None:
            raise ApiFail(404, "Record not found")

        choices = self.f("choices") or []
        if isinstance(choices, (str, int)):
            choices = [choices]
        try:
            choices = [int(choice) for choice in choices]
        except (TypeError, ValueError):
            raise ApiFail(422, "The chosen vote option does not exist")

        if len(choices) > 1 and not poll.multiple:
            # Mastodon answers a multi-choice vote on a single-choice poll with
            # this error; upstream asserts it, so mirror it.
            raise ApiFail(422, "You have already voted on this poll")
        for choice in choices:
            if choice < 0 or choice >= len(poll.options):
                raise ApiFail(422, "The chosen vote option does not exist")
        if user.id in poll.voters:
            raise ApiFail(422, "You have already voted on this poll")

        for choice in choices:
            poll.options[choice]["votes"] += 1
        poll.voters[user.id] = choices
        return 200, self.poll_json(poll, user)

    # -- lists -----------------------------------------------------------------------

    @route("GET", r"/api/v1/lists")
    def get_lists(self):
        user = self.require_user()
        items = [self.store.lists[i] for i in sorted(self.store.lists, key=int)
                 if self.store.lists[i]["user"] is user]
        return 200, [self.list_json(entry) for entry in items]

    def list_json(self, entry):
        return {
            "id": entry["id"],
            "title": entry["title"],
            "replies_policy": entry["replies_policy"],
            "exclusive": False,
        }

    @route("POST", r"/api/v1/lists")
    def create_list(self):
        user = self.require_user()
        title = self.f("title")
        if not title:
            raise ApiFail(422, "Validation failed: Title can't be blank")
        entry = {
            "id": self.store.ids.next(),
            "title": title,
            "replies_policy": self.f("replies_policy", "none") or "none",
            "user": user,
            "account_ids": set(),
        }
        self.store.lists[entry["id"]] = entry
        user.lists.add(entry["id"])
        return 200, self.list_json(entry)

    def _own_list(self, list_id):
        user = self.require_user()
        entry = self.store.lists.get(list_id)
        if entry is None or entry["user"] is not user:
            raise ApiFail(404, "Record not found")
        return user, entry

    @route("GET", r"/api/v1/lists/(?P<list_id>[^/]+)")
    def show_list(self, list_id):
        _, entry = self._own_list(list_id)
        return 200, self.list_json(entry)

    @route("PUT", r"/api/v1/lists/(?P<list_id>[^/]+)")
    def rename_list(self, list_id):
        _, entry = self._own_list(list_id)
        if self.given("title"):
            entry["title"] = self.f("title")
        if self.given("replies_policy"):
            entry["replies_policy"] = self.f("replies_policy")
        return 200, self.list_json(entry)

    @route("DELETE", r"/api/v1/lists/(?P<list_id>[^/]+)")
    def delete_list(self, list_id):
        user, entry = self._own_list(list_id)
        self.store.lists.pop(list_id)
        user.lists.discard(list_id)
        return 200, {}

    @route("GET", r"/api/v1/lists/(?P<list_id>[^/]+)/accounts")
    def list_accounts(self, list_id):
        _, entry = self._own_list(list_id)
        items = [self.store.users[i] for i in sorted(entry["account_ids"], key=int)
                 if i in self.store.users]
        return self.render_list(items, "/api/v1/lists/%s/accounts" % list_id)

    def _list_account_ids(self):
        ids = self.f("account_ids") or []
        if isinstance(ids, str):
            ids = [ids]
        return [str(i) for i in ids]

    @route("POST", r"/api/v1/lists/(?P<list_id>[^/]+)/accounts")
    def list_add_accounts(self, list_id):
        user, entry = self._own_list(list_id)
        for account_id in self._list_account_ids():
            if account_id not in self.store.users:
                raise ApiFail(422, "Record not found")
            if account_id not in user.following:
                raise ApiFail(422, "Record not found")
            entry["account_ids"].add(account_id)
        return 200, {}

    @route("DELETE", r"/api/v1/lists/(?P<list_id>[^/]+)/accounts")
    def list_remove_accounts(self, list_id):
        _, entry = self._own_list(list_id)
        for account_id in self._list_account_ids():
            entry["account_ids"].discard(account_id)
        return 200, {}


def _attr(header, name):
    match = re.search(name + r'="([^"]*)"', header)
    return match.group(1) if match else None


def _split_url(path):
    parts = path.split("?", 1)
    return unquote(parts[0].split("#", 1)[0]), (parts[1] if len(parts) > 1 else "")


def _extension(filename):
    if not filename or "." not in filename:
        return None
    return "." + filename.rsplit(".", 1)[-1].lower()


def _png_dims(payload):
    if not payload or len(payload) < 24 or payload[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", payload[16:24])


def _id_of(item):
    if isinstance(item, dict):
        return item.get("id")
    return getattr(item, "id", None)


def _index_of(items, cursor):
    for index, item in enumerate(items):
        if _id_of(item) == cursor:
            return index
    return None


def serve(host, port, verbose=False):
    store = Store()
    Handler.store = store
    Handler.verbose = verbose
    server = ThreadingHTTPServer((host, port), Handler)
    server.daemon_threads = True
    return server, store


def main(argv=None):
    parser = argparse.ArgumentParser(description="Mastodon API stub for toot's integration tests")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=3000)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    server, _ = serve(args.host, args.port, args.verbose)
    sys.stdout.write("ready {}:{}\n".format(args.host, server.server_address[1]))
    sys.stdout.flush()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
