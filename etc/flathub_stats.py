#!/usr/bin/python3

from urllib import request
from urllib.error import HTTPError
import json
import csv
import datetime
import os
import argparse
import logging
import asyncio
import aiohttp

STATS_URL = 'https://flathub.org/stats'

START_DATE = datetime.date(2018, 4, 29)
END_DATE = datetime.date.today()

async def get_json_for_date(http_session, date):
    date_subpath = date.strftime("%Y/%m/%d")
    url = f'{STATS_URL}/{date_subpath}.json'
    async with http_session.get(url) as resp:
        if resp.status >= 400:
            logging.error(f'GET {url} returned {resp.status}')
        else:
            return await resp.json()

async def get_stats_for_date(http_session, date, app_ids):
    data = await get_json_for_date(http_session, date)
    if data is None:
        return
    logging.debug(f'Fetched data for {date}')
    per_app_new_downloads = []
    for app_id in app_ids:
        new_downloads = 0
        if app_id in data['refs']:
            app_data = data['refs'][app_id]
            for arch in app_data.keys():
                d, u = app_data[arch]
                new_downloads += d - u
        per_app_new_downloads.append(new_downloads)
    return (date, per_app_new_downloads)

async def get_stats(start_date, end_date, app_ids):
    coros = []
    async with aiohttp.ClientSession() as http_session:
        for date in (start_date + datetime.timedelta(n) for n in range((end_date - start_date).days)):
            coros.append(get_stats_for_date(http_session, date, app_ids))
        for stats in await asyncio.gather(*coros):
            if stats is not None:
                yield stats

async def download_stats(app_ids: list, outfile="flathub_stats.csv"):
    with open(outfile, 'w') as c:
        writer = csv.writer(c)
        writer.writerow(['date'] + app_ids)
        async for date, new_downloads in get_stats(START_DATE, END_DATE, app_ids):
            logging.debug(f'Writing data for {date}')
            writer.writerow([date.isoformat()] + new_downloads)

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("app_id", nargs="+", help="Application ID(s)")
    args = parser.parse_args()
    await download_stats(app_ids=args.app_id)

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(main())
