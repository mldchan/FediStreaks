
# Fedi Streaks

A bot that simply counts how many days in a row have you posted a note.

## Development

1. Clone the repository
2. Start the development postgres server in docker-compose.dev.yml
3. Configure the .env file
4. Run main.py

## Env File

```
INSTANCE=social.mldchan.dev
TOKEN=
POSTGRES_HOST=
POSTGRES_PORT=
POSTGRES_USER=
POSTGRES_PASSWORD=
POSTGRES_DB=
SENTRY_DSN=
```

You can use the same env file for Postgres to have one config file for everything.

## Functionality

The main functionality is that you follow the bot for it to take actions on you.
