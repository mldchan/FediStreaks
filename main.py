import datetime
import logging
import os
import threading
import time

import psycopg2
import schedule
import sentry_sdk
from misskey import Misskey, NoteVisibility
from misskey.exceptions import MisskeyAPIException
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

INSTANCE = os.getenv("INSTANCE")
TOKEN = os.getenv("TOKEN")
SENTRY_DSN = os.getenv("SENTRY_DSN")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", encoding='utf-8')

sentry_sdk.init(SENTRY_DSN,
                integrations=[LoggingIntegration(level=logging.INFO, event_level=logging.WARN),
                              AsyncioIntegration()], traces_sample_rate=1.0, profiles_sample_rate=1.0)

mk = Misskey(INSTANCE, i=TOKEN)
db = psycopg2.connect(f'postgres://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}')


def check_user_streak(user_id: str):
    cur = db.cursor()

    try:
        user = mk.users_show(user_id=user_id)
        if user['host']:
            mention = '@' + user['username'] + '@' + user['host']
        else:
            mention = '@' + user['username']

        logging.info(f'Checking user user {mention}')

        now = datetime.datetime.now()
        notes = mk.users_notes(user_id=user_id, include_replies=True, include_my_renotes=True, limit=100,
                               since_date=datetime.datetime(now.year, now.month, now.day))

        logging.info('Today note count: %i', len(notes))

        cur.execute(
            'insert into fedistreaks_users("user", start_date, last_note_date) values (%s, current_date, current_date) on conflict do nothing',
            (mention,))

        if len(notes) > 0:
            cur.execute(
                'select (last_note_date - start_date) AS days from fedistreaks_users where "user" = %s',
                (mention,)
            )

            old_days = cur.fetchone()[0]

            logging.info('Old days count: %i', old_days)

            cur.execute('update fedistreaks_users set last_note_date = current_date where "user" = %s', (mention,))

            logging.info('Updated DB, changes: %i', cur.rowcount)

            cur.execute(
                'select (last_note_date - start_date) AS days from fedistreaks_users where "user" = %s',
                (mention,)
            )

            new_days = cur.fetchone()[0]

            logging.info('New days count: %i', new_days)

            if old_days != new_days:
                logging.info('Note time change')
                mk.notes_create(f'{mention} {new_days} day streak! :3', visibility=NoteVisibility.SPECIFIED, visible_user_ids=[user_id])
        else:
            cur.execute(
                'select (current_date - start_date) AS days from fedistreaks_users where "user" = %s',
                (mention,)
            )

            days = cur.fetchone()[0]

            logging.info('Current days count: %i', days)

            cur.execute(
                'update fedistreaks_users set start_date = current_date, last_note_date = current_date where (current_date - last_note_date) >= 2')

            logging.info('Updated DB for older users, changes: %i', cur.rowcount)

            if cur.rowcount > 0:
                logging.info('User streak expired')
                mk.notes_create(f'{mention} Your streak of {days} days has expired :(', visibility=NoteVisibility.SPECIFIED, visible_user_ids=[user_id])
    finally:
        db.commit()
        if not cur.closed:
            cur.close()


def check_users_streak():
    cur = db.cursor()

    cur.execute('''create table if not exists fedistreaks_users
(
    "user"         text not null
        constraint fedistreaks_users_pk
            primary key,
    start_date     date not null,
    last_note_date date not null
);

comment on column fedistreaks_users."user" is 'The ID located in the fediverse.';

comment on constraint fedistreaks_users_pk on fedistreaks_users is 'A username on fedi can''t be changed';

comment on column fedistreaks_users.start_date is 'The date of start of the streak. Set to follow date or current date when one day is missed.';

comment on column fedistreaks_users.last_note_date is 'The date when the user last made a note.';

alter table fedistreaks_users
    owner to mldchan;''')

    try:
        user = mk.i()
        followers = mk.users_followers(user_id=user['id'])
        threads = []

        for follower in followers:
            t = threading.Thread(target=check_user_streak, args=(follower['followerId'],))
            t.start()
            logging.info(f'Started thread {t.name}')

        for thread in threads:
            thread.join()
    finally:
        if not cur.closed:
            cur.close()

def follow_back():
    try:
        user = mk.i()
        followers = mk.users_followers(user_id=user['id'])
        for follower in followers:
            try:
                mk.following_create(user_id=follower['followerId'])
            except MisskeyAPIException:
                pass
    except Exception as e:
        sentry_sdk.capture_exception(e)


if __name__ == '__main__':

    schedule.every(30).seconds.do(check_users_streak)
    schedule.every(5).minutes.do(follow_back)

    while True:
        schedule.run_pending()
        time.sleep(1)
